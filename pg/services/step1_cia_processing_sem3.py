"""
Dynamic CIA Processing for PG Students (Ignore Eligibility)

This script is a variation of Step 1 processing that allows any semester.
It focuses on assessments for the specified semester and handles registration creation
while ignoring previous semester history/eligibility.
"""

from typing import Dict
from decimal import Decimal
from django.db import transaction

from pg.models import (
    PGStudentProfile,
    PGExamResult,
    PGExamRegistration,
    PGStudentCourseAssessment,
)
from pg.services.step1_cia_processing import PGCIAResultProcessingService


class PGCIAResultProcessingServiceSem3(PGCIAResultProcessingService):
    """
    Step 1 processing that ignores previous history.
    Focuses only on the specified semester.
    """

    def __init__(self, batch: str = None, semester: str = '1ST', session: str = None, include_all_batches: bool = False, registration_no: str = None, ignore_eligibility: bool = True):
        super().__init__(
            batch=batch, 
            semester=semester, 
            session=session, 
            include_all_batches=include_all_batches, 
            registration_no=registration_no
        )
        # Default to True as per user request to ignore previous sem results
        self.ignore_eligibility = ignore_eligibility

    def _process_student(self, student: PGStudentProfile, dry_run: bool = False, show_detail: bool = False):
        """
        Modified process: 
        Directly calculates result for the specified semester without checking previous history.
        """
        
        # 1. GET CIA ASSESSMENTS
        cia_assessments = PGStudentCourseAssessment.objects.filter(
            student=student,
            semester=self.semester, 
            session=self.session,
            label__icontains='CIA'
        )

        if not cia_assessments.exists():
            # No CIA assessments for this sem - skip student
            return
        
        self.stats['students_with_cia'] += 1
        
        # Show detailed info if requested (Dry Run mode)
        if show_detail:
            print(f"\n{'='*100}")
            print(f"📋 {self.semester} CIA PROCESSING DETAILS")
            print(f"{'='*100}")
            print(f"Student: {student.first_name} {student.last_name}")
            print(f"Reg No:  {student.registration_no}")
            print(f"Dept:    {student.department.name if student.department else 'N/A'}")
            print(f"\nCIA Assessments ({cia_assessments.count()} courses):")
            print(f"{'-'*100}")
            
            for idx, assessment in enumerate(cia_assessments, 1):
                is_pass = False
                if assessment.ind_marks_obtained is not None and assessment.ind_pass_marks is not None:
                    if not assessment.ind_is_absent:
                        is_pass = assessment.ind_marks_obtained >= assessment.ind_pass_marks
                
                status_icon = "✅" if is_pass else "❌"
                print(f"{idx}. {status_icon} {assessment.course_name[:50]:50} | "
                      f"Marks: {assessment.ind_marks_obtained}/{assessment.ind_max_marks} | "
                      f"Pass: {assessment.ind_pass_marks}")

        # 2. CALCULATE CIA STATUS
        # We explicitly skip ANY check for previous semesters
        # This is ensured because we have overridden _process_student and NOT called super()
        cia_passed = self._check_cia_passed(cia_assessments, student, dry_run=dry_run)
        
        if show_detail:
            overall_status = "✅ PASS" if cia_passed else "❌ FAIL"
            print(f"{'-'*100}")
            print(f"Overall {self.semester} CIA Status: {overall_status}")
            print(f"{'='*100}\n")
        
        # 3. UPDATE STATS
        if cia_passed:
            self.stats['cia_pass'] += 1
        else:
            self.stats['cia_fail'] += 1
            if len(self.failed_students) < 10:
                self.failed_students.append(student.registration_no)
        
        # 4. SAVE TO DATABASE (Simulation in Dry Run)
        # We call these methods even in dry_run to update the statistics/stats
        # but the methods themselves will skip the actual DB save if dry_run=True
        
        # Update/Create Result (Always update status)
        self._create_or_update_exam_result(student, cia_passed, dry_run=dry_run)
        
        # If CIA passed, handle registration (Skip if exists, Create if not)
        if cia_passed:
            self._create_exam_registration(student, dry_run=dry_run)

    def _check_cia_passed(self, cia_assessments, student, dry_run: bool = False) -> bool:
        """
        STRICT VERSION: Only checks assessments for the current session.
        Ignores historical passes in previous sessions or result records.
        """
        if not cia_assessments:
            return False
            
        # Group assessments by paper_code
        paper_assessments = {}
        for assessment in cia_assessments:
            code = assessment.paper_code
            if code not in paper_assessments:
                paper_assessments[code] = []
            paper_assessments[code].append(assessment)
            
        all_papers_cleared = True
        
        for code, assessments in paper_assessments.items():
            paper_cleared = False
            for assessment in assessments:
                is_pass = False
                if assessment.ind_marks_obtained is not None and assessment.ind_pass_marks is not None:
                    if not assessment.ind_is_absent:
                        is_pass = assessment.ind_marks_obtained >= assessment.ind_pass_marks
                
                # Update DB if incorrect (standard logic)
                if not dry_run and assessment.ind_is_pass != is_pass:
                    assessment.ind_is_pass = is_pass
                    assessment.save(update_fields=['ind_is_pass', 'updated_at'])
                
                if is_pass:
                    paper_cleared = True
            
            if not paper_cleared:
                all_papers_cleared = False
                break # One fail is enough to fail overall CIA
        
        return all_papers_cleared

    def _create_or_update_exam_result(self, student: PGStudentProfile, cia_passed: bool, dry_run: bool = False):
        """
        Create or update PGExamResult entry - IDEMPOTENT VERSION (Per Session)
        Modified to support dry_run simulation stats.
        """
        # 1. Try to find EXISTING record for this student & semester & SESSION
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
        
        dept_name = student.department.name if student.department else "N/A"
        
        if existing_result:
            # UPDATE existing (for this session)
            if not dry_run:
                existing_result.cia_pass = cia_passed
                existing_result.save(update_fields=['cia_pass', 'updated_at'])
            
            self.stats['exam_results_updated'] += 1
            
        else:
            # CREATE new (for this session)
            if not dry_run:
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

    def _create_exam_registration(self, student: PGStudentProfile, dry_run: bool = False):
        """
        Create exam registration (form fillup) for ESE.
        Only for students who passed CIA.
        Modified to support dry_run simulation stats.

        Policy:
          - If a PGExamRegistration entry already EXISTS  → SKIP (do not update)
          - If it does NOT exist                          → CREATE only
        """
        # Convert semester string to integer (1ST -> 1, 2ND -> 2, etc.)
        sem_map = {'1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4}
        sem_int = sem_map.get(self.semester.upper(), 1)
        dept_name = student.department.name if student.department else "N/A"

        # Check if registration already exists — if so, SKIP entirely
        existing = PGExamRegistration.objects.filter(
            student=student,
            sem=sem_int,
            session=self.session,
        ).first()
        
        if existing:
            # Entry already exists — do NOT update, just skip
            self.stats['exam_registrations_skipped'] += 1
            return

        # No existing entry — CREATE a new one (Skip in dry run)
        if not dry_run:
            PGExamRegistration.objects.create(
                student=student,
                sem=sem_int,
                session=self.session,
                status='PENDING',
                is_open=True,
                exam_type='BACK' # Default for this script
            )
        
        print(f"   [REGISTRATION] CREATE: {student.registration_no:15} | Dept: {dept_name[:30]:30}")
        self.stats['exam_registrations_created'] += 1

    def _print_summary(self):
        """Print specialized summary for Sem 3"""
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
        
        print(f"\nPGExamResult Entries Created:      {self.stats['exam_results_created']:,}")
        print(f"PGExamResult Entries Updated:      {self.stats['exam_results_updated']:,}")
        
        # Only print creates if > 0
        if self.stats['exam_registrations_created'] > 0:
            print(f"PGExamRegistrations Created:       {self.stats['exam_registrations_created']:,}")
            
        print(f"PGExamRegistrations Skipped:       {self.stats['exam_registrations_skipped']:,}  (already existed — not modified)")
        print("="*100)


def run_cia_processing_sem3(batch: str = None, semester: str = '1ST', session: str = None, dry_run: bool = False, include_all_batches: bool = False, registration_no: str = None, ignore_eligibility: bool = True) -> Dict:
    """Convenience function for specialized processing"""
    service = PGCIAResultProcessingServiceSem3(batch, semester, session, include_all_batches, registration_no, ignore_eligibility)
    return service.process(dry_run=dry_run)
