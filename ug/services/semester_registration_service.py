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
    UGDepartment,
    UGBatch
)
from django.utils import timezone

class SemesterRegistrationService:
    """Service for handling semester registration operations"""
    
    # Semester mapping constant
    SEMESTER_MAP = {
        '1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4,
        '5TH': 5, '6TH': 6, '7TH': 7, '8TH': 8
    }
    
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
        registration = SemesterRegistration.objects.filter(
            student=student
        ).order_by('-sem').first()
        
        if not registration:
            return {
                'eligible': False,
                'reason': 'No registration record found. Please contact admin.',
                'current_semester': student.current_semester,
            }
            
        current_semester = registration.sem ## created entry first in semesterregistration then open it
        # current_semester = next_semester - 1 if next_semester > 1 else 1 # Infer current sem

        # 2. Check simple eligibility (record exists = eligible contextually)
        # But we need to check if it represents an OPEN registration window
        
        is_open = registration.is_open
        now = timezone.now()
        
        # Check date validity if dates are present
        date_valid = True
        if registration.start_date and now < registration.start_date:
            date_valid = False
        if registration.end_date and now > registration.end_date:
            date_valid = False
        
        # Convert semester number to text format
        semester_text_map = {
            1: '1ST', 2: '2ND', 3: '3RD', 4: '4TH',
            5: '5TH', 6: '6TH', 7: '7TH', 8: '8TH'
        }
        semester_name = semester_text_map.get(int(current_semester), f'{current_semester}TH')
        
        # Check if already registered
        if registration.status == 'REGISTERED':
            return {
                'eligible': False,
                'already_registered': True,
                'current_semester': int(current_semester) - 1,
                'next_semester': current_semester,
                'registration_open': False,
                'message': f'You are already registered for Semester {semester_name}',
                'reason': f'Already registered for Semester {semester_name}'
            }
            
        if is_open and date_valid:
             return {
                'eligible': True,
                'current_semester': int(current_semester) - 1,
                'next_semester': current_semester,
                'registration_open': True,
                'registration_window': {
                    'start_date': registration.start_date.isoformat() if registration.start_date else None,
                    'end_date': registration.end_date.isoformat() if registration.end_date else None,
                    'is_open': True
                },  
                'message': f'You are eligible to register for Semester {semester_name}'
            }
        
        # Record exists but closed
        return {
            'eligible': True, # User says "those entry already created... are eligible"
            'registration_open': False,
            'reason': 'Registration window is currently closed',
            'current_semester': int(current_semester) - 1,
            'next_semester': current_semester,
            'registration_window': {
                'start_date': registration.start_date.isoformat() if registration.start_date else None,
                'end_date': registration.end_date.isoformat() if registration.end_date else None,
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
        print(common_courses, 'this is common courses for 3rd semester')
        requirements = {}
        for course in common_courses:
            course_type = course.course_type
            print(course_type, 'this is course type')
            if course_type:
                # Extract type prefix (e.g., 'MJC' from 'MJC-1')
                type_prefix = course_type.split('-')[0] if '-' in course_type else course_type
                requirements[type_prefix] = requirements.get(type_prefix, 0) + 1
        
        return requirements
    
    @staticmethod
    def _consolidate_courses_by_type(courses_queryset):
        """
        Consolidate courses by course_type (course_code).
        Returns a dictionary keyed by course_type with unique course info
        and all assessment entries (CIA, ESE, Theory, Practical).
        
        Returns:
            Dictionary where keys are course_types (e.g., MJC-3, AEC-3)
        """
        courses_dict = {}
        
        for course in courses_queryset:
            course_type = course.course_code  # e.g., MJC-3, AEC-3
            
            if course_type:
                if course_type not in courses_dict:
                    # First entry for this course type - initialize the structure
                    courses_dict[course_type] = {
                        'uid': str(course.uid),
                        'code': course.paper_code or course.course_code,
                        'name': course.course_name,
                        'department': course.department.name if course.department else None,
                        'total_credit': course.max_credit or 0,
                        'assessments': []
                    }
                
                # Add assessment entry
                assessment = {
                    'uid': str(course.uid),
                    'label': course.label or 'Assessment',
                    'type': course.course_type or 'General',
                    'marks': float(course.max_marks) if course.max_marks else 0,
                    'min_marks': float(course.min_marks) if course.min_marks else 0,
                }
                courses_dict[course_type]['assessments'].append(assessment)
        
        # Calculate total marks for each course
        for course_data in courses_dict.values():
            course_data['total_marks'] = sum(a['marks'] for a in course_data['assessments'])
        
        return courses_dict


    
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
        # Get the UGBatch object from student's batch string
        batch_obj = None
        if student.batch:
            batch_obj = UGBatch.objects.filter(name=student.batch).first()
        
        # Map semester name to number using class constant
        semester_num = SemesterRegistrationService.SEMESTER_MAP.get(semester, 3)
        semester_num_str = str(semester_num)  # CourseStructure uses '1', '2', '3'

        
        # Get session from SemesterRegistration
        registration = SemesterRegistration.objects.filter(
            student=student,
            sem=semester_num,
            is_open=True
        ).order_by('-created_at').first()
        
        session = registration.session if registration and registration.session else student.session
        
        # Get course types from CommonCourseStructure for this semester
        common_courses = CommonCourseStructure.objects.filter(
            semester__icontains=semester
        )
        # Extract course type patterns (e.g., MJC-3, MIC-3, MDC-3, AEC-3, SEC-3)
        course_types_in_semester = set()
        for cc in common_courses:
            if cc.course_type:
                course_types_in_semester.add(cc.course_type.upper())
        # Base query for CourseStructure - filter by semester only (no batch filter)
        base_query = CourseStructure.objects.filter(semester=semester_num_str)

        
        # === MAJOR COURSES (MJC) ===
        mjc_patterns = [ct for ct in course_types_in_semester if ct.startswith('MJC')]
        
        if mjc_patterns:
            mjc_query = base_query.filter(course_code__in=mjc_patterns)
            if student.major_course:
                mjc_query = mjc_query.filter(
                    department=student.major_course,
                    department__is_publish=True
                )
            
            major_courses_dict = SemesterRegistrationService._consolidate_courses_by_type(mjc_query)
        else:
            major_courses_dict = {}
        
        # === MINOR COURSES (MIC) ===
        mic_patterns = [ct for ct in course_types_in_semester if ct.startswith('MIC')]
        
        if mic_patterns:
            mic_query = base_query.filter(course_code__in=mic_patterns)
            if student.minor_course:
                mic_query = mic_query.filter(
                    department=student.minor_course,
                    department__is_publish=True
                )
            
            minor_courses_dict = SemesterRegistrationService._consolidate_courses_by_type(mic_query)
        else:
            minor_courses_dict = {}
        
        # === MDC COURSES ===
        mdc_patterns = [ct for ct in course_types_in_semester if ct.startswith('MDC')]
        
        if mdc_patterns:
            mdc_query = base_query.filter(course_code__in=mdc_patterns)
            if student.mdc_course:
                mdc_query = mdc_query.filter(
                    department=student.mdc_course,
                    department__is_publish=True
                )
            mdc_courses_dict = SemesterRegistrationService._consolidate_courses_by_type(mdc_query)
        else:
            mdc_courses_dict = {}
        
        # === OTHER COURSES (AEC, SEC, GE, etc.) ===
        other_patterns = [ct for ct in course_types_in_semester 
                         if not ct.startswith('MJC') 
                         and not ct.startswith('MIC') 
                         and not ct.startswith('MDC')]
        
        if other_patterns:
            other_query = base_query.filter(course_code__in=other_patterns)
            other_courses_dict = SemesterRegistrationService._consolidate_courses_by_type(other_query)
        else:
            other_courses_dict = {}
        
        # Merge all courses into a single dictionary
        all_courses = {}
        all_courses.update(major_courses_dict)
        all_courses.update(minor_courses_dict)
        all_courses.update(mdc_courses_dict)
        all_courses.update(other_courses_dict)
        
        return {
            'batch': student.batch,
            'semester': semester,
            'session': session,
            'courses': all_courses,
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
                                    assessment_uids: list) -> Dict:
        """
        Create StudentCourseAssessment entries from assessment UIDs
        OPTIMIZED FOR HIGH VOLUME: 30k students, 800k existing rows
        
        Args:
            student: UGStudentProfile instance
            semester: Target semester (e.g., '3RD')
            assessment_uids: List of CourseStructure UIDs from the payload
                Example: ["uuid1", "uuid2", "uuid3", ...]
            
        Returns:
            Dict with registration details
        """
        from django.db import transaction
        
        # === VALIDATION PHASE (Fast, before expensive queries) ===
        if not assessment_uids:
            raise ValueError("No assessment UIDs provided")
        
        # Limit number of assessments to prevent abuse
        if len(assessment_uids) > 50:
            raise ValueError(f"Too many assessments ({len(assessment_uids)}). Maximum 50 allowed.")
        
        # Get semester number using class constant
        semester_num = SemesterRegistrationService.SEMESTER_MAP.get(semester, 3)
        
        # 1. VALIDATE ELIGIBILITY (Single query with select_related)
        registration = SemesterRegistration.objects.select_related('student').filter(
            student=student,
            sem=semester_num,
            is_open=True
        ).first()
        
        if not registration:
            raise ValueError(f"No open registration window for semester {semester}")
        
        if registration.status == 'REGISTERED':
            raise ValueError(f"Already registered for semester {semester}")
        
        # Check if student is eligible
        if not registration.exam_eligible:
            raise ValueError("Student is not eligible for registration. Please check with administration.")
        
        # Get session and batch (optimize batch query)
        session = registration.session or student.session
        batch_obj = None
        if student.batch:
            batch_obj = UGBatch.objects.only('id', 'name').filter(name=student.batch).first()
        
        # 2. FETCH COURSESTRUCTURE DATA (Optimized query with select_related)
        course_structures = list(
            CourseStructure.objects.filter(
                uid__in=assessment_uids,
                semester=str(semester_num)
            ).select_related('department').only(
                'uid', 'paper_code', 'course_code', 'course_name', 'course_short_name',
                'course_type', 'label', 'max_marks', 'min_marks', 'max_credit',
                'department__id', 'department__name'
            )
        )
        
        if not course_structures:
            raise ValueError("No valid course structures found for provided UIDs")
        
        # Validate all UIDs were found
        found_uids = {str(cs.uid) for cs in course_structures}
        requested_uids = set(assessment_uids)
        missing_uids = requested_uids - found_uids
        
        if missing_uids:
            raise ValueError(f"Invalid assessment UIDs: {', '.join(list(missing_uids)[:5])}")
        
        # 3. CHECK FOR EXISTING REGISTRATIONS (Single bulk query)
        # Build list of (paper_code, label, exam_type) tuples to check
        # Note: exam_type differentiates regular vs back exams
        assessment_keys = [
            (cs.paper_code or cs.course_code, cs.label, 'Regular')  # Default to 'Regular' for new registrations
            for cs in course_structures
        ]
        
        # Get existing assessments in one query using Q objects
        from django.db.models import Q
        existing_query = Q()
        for paper_code, label, exam_type in assessment_keys:
            existing_query |= Q(paper_code=paper_code, label=label, exam_type=exam_type)
        
        existing_assessments = set(
            StudentCourseAssessment.objects.filter(
                student=student,
                semester=str(semester_num),
                session=session
            ).filter(existing_query).values_list('paper_code', 'label', 'exam_type')
        )
        
        # 4. PREPARE BULK CREATE (Build list of objects to create)
        assessments_to_create = []
        registered_assessments = []
        courses_registered = set()
        total_credits = 0
        
        # Get college and degree codes once
        college_code = student.college.code if student.college else None
        degree_code = student.degree.code if student.degree else None
        
        for course_structure in course_structures:
            paper_code = course_structure.paper_code or course_structure.course_code
            label = course_structure.label
            exam_type = 'Regular'  # New registrations are always 'Regular' (back exams handled separately)
            
            # Skip if already exists (including exam_type check)
            if (paper_code, label, exam_type) in existing_assessments:

                continue
            
            # Extract course_type from course_code (e.g., MJC from MJC-3)
            course_code_value = course_structure.course_code
            course_type_value = (
                course_code_value.split('-')[0] 
                if course_code_value and '-' in course_code_value 
                else course_structure.course_type
            )
            
            # Create assessment object (don't save yet)
            assessment = StudentCourseAssessment(
                student=student,
                semester=str(semester_num),
                session=session,
                batch=batch_obj,
                
                # Course info
                paper_code=paper_code,
                course_name=course_structure.course_name,
                course_short_name=course_structure.course_short_name,
                course_code=course_code_value,
                course_type=course_type_value,
                department=course_structure.department,
                
                # Assessment info
                label=label,
                exam_type=exam_type,  # 'Regular' for new registrations
                ind_max_marks=int(course_structure.max_marks) if course_structure.max_marks else 0,
                ind_pass_marks=float(course_structure.min_marks) if course_structure.min_marks else 0,
                
                # Student info
                college_code=college_code,
                degree=degree_code,
            )
            
            assessments_to_create.append(assessment)
            
            # Track for response
            registered_assessments.append({
                'uid': str(course_structure.uid),
                'paper_code': paper_code,
                'course_name': course_structure.course_name,
                'label': label,
                'max_marks': course_structure.max_marks,
                'pass_marks': course_structure.min_marks
            })
            
            # Track unique courses and credits
            if paper_code not in courses_registered:
                courses_registered.add(paper_code)
                total_credits += course_structure.max_credit or 0
        
        # 5. BULK INSERT IN TRANSACTION (Much faster than individual creates)
        with transaction.atomic():
            if assessments_to_create:
                # Use bulk_create for massive performance improvement
                StudentCourseAssessment.objects.bulk_create(
                    assessments_to_create,
                    batch_size=500  # Process in batches of 500
                )
            
            # Update registration status
            registration.status = 'REGISTERED'
            registration.save(update_fields=['status'])
        
        return {
            'success': True,
            'message': f'Successfully registered for Semester {semester}',
            'batch': student.batch,
            'registered_assessments': registered_assessments,
            'total_courses': len(courses_registered),
            'total_credits': total_credits,
            'total_assessments': len(registered_assessments)
        }
