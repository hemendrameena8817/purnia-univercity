"""
Service to create PGStudentCourseAssessment entries for next semester
based on PGExamResult status (PASS/PROMOTED)

This service:
1. Reads PGExamResult records where semester_result is 'PASS' or 'PROMOTED'
2. Creates PGStudentCourseAssessment entries for the next semester
3. Populates assessment records based on course structure

Usage:
    from pg.services.create_next_semester_assessments import NextSemesterAssessmentService
    
    # Create assessments for all eligible students
    NextSemesterAssessmentService.create_assessments_for_eligible_students(
        semester="1ST",
        session="2024-25",
        dry_run=True
    )
    
    # Create assessments for a specific student
    NextSemesterAssessmentService.create_assessments_for_student(
        student_id=123,
        current_semester="1ST",
        session="2024-25",
        dry_run=True
    )
"""

from decimal import Decimal
from typing import Dict, List, Optional
from django.db import transaction
from django.db.models import Q


class NextSemesterAssessmentService:
    """
    Service to create PGStudentCourseAssessment entries for students
    who have passed or been promoted to the next semester
    """
    
    @staticmethod
    def _get_next_semester(current_sem_str: str) -> Optional[int]:
        """Map current semester string to next semester integer"""
        mapping = {
            '1ST': 2, 'I': 2, '1': 2,
            '2ND': 3, 'II': 3, '2': 3,
            '3RD': 4, 'III': 4, '3': 4,
            '4TH': 5, 'IV': 5, '4': 5
        }
        return mapping.get(current_sem_str.upper())
    
    @staticmethod
    def _get_next_semester_str(current_sem_str: str) -> Optional[str]:
        """Get next semester as string"""
        next_sem_num = NextSemesterAssessmentService._get_next_semester(current_sem_str)
        if not next_sem_num:
            return None
        
        mapping = {
            2: '2ND',
            3: '3RD',
            4: '4TH',
            5: '5TH'
        }
        return mapping.get(next_sem_num)
    
    @staticmethod
    def _get_next_session(current_session: str, current_sem_str: str) -> str:
        """
        Calculate the next session based on semester transition.
        
        For 2-year PG courses (4 semesters):
        - Year 1: Sem 1 (2024-25), Sem 2 (2024-25)
        - Year 2: Sem 3 (2025-26), Sem 4 (2025-26)
        
        Session increments when moving from even semester to odd semester.
        """
        sem_map = {'1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4}
        current_sem_val = sem_map.get(current_sem_str.upper(), 1)
        next_sem_val = NextSemesterAssessmentService._get_next_semester(current_sem_str)
        
        if not next_sem_val:
            return current_session
        
        # If moving from even semester to odd semester (e.g., 2→3), increment year
        if current_sem_val % 2 == 0 and next_sem_val % 2 == 1:
            try:
                parts = current_session.split('-')
                if len(parts) == 2:
                    start_year = int(parts[0])
                    end_year = int(parts[1])
                    
                    new_start = start_year + 1
                    new_end = end_year + 1
                    
                    return f"{new_start}-{new_end:02d}"
            except (ValueError, AttributeError):
                pass
        
        return current_session
    
    @staticmethod
    @transaction.atomic
    def create_assessments_for_student(
        student_id: int,
        current_semester: str,
        session: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Create PGStudentCourseAssessment entries for a single student
        if they have passed or been promoted
        
        Args:
            student_id: ID of the student
            current_semester: Current semester (e.g., '1ST', '2ND')
            session: Academic session (e.g., '2024-25')
            dry_run: If True, don't save to database
            
        Returns:
            Dict with status and details
        """
        from pg.models import (
            PGExamResult, PGStudentProfile, PGStudentCourseAssessment,
            PGCourseStructure
        )
        
        try:
            # Check if student exists
            try:
                student = PGStudentProfile.objects.get(id=student_id)
            except PGStudentProfile.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Student with ID {student_id} not found'
                }
            
            # Check PGExamResult for current semester
            exam_result = PGExamResult.objects.filter(
                student_id=student_id,
                semester=current_semester,
                session=session
            ).first()
            
            if not exam_result:
                return {
                    'success': False,
                    'error': f'No exam result found for student {student_id}, semester {current_semester}, session {session}'
                }
            
            # Check if semester_result is PASS or PROMOTED
            if exam_result.semester_result not in ['PASS', 'PROMOTED']:
                return {
                    'success': False,
                    'error': f'Student semester result is {exam_result.semester_result}, not eligible for next semester'
                }
            
            # Get next semester
            next_semester_str = NextSemesterAssessmentService._get_next_semester_str(current_semester)
            if not next_semester_str:
                return {
                    'success': False,
                    'error': f'No next semester found for {current_semester}'
                }
            
            # Get next session
            next_session = NextSemesterAssessmentService._get_next_session(session, current_semester)
            
            # Get course structure for next semester
            course_structures = PGCourseStructure.objects.filter(
                semester=next_semester_str.replace('ST', '').replace('ND', '').replace('RD', '').replace('TH', '')[0],
                department=student.department,
                batch=student.program.batches.first() if student.program else None
            )
            
            if not course_structures.exists():
                # Try without batch filter
                course_structures = PGCourseStructure.objects.filter(
                    semester=next_semester_str.replace('ST', '').replace('ND', '').replace('RD', '').replace('TH', '')[0],
                    department=student.department
                )
            
            if not course_structures.exists():
                return {
                    'success': False,
                    'error': f'No course structure found for semester {next_semester_str}, department {student.department}'
                }
            
            # Create assessment entries
            created_assessments = []
            
            for course_structure in course_structures:
                # Only process CIA/MID_SEM entries
                # Skip if this is an ESE entry
                if course_structure.label and 'ESE' in course_structure.label.upper():
                    continue
                
                # Use CIA as the label for all CIA assessments
                labels = ['CIA']
                
                # Prefix paper code with PG if not already present
                final_paper_code = course_structure.paper_code
                if final_paper_code and not final_paper_code.startswith('PG'):
                    final_paper_code = f"PG{final_paper_code}"
                
                for label in labels:
                    # Check if assessment already exists
                    existing = PGStudentCourseAssessment.objects.filter(
                        student=student,
                        semester=next_semester_str,
                        session=next_session,
                        paper_code=final_paper_code,
                        label=label
                    ).first()
                    
                    if existing:
                        print(f"Assessment already exists for {student.registration_no}, "
                              f"semester {next_semester_str}, paper {final_paper_code}, label {label}")
                        continue
                    
                    # Use max_marks and min_marks directly from PGCourseStructure
                    # Since PGCourseStructure has separate rows for CIA and ESE with correct values
                    ind_max_marks = int(course_structure.max_marks) if course_structure.max_marks else None
                    ind_pass_marks = course_structure.min_marks if course_structure.min_marks else None
                    
                    # Fallback calculation if max_marks is not set in course structure
                    if ind_max_marks is None:
                        if 'CIA' in label.upper():
                            ind_max_marks = 30  # Default CIA marks
                            ind_pass_marks = Decimal('12.00')  # 40% of 30
                        elif 'ESE' in label.upper():
                            ind_max_marks = 70  # Default ESE marks
                            ind_pass_marks = Decimal('28.00')  # 40% of 70
                    
                    # Get batch object - PGStudentCourseAssessment.batch is a ForeignKey to PGBatch
                    batch_obj = None
                    if student.batch:
                        # Try to find batch by name
                        from pg.models import PGBatch
                        batch_obj = PGBatch.objects.filter(name=student.batch).first()
                    
                    # Fallback to program's batch if not found
                    if not batch_obj and student.program:
                        batch_obj = student.program.batches.first()
                    
                    # Create assessment entry
                    assessment_data = {
                        'student': student,
                        'course_name': course_structure.course_name,
                        'course_short_name': course_structure.course_short_name,
                        'course_type': course_structure.course_type,
                        'course_code': course_structure.code,  # Use 'code' field instead of 'course_code'
                        'paper_code': final_paper_code,
                        'semester': next_semester_str,
                        'label': label,
                        'department': student.department,
                        'degree': student.degree.short_name if student.degree else None,
                        'session': next_session,
                        'batch': batch_obj,  # PGBatch object, not string
                        'college_code': student.college.college_code if student.college else None,
                        'exam_type': 'Regular',
                        
                        # Individual marks fields
                        'ind_max_marks': ind_max_marks,
                        'ind_pass_marks': ind_pass_marks,
                        'ind_is_absent': False,  # Not absent by default
                        'ind_marks_obtained': None,
                        'ind_grace_obtained': Decimal('0.00'),
                        'ind_final_marks_obtained': None,
                        'ind_is_pass': None,
                        
                        # Combined fields - Leave empty, will be filled after marks entry
                        'comb_max_marks': None,
                        'comb_max_credits': None,
                        'comb_pass_marks': None,
                        
                        # Course fields - Leave empty, will be filled after marks entry
                        'course_max_marks': None,
                        'course_max_credits': None,
                        'course_pass_marks': None,
                    }
                    
                    if not dry_run:
                        assessment = PGStudentCourseAssessment.objects.create(**assessment_data)
                        created_assessments.append(assessment)
                        print(f"Created assessment: {student.registration_no} - {next_semester_str} - "
                              f"{course_structure.paper_code} - {label}")
                    else:
                        print(f"[DRY RUN] Would create assessment: {student.registration_no} - "
                              f"{next_semester_str} - {course_structure.paper_code} - {label}")
                        created_assessments.append(assessment_data)
            
            return {
                'success': True,
                'student_id': student_id,
                'student_registration': student.registration_no,
                'current_semester': current_semester,
                'next_semester': next_semester_str,
                'next_session': next_session,
                'semester_result': exam_result.semester_result,
                'assessments_created': len(created_assessments),
                'dry_run': dry_run
            }
            
        except Exception as e:
            return {
                'success': False,
                'student_id': student_id,
                'error': str(e)
            }
    

    @staticmethod
    def create_assessments_for_eligible_students(
        semester: str,
        session: str,
        dry_run: bool = False,
        limit: Optional[int] = None,
        batch: Optional[str] = None
    ) -> Dict:
        """
        Create PGStudentCourseAssessment entries for all students
        who have passed or been promoted from the given semester
        
        Args:
            semester: Semester to check (e.g., '1ST', '2ND')
            session: Academic session (e.g., '2024-25')
            dry_run: If True, don't save to database
            limit: Optional limit on number of students to process
            batch: Optional batch name to filter students
            
        Returns:
            Dict with summary of results
        """
        from pg.models import PGExamResult
        
        # Get all exam results with PASS or PROMOTED status
        eligible_results = PGExamResult.objects.filter(
            semester=semester,
            session=session,
            semester_result__in=['PASS', 'PROMOTED']
        )
        
        if batch:
            # Filter by student's batch
            # PGStudentProfile has 'batch' CharField.
            eligible_results = eligible_results.filter(student__batch=batch)
            print(f"Filtering by batch: {batch}")
        
        if limit:
            eligible_results = eligible_results[:limit]
        
        total = eligible_results.count()
        print(f"\nFound {total} eligible students for semester {semester}, session {session}" + (f", batch {batch}" if batch else ""))
        
        results = {
            'total_eligible': total,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for idx, exam_result in enumerate(eligible_results, 1):
            print(f"\nProcessing {idx}/{total}: Student {exam_result.student.registration_no}")
            
            result = NextSemesterAssessmentService.create_assessments_for_student(
                student_id=exam_result.student.id,
                current_semester=semester,
                session=session,
                dry_run=dry_run
            )
            
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'student_id': exam_result.student.id,
                    'registration_no': exam_result.student.registration_no,
                    'error': result.get('error', 'Unknown error')
                })
        
        return results


# Standalone script execution
if __name__ == '__main__':
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    django.setup()
    
    # Example usage
    print("=" * 80)
    print("Next Semester Assessment Creation Service")
    print("=" * 80)
    
    # Configuration
    SEMESTER = "2ND"
    SESSION = "2024-25"
    DRY_RUN = True  # Set to False to actually create records
    LIMIT = None  # Set to a number to limit processing
    
    print(f"\nConfiguration:")
    print(f"  Semester: {SEMESTER}")
    print(f"  Session: {SESSION}")
    print(f"  Dry Run: {DRY_RUN}")
    print(f"  Limit: {LIMIT or 'None'}")
    print()
    
    # Run the service
    results = NextSemesterAssessmentService.create_assessments_for_eligible_students(
        semester=SEMESTER,
        session=SESSION,
        dry_run=DRY_RUN,
        limit=LIMIT
    )
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Eligible Students: {results['total_eligible']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"  - Student {error['registration_no']}: {error['error']}")
        
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")
    
    print("=" * 80)
