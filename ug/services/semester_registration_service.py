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
        Eligibility is determined by the LATEST SemesterRegistration record.
        
        Logic:
        1. Find latest SemesterRegistration for student
        2. If is_open=True AND today is within start_date/end_date (if set) -> Eligible & Open
        
        Args:
            student: UGStudentProfile instance
            
        Returns:
            Dict with eligibility status and details
        """
        # 1. Get the latest registration record (by sem mainly)
        last_registration = SemesterRegistration.objects.filter(
            student=student
        ).order_by('-sem').first()
        
        if not last_registration:
            return {
                'eligible': False,
                'reason': 'No registration record found. Please contact admin.',
                'current_semester': student.current_semester,
            }
            
        current_semester = last_registration.sem ## created entry first in semesterregistration then open it
        # current_semester = next_semester - 1 if next_semester > 1 else 1 # Infer current sem

        # 2. Check simple eligibility (record exists = eligible contextually)
        # But we need to check if it represents an OPEN registration window
        
        is_open = last_registration.is_open
        now = timezone.now()
        
        # Check date validity if dates are present
        date_valid = True
        if last_registration.start_date and now < last_registration.start_date:
            date_valid = False
        if last_registration.end_date and now > last_registration.end_date:
            date_valid = False
            
        if is_open and date_valid:
             return {
                'eligible': True,
                'current_semester': int(current_semester) -1,
                'next_semester': current_semester,
                'registration_open': True,
                'registration_window': {
                    'start_date': last_registration.start_date.isoformat() if last_registration.start_date else None,
                    'end_date': last_registration.end_date.isoformat() if last_registration.end_date else None,
                    'is_open': True
                },  
                'message': f'You are eligible to register for Semester {current_semester}'
            }
        
        # Record exists but closed
        return {
            'eligible': True, # User says "those entry already created... are eligible"
            'registration_open': False,
            'reason': 'Registration window is currently closed',
            'current_semester': int(current_semester) - 1,
            'next_semester': current_semester,
            'registration_window': {
                'start_date': last_registration.start_date.isoformat() if last_registration.start_date else None,
                'end_date': last_registration.end_date.isoformat() if last_registration.end_date else None,
                'is_open': False
            }
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
        # Get all courses for this semester and batch
        all_courses = CourseStructure.objects.filter(
            semester=semester,
            batch=student.batch
        )
        
        # Get major courses (filtered by student's major_course department)
        major_courses_qs = all_courses.filter(
            course_type__icontains='MJC'
        )
        if student.major_course:
            major_courses_qs = major_courses_qs.filter(department=student.major_course)
        
        major_courses = []
        for course in major_courses_qs:
            major_courses.append({
                'code': course.paper_code or course.course_code,
                'name': course.course_name,
                'course_type': course.course_type,
                'credit': course.max_credit,
                'marks': float(course.max_marks) if course.max_marks else 100,
                'department': course.department.name if course.department else None
            })
        
        # Get minor courses (filtered by student's minor_course department)
        minor_courses_qs = all_courses.filter(
            course_type__icontains='MIC'
        )
        if student.minor_course:
            minor_courses_qs = minor_courses_qs.filter(department=student.minor_course)
        
        minor_courses = []
        for course in minor_courses_qs:
            minor_courses.append({
                'code': course.paper_code or course.course_code,
                'name': course.course_name,
                'course_type': course.course_type,
                'credit': course.max_credit,
                'marks': float(course.max_marks) if course.max_marks else 100,
                'department': course.department.name if course.department else None
            })
        
        # Get MDC courses (filtered by student's mdc_course department)
        mdc_courses_qs = all_courses.filter(
            course_type__icontains='MDC'
        )
        if student.mdc_course:
            mdc_courses_qs = mdc_courses_qs.filter(department=student.mdc_course)
        
        mdc_courses = []
        for course in mdc_courses_qs:
            mdc_courses.append({
                'code': course.paper_code or course.course_code,
                'name': course.course_name,
                'course_type': course.course_type,
                'credit': course.max_credit,
                'marks': float(course.max_marks) if course.max_marks else 100,
                'department': course.department.name if course.department else None
            })
        
        # Get department-agnostic courses (courses without department)
        other_courses_qs = all_courses.filter(
            department__isnull=True
        ).exclude(
            course_type__icontains='MJC'
        ).exclude(
            course_type__icontains='MIC'
        ).exclude(
            course_type__icontains='MDC'
        )
        
        other_courses = []
        for course in other_courses_qs:
            other_courses.append({
                'code': course.paper_code or course.course_code,
                'name': course.course_name,
                'course_type': course.course_type,
                'credit': course.max_credit,
                'marks': float(course.max_marks) if course.max_marks else 100
            })
        
        # Determine auto_assign
        # MJC, MIC, MDC are ALWAYS auto_assigned as per requirements
        mjc_auto_assign = True
        mic_auto_assign = True
        mdc_auto_assign = True
        
        # Other courses: Auto-assign only if there is exactly one option
        # If more than one, user must select
        other_auto_assign = len(other_courses) == 1
        
        return {
            'semester': semester,
            'session': student.session,
            'courses': {
                'major_courses': {
                    'type': 'MJC',
                    'description': 'Major Core Courses',
                    'auto_assigned': mjc_auto_assign,
                    'options': major_courses
                },
                'minor_courses': {
                    'type': 'MIC',
                    'description': 'Minor Core Courses',
                    'auto_assigned': mic_auto_assign,
                    'options': minor_courses
                },
                'mdc_courses': {
                    'type': 'MDC',
                    'description': 'Multi-Disciplinary Courses',
                    'auto_assigned': mdc_auto_assign,
                    'options': mdc_courses
                },
                'other_courses': {
                    'description': 'Other Courses (SEC, AEC, etc.)',
                    'auto_assigned': other_auto_assign,
                    'options': other_courses
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
        # Get requirements and available courses
        available = SemesterRegistrationService.get_available_courses(student, semester)
        
        # Check other courses (if not auto-assigned)
        other_info = available['courses']['other_courses']
        if not other_info['auto_assigned']:
            # If not auto-assigned, user must have selected something?
            # User said "give option to select". We assume at least one selection if options exist.
            # However, without specific requirement counts (which are fuzzy for "other"), 
            # we will just validate that selected codes are valid options.
            selected_codes = selections.get('other_courses', [])
            
            # If options exist but nothing selected, is it an error?
            # Depending on strictness. Let's assume yes if options > 0.
            if len(other_info['options']) > 0 and len(selected_codes) == 0:
                pass # Warning: We'll allow 0 selection for now unless strict requirements are reintroduced
            
            # Validate selected codes exist in options
            valid_codes = [c['code'] for c in other_info['options']]
            for code in selected_codes:
                if code not in valid_codes:
                    return False, f'Invalid course code selected: {code}'
        
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
        
        # 1. MJC (Always auto-assigned)
        courses_to_register.extend(available['courses']['major_courses']['options'])
        
        # 2. MIC (Always auto-assigned)
        courses_to_register.extend(available['courses']['minor_courses']['options'])
        
        # 3. MDC (Always auto-assigned)
        courses_to_register.extend(available['courses']['mdc_courses']['options'])
        
        # 4. Other Courses
        other_info = available['courses']['other_courses']
        if other_info['auto_assigned']:
            # Auto-assign all options (there should be only 1)
            courses_to_register.extend(other_info['options'])
        else:
            # User selected courses from options
            selected_codes = selections.get('other_courses', [])
            for code in selected_codes:
                course = next(
                    (c for c in other_info['options'] if c['code'] == code),
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
                    session=student.session,
                    paper_code=course['code']
                ).exists()
                
                if existing:
                    continue
                
                # Create assessment entry
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
                    department_id=None, # Will be filled by mapper script or null for common
                    label='REGISTRATION',
                )
                
                registered_courses.append({
                    'code': course['code'],
                    'name': course['name'],
                    'type': course['course_type'],
                    'auto_assigned': True # Effectively true for most
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
