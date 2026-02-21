"""
Step 1: CIA Processing for PG Students

Processes CIA (Internal Assessment) results for a batch and semester:
1. Checks if students passed ALL CIA assessments
2. Creates PGExamResult entries with cia_pass flag (CIA status)
3. Creates PGExamRegistration entries for ESE if CIA passed
4. Sets initial values for ESE processing

Note: PG uses CIA/ESE terminology.

Usage Examples:
    # Regular batch processing (dry run)
    python pg/services/run_step1_cia_processing.py --batch 2024-26 --semester 1ST --session 2024-25 --dry-run
    
    # Back paper processing - includes all batches in session (dry run)
    python pg/services/run_step1_cia_processing.py --batch 2024-26 --semester 1ST --session 2024-25 --include-all-batches --dry-run
    
    # Production run (saves to database)
    python pg/services/run_step1_cia_processing.py --batch 2024-26 --semester 1ST --session 2024-25
    
    # Back paper production run
    python pg/services/run_step1_cia_processing.py --batch 2024-26 --semester 1ST --session 2024-25 --include-all-batches


# Dry run first (recommended)
python pg/services/run_step1_cia_processing.py \
    --semester 3RD \
    --session 2024-25 \
    --registration-no PU2024001 \
    --dry-run

# Production run
python pg/services/run_step1_cia_processing.py \
    --semester 3RD \
    --session 2024-25 \
    --registration-no PU2024001
Note: Run this after CIA marks have been entered for all students.
"""

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
    
    def __init__(self, batch: str = None, semester: str = None, session: str = None, include_all_batches: bool = False, registration_no: str = None):
        """
        Initialize service
        
        Args:
            batch: Batch code (e.g., '23-25') (Optional)
            semester: Semester code (e.g., '1ST', '2ND')
            session: Academic session (e.g., '2024-25')
            include_all_batches: If True, includes students from all batches who have
                               assessments in this session (for back paper processing)
            registration_no: If set, process only this single student
        """
        self.batch = batch
        self.semester = semester
        self.session = session
        self.include_all_batches = include_all_batches
        self.registration_no = registration_no
        
        if not self.batch and not self.registration_no:
            self.include_all_batches = True
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
        
        # Get batch object first (if needed)
        from pg.models import PGBatch
        
        if self.batch and not self.include_all_batches:
            try:
                batch_objs = list(PGBatch.objects.filter(name=self.batch))
                if not batch_objs:
                    raise PGBatch.DoesNotExist
            except PGBatch.DoesNotExist:
                print(f"\n❌ ERROR: Batch '{self.batch}' not found in database")
                return self.stats
        
        # Get students based on filtering mode
        if self.registration_no:
            # Single student mode
            students = PGStudentProfile.objects.filter(
                registration_no=self.registration_no
            ).distinct()
            print(f"\n📊 Processing SINGLE student: {self.registration_no}")
        elif self.include_all_batches:
            # Include ALL students with assessments in this session (for back papers)
            students = PGStudentProfile.objects.filter(
                course_assessments__semester=self.semester,
                course_assessments__session=self.session
            ).distinct()
            print(f"\n📊 Processing ALL batches with assessments in session {self.session}")
        else:
            # Original logic: only students from specified batch
            students = PGStudentProfile.objects.filter(
                batch=self.batch,
                course_assessments__semester=self.semester
            ).distinct()
            print(f"\n📊 Found students in batch {self.batch} for semester {self.semester}")
        
        self.stats['total_students'] = students.count()
        print(f"   Total students to process: {self.stats['total_students']:,}")
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
        # Get all CIA (Internal Assessment) assessments for this student in semester
        cia_assessments = PGStudentCourseAssessment.objects.filter(
            student=student,
            semester=self.semester,
            session=self.session,
            label__icontains='CIA'  # PG uses CIA for internal assessment
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
                    if prev_result.semester_result not in ['PASS', 'PROMOTED', 'QUALIFIED']:
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
            print(f"\nCIA Assessments ({cia_assessments.count()} courses):")
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
        cia_passed = self._check_cia_passed(cia_assessments, student, dry_run=dry_run)
        
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
    
    
    def _check_cia_passed(self, cia_assessments, student, dry_run: bool = False) -> bool:
        """
        Check if student passed ALL CIA assessments (Grouped by Paper Code)
        
        Passing Criteria:
        - For each unique paper_code, the student must have at least ONE passed attempt (Best of).
        - If any paper has NO passed attempts, then the student fails CIA.
        
        Args:
            cia_assessments: QuerySet of CIA assessments (includes usage from multiple sessions)
            student: The student object
            dry_run: If True, don't update database
            
        Returns:
            True if passed all CIA, False otherwise
        """
        if not cia_assessments:
            return True # Should not happen based on caller logic, or implies no requirement? Caller handles empty check.
            
        # Group assessments by paper_code
        paper_assessments = {}
        for assessment in cia_assessments:
            code = assessment.paper_code
            if code not in paper_assessments:
                paper_assessments[code] = []
            paper_assessments[code].append(assessment)
            
        all_papers_cleared = True
        
        for code, assessments in paper_assessments.items():
            # Check if ANY attempt for this paper is passed
            paper_cleared = False
            
            for assessment in assessments:
                is_pass = False
                
                # Calculate pass/fail based on actual marks
                if assessment.ind_marks_obtained is not None and assessment.ind_pass_marks is not None:
                    if assessment.ind_is_absent:
                        is_pass = False
                    else:
                        is_pass = assessment.ind_marks_obtained >= assessment.ind_pass_marks
                elif assessment.ind_is_absent:
                    is_pass = False
                
                # Update ind_is_pass in database if incorrect and not dry run
                if not dry_run and assessment.ind_is_pass != is_pass:
                    assessment.ind_is_pass = is_pass
                    assessment.save(update_fields=['ind_is_pass', 'updated_at'])
                
                if is_pass:
                    paper_cleared = True
            
            if not paper_cleared:
                # [NEW] Check History: If not cleared in current session, check previous sessions
                # This handles cases where student passed earlier but re-appeared and failed,
                # or if we are processing a mix of current/back papers.
                historical_pass = PGStudentCourseAssessment.objects.filter(
                    student=student,
                    paper_code=code,
                    label__icontains='CIA',
                    ind_is_pass=True
                ).exclude(session=self.session).exists()
                
                if historical_pass:
                    paper_cleared = True

            if not paper_cleared:
                all_papers_cleared = False
        
        # Passed all CIA assessments?
        if all_papers_cleared:
            return True
            
        # If NOT passed based on current assessments (or no current assessments), 
        # check if they passed CIA in a PREVIOUS attempt for this SAME semester.
        # ... (rest of logic)
            
        # If NOT passed based on current assessments (or no current assessments), 
        # check if they passed CIA in a PREVIOUS attempt for this SAME semester.
        # This handles cases where a student is retaking the semester (back paper)
        # but already cleared internal assessments in the past.
        
        # We need to find valid previous results for this student + semester
        # But we must exclude the result we are about to create/update for THIS session
        # (Though usually that record wouldn't exist or be updated yet in this flow, safe to check excluding current session potentially?)
        # Actually simplest is to just check ANY record for this semester where cia_pass is True.
        
        # Normalized semester for lookup
        normalized_sem = self.semester
        if normalized_sem.upper() in ['1ST', '2ND', '3RD', '4TH']:
             sem_map = {'1ST': '1', '2ND': '2', '3RD': '3', '4TH': '4'}
             normalized_sem = sem_map.get(self.semester.upper(), self.semester)

        # Check for any existing exam result where CIA is passed for this semester
        # Note: cia_assessments[0].student is safe because _process_student returns early if no assessments
        student = cia_assessments[0].student if cia_assessments else None
        
        if not student:
            return False

        previous_pass = PGExamResult.objects.filter(
            Q(semester=self.semester) | Q(semester=normalized_sem),
            student=student,
            cia_pass=True
        ).exists()
        
        if previous_pass:
            if not dry_run:
                 # Logic: If they passed previously, we trust that.
                 pass
            return True
            
        return False
    
    def _create_or_update_exam_result(self, student: PGStudentProfile, cia_passed: bool):
        """
        Create or update PGExamResult entry - IDEMPOTENT VERSION (Per Session)
        
        Args:
            student: PGStudentProfile instance
            cia_passed: Whether student passed CIA
        """
        # 1. Try to find EXISTING record for this student & semester & SESSION
        # We MUST filter by session to avoid overwriting history (e.g., 2023-24 result).
        
        existing_result = PGExamResult.objects.filter(
            student=student,
            semester=self.semester,
            session=self.session
        ).first()
        
        # 2. If not found, try normalized semester (e.g. '1' vs '1ST') but SAME SESSION
        if not existing_result:
            sem_map = {'1ST': '1', '2ND': '2', '3RD': '3', '4TH': '4'}
            normalized_sem = sem_map.get(self.semester.upper())
            if normalized_sem:
                 existing_result = PGExamResult.objects.filter(
                    student=student,
                    semester=normalized_sem,
                    session=self.session
                ).first()
        
        if existing_result:
            # UPDATE existing (for this session)
            existing_result.cia_pass = cia_passed
            # session and semester are already correct
            
            existing_result.save(update_fields=['cia_pass', 'updated_at'])
            self.stats['exam_results_updated'] += 1
            
        else:
            # CREATE new (for this session)
            # This preserves previous sessions' results!
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
            session=self.session,
            defaults={
                'status': 'PENDING',
                'is_open': True,
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


def run_cia_processing(batch: str = None, semester: str = None, session: str = None, dry_run: bool = False, include_all_batches: bool = False, registration_no: str = None) -> Dict:
    """
    Convenience function to run Step 1: PG CIA Result Processing
    
    Args:
        batch: Batch code (e.g., '23-25') - Optional
        semester: Semester code (e.g., '1ST')
        session: Academic session (e.g., '2024-25')
        dry_run: If True, don't save to database
        include_all_batches: If True, includes students from all batches (for back papers)
        registration_no: If set, process only this single student
        
    Returns:
        Dictionary with processing statistics
    """
    service = PGCIAResultProcessingService(batch, semester, session, include_all_batches, registration_no)
    return service.process(dry_run=dry_run)
