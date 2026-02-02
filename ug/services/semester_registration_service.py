"""
Semester Registration Service

Handles student semester registration logic including:
- Eligibility verification (PASS/PROMOTED status)
- Course filtering by department
- Auto-assignment of minor/MDC courses
- Validation of course selections
- Creation of StudentCourseAssessment records
"""
from django.db.models import Q
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from ug.models import (
    UGStudentProfile,
    UGExamResult,
    SemesterRegistration,
    CourseStructure,
    CommonCourseStructure,
    StudentCourseAssessment,
    UGDepartment
)


class SemesterRegistrationService:
    """Service for handling semester registration operations"""
    
    @staticmethod
    def check_registration_eligibility(student: UGStudentProfile) -> Dict:
        """
        Check if student is eligible to register for next semester
        
        Args:
            student: UGStudentProfile instance
            
        Returns:
            Dict with eligibility status and details
        """
        current_semester = student.current_semester or 1
        next_semester = current_semester + 1
        
        # Get latest exam result
        latest_result = UGExamResult.objects.filter(
            student=student
        ).order_by('-created_at').first()
        
        if not latest_result:
            return {
                'eligible': False,
                'reason': 'No exam results found',
                'current_semester': current_semester,
                'next_semester': next_semester
            }
        
        # Check if student passed or was promoted
        semester_result = latest_result.semester_result
        is_eligible = semester_result in ['PASS', 'PROMOTED']
        
        if not is_eligible:
            return {
                'eligible': False,
                'reason': f'Student result is {semester_result}. Only PASS or PROMOTED students can register.',
                'current_semester': current_semester,
                'next_semester': next_semester,
                'semester_result': semester_result
            }
        
        # Check if semester registration exists for next semester
        sem_registration = SemesterRegistration.objects.filter(
            student=student,
            sem=next_semester
        ).first()
        
        if not sem_registration:
            return {
                'eligible': False,
                'reason': f'Semester {next_semester} registration not created yet',
                'current_semester': current_semester,
                'next_semester': next_semester,
                'semester_result': semester_result
            }
        
        # Check if registration window is open
        if not sem_registration.is_open:
            return {
                'eligible': False,
                'reason': 'Registration window is closed',
                'current_semester': current_semester,
                'next_semester': next_semester,
                'semester_result': semester_result,
                'registration_window': {
                    'start_date': sem_registration.start_date.isoformat() if sem_registration.start_date else None,
                    'end_date': sem_registration.end_date.isoformat() if sem_registration.end_date else None,
                    'is_open': False
                }
            }
        
        # Student is eligible
        return {
            'eligible': True,
            'current_semester': current_semester,
            'next_semester': next_semester,
            'semester_result': semester_result,
            'registration_open': True,
            'registration_window': {
                'start_date': sem_registration.start_date.isoformat() if sem_registration.start_date else None,
                'end_date': sem_registration.end_date.isoformat() if sem_registration.end_date else None,
                'is_open': True
            },
            'message': f'You are eligible to register for Semester {next_semester}'
        }
    
    @staticmethod
    def get_student_department_from_major(student: UGStudentProfile) -> Optional[str]:
        """
        Extract department name from student's major course
        
        Args:
            student: UGStudentProfile instance
            
        Returns:
            Department name or None
        """
        if student.department:
            return student.department.name
        
        # Fallback: Extract from major_course field
        if student.major_course:
            # major_course might be like "History" or "Political Science"
            return student.major_course
        
        return None
    
    @staticmethod
    def get_major_courses_for_student(student: UGStudentProfile, semester: str) -> List[Dict]:
        """
        Get major courses filtered by student's department
        
        Args:
            student: UGStudentProfile instance
            semester: Semester code (e.g., '3RD')
            
        Returns:
            List of course dictionaries
        """
        dept_name = SemesterRegistrationService.get_student_department_from_major(student)
        
        # Get major courses from CourseStructure
        major_courses = CourseStructure.objects.filter(
            semester=semester,
            course_type__icontains='MJC',  # Major Core Courses
            batch=student.batch
        )
        
        # Filter by department if available
        if dept_name and student.department:
            major_courses = major_courses.filter(department=student.department)
        
        # Convert to list of dicts
        courses = []
        for course in major_courses:
            courses.append({
                'code': course.paper_code or course.course_code,
                'name': course.course_name,
                'course_type': course.course_type,
                'credit': course.max_credit,
                'marks': float(course.max_marks) if course.max_marks else 100,
                'department': course.department.name if course.department else None
            })
        
        return courses
    
    @staticmethod
    def get_first_semester_courses(student: UGStudentProfile, course_type: str) -> List[Dict]:
        """
        Get courses of specific type from student's 1st semester
        
        Args:
            student: UGStudentProfile instance
            course_type: Course type filter (e.g., 'MIC', 'MDC')
            
        Returns:
            List of course dictionaries
        """
        first_sem_assessments = StudentCourseAssessment.objects.filter(
            student=student,
            semester='1ST',
            course_type__icontains=course_type
        ).distinct('paper_code')
        
        courses = []
        for assessment in first_sem_assessments:
            courses.append({
                'code': assessment.paper_code,
                'name': assessment.course_name,
                'course_type': assessment.course_type,
                'credit': assessment.course_max_credits or 0,
                'marks': float(assessment.course_max_marks) if assessment.course_max_marks else 100
            })
        
        return courses
    
    @staticmethod
    def get_next_semester_equivalent(student: UGStudentProfile, semester: str, 
                                     first_sem_course_type: str) -> List[Dict]:
        """
        Get equivalent courses for next semester based on 1st semester selection
        
        Args:
            student: UGStudentProfile instance
            semester: Target semester (e.g., '3RD')
            first_sem_course_type: Course type from 1st semester
            
        Returns:
            List of equivalent course dictionaries
        """
        # Get 1st semester course
        first_sem_courses = SemesterRegistrationService.get_first_semester_courses(
            student, first_sem_course_type
        )
        
        if not first_sem_courses:
            return []
        
        # Get equivalent for target semester
        # For now, just filter by course_type and semester
        next_sem_courses = CourseStructure.objects.filter(
            semester=semester,
            course_type__icontains=first_sem_course_type,
            batch=student.batch
        )
        
        # If minor course, try to match department
        if first_sem_course_type == 'MIC' and first_sem_courses:
            # Try to find same subject/department minor courses
            # This depends on your course naming convention
            pass
        
        courses = []
        for course in next_sem_courses:
            courses.append({
                'code': course.paper_code or course.course_code,
                'name': course.course_name,
                'course_type': course.course_type,
                'credit': course.max_credit,
                'marks': float(course.max_marks) if course.max_marks else 100,
                'auto_assigned': True
            })
        
        return courses
    
    @staticmethod
    def get_elective_courses(student: UGStudentProfile, semester: str, 
                            course_types: List[str]) -> List[Dict]:
        """
        Get elective courses for semester
        
        Args:
            student: UGStudentProfile instance
            semester: Target semester
            course_types: List of course types to include (e.g., ['GE', 'DSE', 'AECC'])
            
        Returns:
            List of elective course dictionaries
        """
        # Build Q object for multiple course types
        q_filter = Q()
        for ct in course_types:
            q_filter |= Q(course_type__icontains=ct)
        
        elective_courses = CourseStructure.objects.filter(
            q_filter,
            semester=semester,
            batch=student.batch
        )
        
        courses = []
        for course in elective_courses:
            courses.append({
                'code': course.paper_code or course.course_code,
                'name': course.course_name,
                'course_type': course.course_type,
                'credit': course.max_credit,
                'marks': float(course.max_marks) if course.max_marks else 100
            })
        
        return courses
    
    @staticmethod
    def get_course_requirements_from_common_structure(semester: str) -> Dict[str, int]:
        """
        Get required course counts from CommonCourseStructure
        
        Args:
            semester: Semester code
            
        Returns:
            Dict mapping course types to required counts
        """
        common_courses = CommonCourseStructure.objects.filter(
            semester__icontains=semester
        )
        
        requirements = {}
        for course in common_courses:
            course_type = course.course_type
            if course_type:
                # Extract type prefix (e.g., 'MJC' from 'MJC-1')
                type_prefix = course_type.split('-')[0] if '-' in course_type else course_type
                requirements[type_prefix] = requirements.get(type_prefix, 0) + 1
        
        return requirements
    
    @staticmethod
    def get_available_courses(student: UGStudentProfile, semester: str) -> Dict:
        """
        Get all available courses for student registration
        
        Args:
            student: UGStudentProfile instance
            semester: Target semester (e.g., '3RD')
            
        Returns:
            Dict with categorized course options
        """
        # Get course requirements
        requirements = SemesterRegistrationService.get_course_requirements_from_common_structure(semester)
        
        # Get major courses (filtered by department)
        major_courses = SemesterRegistrationService.get_major_courses_for_student(student, semester)
        
        # Get minor courses (auto-assigned from 1st semester)
        minor_courses = SemesterRegistrationService.get_next_semester_equivalent(
            student, semester, 'MIC'
        )
        
        # Get MDC courses (auto-assigned from 1st semester)
        mdc_courses = SemesterRegistrationService.get_next_semester_equivalent(
            student, semester, 'MDC'
        )
        
        # Get elective courses
        elective_courses = SemesterRegistrationService.get_elective_courses(
            student, semester, ['GE', 'DSE', 'SEC']
        )
        
        # Get AECC courses
        aecc_courses = SemesterRegistrationService.get_elective_courses(
            student, semester, ['AECC']
        )
        
        return {
            'semester': semester,
            'session': student.session,
            'courses': {
                'major_courses': {
                    'type': 'MJC',
                    'description': 'Major Core Courses',
                    'required_count': requirements.get('MJC', 0),
                    'auto_assigned': False,
                    'options': major_courses
                },
                'minor_courses': {
                    'type': 'MIC',
                    'description': 'Minor Core Courses',
                    'required_count': requirements.get('MIC', 0),
                    'auto_assigned': True,
                    'selected': minor_courses
                },
                'mdc_courses': {
                    'type': 'MDC',
                    'description': 'Multi-Disciplinary Courses',
                    'required_count': requirements.get('MDC', 0),
                    'auto_assigned': True,
                    'selected': mdc_courses
                },
                'elective_courses': {
                    'type': 'GE/DSE/SEC',
                    'description': 'Elective Courses',
                    'required_count': requirements.get('GE', 0) + requirements.get('DSE', 0) + requirements.get('SEC', 0),
                    'auto_assigned': False,
                    'options': elective_courses
                },
                'aecc_courses': {
                    'type': 'AECC',
                    'description': 'Ability Enhancement Compulsory Course',
                    'required_count': requirements.get('AECC', 0),
                    'auto_assigned': False,
                    'options': aecc_courses
                }
            }
        }
    
    @staticmethod
    def validate_course_selections(student: UGStudentProfile, semester: str, 
                                   selections: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate student's course selections
        
        Args:
            student: UGStudentProfile instance
            semester: Target semester
            selections: Dict with selected course codes by type
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get requirements
        requirements = SemesterRegistrationService.get_course_requirements_from_common_structure(semester)
        available = SemesterRegistrationService.get_available_courses(student, semester)
        
        # Check major course count
        major_selected = selections.get('major_courses', [])
        major_required = requirements.get('MJC', 0)
        if len(major_selected) != major_required:
            return False, f'Must select exactly {major_required} major courses, but {len(major_selected)} selected'
        
        # Validate major courses are from available options
        major_codes = [c['code'] for c in available['courses']['major_courses']['options']]
        for code in major_selected:
            if code not in major_codes:
                return False, f'Invalid major course code: {code}'
        
        # Check for duplicates
        all_selected = (
            major_selected + 
            selections.get('elective_courses', []) + 
            selections.get('aecc_courses', [])
        )
        if len(all_selected) != len(set(all_selected)):
            return False, 'Duplicate course selection detected'
        
        # Check elective count if required
        elective_selected = selections.get('elective_courses', [])
        elective_required = requirements.get('GE', 0) + requirements.get('DSE', 0) + requirements.get('SEC', 0)
        if elective_required > 0 and len(elective_selected) != elective_required:
            return False, f'Must select exactly {elective_required} elective courses'
        
        return True, None
    
    @staticmethod
    def create_course_registrations(student: UGStudentProfile, semester: str, 
                                    selections: Dict) -> Dict:
        """
        Create StudentCourseAssessment entries for selected courses
        
        Args:
            student: UGStudentProfile instance
            semester: Target semester
            selections: Dict with selected course codes
            
        Returns:
            Dict with registration details
        """
        from django.db import transaction
        
        # Validate selections first
        is_valid, error_msg = SemesterRegistrationService.validate_course_selections(
            student, semester, selections
        )
        
        if not is_valid:
            raise ValueError(error_msg)
        
        # Get all available courses
        available = SemesterRegistrationService.get_available_courses(student, semester)
        
        # Collect all courses to register
        courses_to_register = []
        
        # Add selected major courses
        for code in selections.get('major_courses', []):
            course = next(
                (c for c in available['courses']['major_courses']['options'] if c['code'] == code),
                None
            )
            if course:
                courses_to_register.append(course)
        
        # Add auto-assigned minor courses
        courses_to_register.extend(available['courses']['minor_courses']['selected'])
        
        # Add auto-assigned MDC courses
        courses_to_register.extend(available['courses']['mdc_courses']['selected'])
        
        # Add selected electives
        for code in selections.get('elective_courses', []):
            course = next(
                (c for c in available['courses']['elective_courses']['options'] if c['code'] == code),
                None
            )
            if course:
                courses_to_register.append(course)
        
        # Add selected AECC
        for code in selections.get('aecc_courses', []):
            course = next(
                (c for c in available['courses']['aecc_courses']['options'] if c['code'] == code),
                None
            )
            if course:
                courses_to_register.append(course)
        
        # Create assessment entries in transaction
        registered_courses = []
        total_credits = 0
        
        with transaction.atomic():
            for course in courses_to_register:
                # Check if already registered
                existing = StudentCourseAssessment.objects.filter(
                    student=student,
                    semester=semester,
                    paper_code=course['code']
                ).exists()
                
                if existing:
                    continue
                
                # Create assessment entry
                # Note: We create one entry per course, marks will be filled later
                StudentCourseAssessment.objects.create(
                    student=student,
                    semester=semester,
                    session=student.session,
                    batch=student.batch,
                    paper_code=course['code'],
                    course_name=course['name'],
                    course_type=course['course_type'],
                    course_max_credits=course['credit'],
                    course_max_marks=course['marks'],
                    label='REGISTRATION',  # Placeholder label
                    # All marks fields are null initially
                )
                
                registered_courses.append({
                    'code': course['code'],
                    'name': course['name'],
                    'type': course['course_type'],
                    'auto_assigned': course.get('auto_assigned', False)
                })
                
                total_credits += course['credit'] or 0
            
            # Update semester registration status
            SemesterRegistration.objects.filter(
                student=student,
                sem=semester
            ).update(status='REGISTERED')
        
        return {
            'success': True,
            'message': f'Successfully registered for Semester {semester}',
            'registered_courses': registered_courses,
            'total_credits': total_credits,
            'total_courses': len(registered_courses)
        }
