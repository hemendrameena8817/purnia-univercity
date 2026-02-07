"""
Step 1: PG CIA Result Processing Service

Processes MID_TERM (CIA equivalent) assessment results for a batch and semester:
1. Checks if students passed ALL MID_TERM assessments
2. Creates PGExamResult entries with cia_pass flag (MID_TERM status)
3. Creates PGExamRegistration entries for END_TERM (ESE) if MID_TERM passed
4. Sets initial values for END_TERM processing

Note: PG uses MID_TERM/END_TERM instead of CIA/ESE terminology.

This is the FIRST step in the PG result processing pipeline.
Run this after MID_TERM marks have been entered for all students.
"""
# python pg/services/run_step1_cia_processing.py --batch 2023-25 --semester 1ST --session 2024-25

from decimal import Decimal
from typing import Dict, List
from django.db import transaction
from django.db.models import Q

from pg.models import (
    PGStudentProfile,
    PGStudentCourseAssessment,
    PGExamResult,
    PGExamRegistration,
)


class PGCIAResultProcessingService:
    """
    Step 1: PG CIA Result Processing
    
    Processes CIA results and creates PGExamResult entries
    """
    
    ################################################################################
    # 1. INITIALIZATION & SETUP
    ################################################################################
    
    def __init__(self, batch: str, semester: str, session: str):
        """
        Initialize service
        
        Args:
            batch: Batch code (e.g., '23-25')
            semester: Semester code (e.g., '1ST', '2ND')
            session: Academic session (e.g., '2024-25')
        """
        self.batch = batch
        self.semester = semester
        self.session = session
        self.stats = {
            'total_students': 0,
            'students_with_cia': 0,
            'cia_pass': 0,
            'cia_fail': 0,
            'exam_results_created': 0,
            'exam_results_updated': 0,
            'exam_registrations_created': 0,
        }
        self.failed_students = []  # Track failed student reg numbers
    
    def process(self, dry_run: bool = False) -> Dict:
        """
        Main processing method
        
        Args:
            dry_run: If True, don't save to database (testing mode)
            
        Returns:
            Dictionary with processing statistics
        """
        self._print_header()
        
        # Get batch object first
        from pg.models import PGBatch
        try:
            batch_objs = list(PGBatch.objects.filter(name=self.batch))
            if not batch_objs:
                raise PGBatch.DoesNotExist
        except PGBatch.DoesNotExist:
            print(f"\n❌ ERROR: Batch '{self.batch}' not found in database")
            return self.stats
        
        # Get all students in batch who have assessments in this semester
        # PGBatch.name is usually what PGStudentProfile.batch (CharField) stores.
        students = PGStudentProfile.objects.filter(
            batch=self.batch,
            course_assessments__semester=self.semester
        ).distinct()
        self.stats['total_students'] = students.count()
        
        print(f"\n📊 Found {self.stats['total_students']:,} students in batch {self.batch} for semester {self.semester}")
        print(f"{'='*100}\n")
        
        # Process each student
        if not dry_run:
            with transaction.atomic():
                self._process_all_students(students)
        else:
            print("🔍 DRY RUN MODE - No database changes will be made\n")
            self._process_all_students(students, dry_run=True)
        
        # Print summary
        self._print_summary()
        
        return self.stats
    
    def _process_all_students(self, students, dry_run: bool = False):
        """Process all students in batch"""
        first_student_shown = False
        
        for idx, student in enumerate(students.iterator(), 1):
            # Show detailed info for first student in dry-run mode
            show_detail = dry_run and not first_student_shown
            if show_detail:
                first_student_shown = True
                
            self._process_student(student, dry_run=dry_run, show_detail=show_detail)
            
            # Progress indicator every 1000 students
            if idx % 1000 == 0:
                print(f"  ⏳ Processed {idx:,}/{self.stats['total_students']:,} students...")

    ################################################################################
    # 2. STUDENT CIA RESULT PROCESSING LOGIC
    ################################################################################
    
    def _process_student(self, student: PGStudentProfile, dry_run: bool = False, show_detail: bool = False):
        """
        Process CIA results for a single student
        
        Args:
            student: PGStudentProfile instance
            dry_run: If True, don't save to database
            show_detail: If True, print detailed assessment information
        """
        # Get all MID_TERM (CIA equivalent) assessments for this student in semester
        cia_assessments = PGStudentCourseAssessment.objects.filter(
            student=student,
            semester=self.semester,
            label__icontains='MID_TERM'  # PG uses MID_TERM instead of CIA
        )

        # CHECK PROMOTION STATUS (For Semesters > 1)
        # Convert semester to int to check if > 1
        sem_map_int = {'1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4}
        current_sem_num = sem_map_int.get(self.semester.upper())
        
        if current_sem_num and current_sem_num > 1:
            # Find previous semester string
            # Invert map to find string from int
            prev_sem_num = current_sem_num - 1
            prev_sem_str = next((k for k, v in sem_map_int.items() if v == prev_sem_num), None)
            
            if prev_sem_str:
                # Check previous semester result
                # Handle potential duplicates (e.g. from different sessions) by taking the latest updated one
                prev_result = PGExamResult.objects.filter(
                    student=student,
                    semester=prev_sem_str
                ).order_by('-updated_at').first()
                
                if prev_result:
                    # Check if passed ALL CIA in previous semester
                    # User requirement: "check he is pass all cia in his previous sem"
                    if not prev_result.cia_pass:
                        if show_detail:
                            print(f"⚠️ SKIPPING: Student failed CIA in {prev_sem_str} (cia_pass: {prev_result.cia_pass})")
                        return
                    
                    # Also check for valid promotion status
                    if prev_result.semester_result not in ['PASS', 'PROMOTED']:
                       if show_detail:
                           print(f"⚠️ SKIPPING: Student not promoted from {prev_sem_str} (Status: {prev_result.semester_result})")
                       return
                else:
                    if show_detail:
                        print(f"⚠️ SKIPPING: No result record found for {prev_sem_str}")
                    return
        
        if not cia_assessments.exists():
            # No CIA assessments found - skip
            return
        
        self.stats['students_with_cia'] += 1
        
        # Show detailed info if requested
        if show_detail:
            print(f"\n{'='*100}")
            print(f"📋 EXAMPLE STUDENT CIA RESULT DETAILS")
            print(f"{'='*100}")
            print(f"Student: {student.first_name} {student.last_name}")
            print(f"Reg No:  {student.registration_no}")
            print(f"Batch:   {student.batch if student.batch else 'N/A'}")
            print(f"Dept:    {student.department.name if student.department else 'N/A'}")
            print(f"\nMID_TERM Assessments ({cia_assessments.count()} courses):")
            print(f"{'-'*100}")
            
            for idx, assessment in enumerate(cia_assessments, 1):
                # Calculate pass/fail status
                is_pass = False
                if assessment.ind_marks_obtained is not None and assessment.ind_pass_marks is not None:
                    if not assessment.ind_is_absent:
                        is_pass = assessment.ind_marks_obtained >= assessment.ind_pass_marks
                
                status_icon = "✅" if is_pass else "❌"
                print(f"{idx}. {status_icon} {assessment.course_name[:50]:50} | "
                      f"Marks: {assessment.ind_marks_obtained}/{assessment.ind_max_marks} | "
                      f"Pass: {assessment.ind_pass_marks} | "
                      f"Status: {'PASS' if is_pass else 'FAIL'}")
            
        # Check if student passed ALL CIA assessments
        cia_passed = self._check_cia_passed(cia_assessments, dry_run=dry_run)
        
        if show_detail:
            overall_status = "✅ PASS" if cia_passed else "❌ FAIL"
            print(f"{'-'*100}")
            print(f"Overall CIA Status: {overall_status}")
            print(f"{'='*100}\n")
        
        # Update stats
        if cia_passed:
            self.stats['cia_pass'] += 1
        else:
            self.stats['cia_fail'] += 1
            # Track failed students (limit to first 10 for display)
            if len(self.failed_students) < 10:
                self.failed_students.append(student.registration_no)
        
        # Create or update PGExamResult and PGExamRegistration
        if not dry_run:
            self._create_or_update_exam_result(student, cia_passed)
            
            # If CIA passed, create exam registration
            if cia_passed:
                self._create_exam_registration(student)

    ################################################################################
    # 3. HELPER UPDATERS & CHECKS
    ################################################################################
    
    def _check_cia_passed(self, cia_assessments, dry_run: bool = False) -> bool:
        """
        Check if student passed ALL CIA assessments
        
        Passing Criteria:
        - Student must pass EVERY CIA assessment (Theory, Practical, etc.)
        - Calculates pass/fail based on marks obtained vs pass marks
        - ALSO UPDATES ind_is_pass field in database if incorrect
        
        Args:
            cia_assessments: QuerySet of CIA assessments
            dry_run: If True, don't update database
            
        Returns:
            True if passed all CIA, False otherwise
        """
        all_passed = True
        
        # Check each assessment
        for assessment in cia_assessments:
            is_pass = False
            
            # Calculate pass/fail based on actual marks
            if assessment.ind_marks_obtained is not None and assessment.ind_pass_marks is not None:
                # If absent, mark as fail
                if assessment.ind_is_absent:
                    is_pass = False
                else:
                    # Pass if marks obtained >= pass marks
                    is_pass = assessment.ind_marks_obtained >= assessment.ind_pass_marks
            elif assessment.ind_is_absent:
                # If absent but no marks data, still mark as fail
                is_pass = False
            
            # Update ind_is_pass in database if incorrect and not dry run
            if not dry_run and assessment.ind_is_pass != is_pass:
                assessment.ind_is_pass = is_pass
                assessment.save(update_fields=['ind_is_pass', 'updated_at'])
            
            # Track overall pass status
            if not is_pass:
                all_passed = False
        
        # Passed all CIA assessments
        return all_passed
    
    def _create_or_update_exam_result(self, student: PGStudentProfile, cia_passed: bool):
        """
        Create or update PGExamResult entry - IDEMPOTENT VERSION
        
        Args:
            student: PGStudentProfile instance
            cia_passed: Whether student passed CIA
        """
        # 1. Try to find EXISTING record for this student & semester (ignoring session initially)
        # This handles cases where 'session' string might differ slightly (2024-25 vs 2024-2025)
        # or if we just want to update the existing record for this semester.
        
        existing_result = PGExamResult.objects.filter(
            student=student,
            semester=self.semester
        ).first()
        
        # 2. If not found, try normalized semester (e.g. '1' vs '1ST')
        if not existing_result:
            sem_map = {'1ST': '1', '2ND': '2', '3RD': '3', '4TH': '4'}
            normalized_sem = sem_map.get(self.semester.upper())
            if normalized_sem:
                 existing_result = PGExamResult.objects.filter(
                    student=student,
                    semester=normalized_sem
                ).first()
        
        if existing_result:
            # UPDATE existing
            existing_result.cia_pass = cia_passed
            existing_result.session = self.session # Update to current session string
            existing_result.semester = self.semester # Update to current semester string
            
            # Reset status if it was pending or handle logic solely for CIA update?
            # We only update CIA status here. 
            existing_result.save(update_fields=['cia_pass', 'session', 'semester', 'updated_at'])
            self.stats['exam_results_updated'] += 1
            
        else:
            # CREATE new
            PGExamResult.objects.create(
                student=student,
                semester=self.semester,
                session=self.session,
                cia_pass=cia_passed,
                semester_result='PENDING',
                semester_max_credit=0,
                semester_credit_earned=0,
                sgpa=Decimal('0.00'),
                is_legacy=False,
            )
            self.stats['exam_results_created'] += 1
            
    def _create_exam_registration(self, student: PGStudentProfile):
        """
        Create exam registration (form fillup) for ESE
        Only for students who passed CIA
        """
        # Convert semester string to integer (1ST -> 1, 2ND -> 2, etc.)
        sem_map = {
            '1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4,
        }
        sem_int = sem_map.get(self.semester, 1)  # Default to 1 if not found
        
        # Check if registration already exists
        registration, created = PGExamRegistration.objects.get_or_create(
            student=student,
            sem=sem_int,
            defaults={
                'status': 'PENDING',
                'is_open': True,
                'session': self.session,
            }
        )
        
        if created:
            self.stats['exam_registrations_created'] += 1

    ################################################################################
    # 4. REPORTING UTILITIES
    ################################################################################
    
    def _print_header(self):
        """Print processing header"""
        print("\n" + "="*100)
        print("📊 STEP 1: PG CIA RESULT PROCESSING")
        print("="*100)
        print(f"Batch:    {self.batch}")
        print(f"Semester: {self.semester}")
        print(f"Session:  {self.session}")
        print("="*100)
    
    def _print_summary(self):
        """Print processing summary"""
        print("\n" + "="*100)
        print("📊 PROCESSING COMPLETE - SUMMARY")
        print("="*100)
        print(f"\nTotal Students in Batch:     {self.stats['total_students']:,}")
        print(f"Students with CIA Data:      {self.stats['students_with_cia']:,}")
        print(f"\n✅ CIA PASS:                  {self.stats['cia_pass']:,} ({self._percentage(self.stats['cia_pass'])}%)")
        print(f"❌ CIA FAIL:                  {self.stats['cia_fail']:,} ({self._percentage(self.stats['cia_fail'])}%)")
        
        # Display failed students if any
        if self.failed_students:
            print(f"\n📋 Failed Student Registration Numbers (showing {len(self.failed_students)}):")
            for idx, reg_no in enumerate(self.failed_students, 1):
                print(f"   {idx}. {reg_no}")
        
        print(f"\nPGExamResult Entries Created: {self.stats['exam_results_created']:,}")
        print(f"PGExamResult Entries Updated: {self.stats['exam_results_updated']:,}")
        print(f"PGExamRegistrations Created:  {self.stats['exam_registrations_created']:,}")
        print("="*100)
    
    def _percentage(self, count: int) -> str:
        """Calculate percentage of students with CIA data"""
        if self.stats['students_with_cia'] == 0:
            return "0.00"
        return f"{(count / self.stats['students_with_cia']) * 100:.2f}"


def run_cia_processing(batch: str, semester: str, session: str, dry_run: bool = False) -> Dict:
    """
    Convenience function to run Step 1: PG CIA Result Processing
    
    Args:
        batch: Batch code (e.g., '23-25')
        semester: Semester code (e.g., '1ST')
        session: Academic session (e.g., '2024-25')
        dry_run: If True, don't save to database
        
    Returns:
        Dictionary with processing statistics
    """
    service = PGCIAResultProcessingService(batch, semester, session)
    return service.process(dry_run=dry_run)
