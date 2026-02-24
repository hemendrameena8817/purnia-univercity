"""
Semester 3 Specialized CIA Processing for PG Students

This script is a variation of Step 1 processing, specifically for 3rd Semester.
It focuses exclusively on 3rd Semester assessments and handles registration creation.
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
    Specialized Step 1 processing for Semester 3.
    Focuses only on 3RD Semester and ignores previous history.
    """

    def __init__(self, batch: str = None, session: str = None, include_all_batches: bool = False, registration_no: str = None, ignore_eligibility: bool = True):
        # Hardcode semester to 3RD
        super().__init__(
            batch=batch, 
            semester='3RD', 
            session=session, 
            include_all_batches=include_all_batches, 
            registration_no=registration_no
        )
        # Default to True as per user request to ignore previous sem results
        self.ignore_eligibility = ignore_eligibility

    def _process_student(self, student: PGStudentProfile, dry_run: bool = False, show_detail: bool = False):
        """
        Modified process: 
        Directly calculates 3rd Semester result without checking previous history (Sem 1/Sem 2).
        """
        
        # 1. GET 3RD SEMESTER CIA ASSESSMENTS
        cia_assessments = PGStudentCourseAssessment.objects.filter(
            student=student,
            semester=self.semester, # This is '3RD'
            session=self.session,
            label__icontains='CIA'
        )

        if not cia_assessments.exists():
            # No CIA assessments for 3rd sem - skip student
            return
        
        self.stats['students_with_cia'] += 1
        
        # Show detailed info if requested (Dry Run mode)
        if show_detail:
            print(f"\n{'='*100}")
            print(f"📋 3RD SEMESTER CIA PROCESSING DETAILS")
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

        # 2. CALCULATE 3RD SEM CIA STATUS
        # We explicitly skip ANY check for previous semesters (1st/2nd)
        # This is ensured because we have overridden _process_student and NOT called super()
        cia_passed = self._check_cia_passed(cia_assessments, student, dry_run=dry_run)
        
        if show_detail:
            overall_status = "✅ PASS" if cia_passed else "❌ FAIL"
            print(f"{'-'*100}")
            print(f"Overall 3rd Sem CIA Status: {overall_status}")
            print(f"{'='*100}\n")
        
        # 3. UPDATE STATS
        if cia_passed:
            self.stats['cia_pass'] += 1
        else:
            self.stats['cia_fail'] += 1
            if len(self.failed_students) < 10:
                self.failed_students.append(student.registration_no)
        
        # 4. SAVE TO DATABASE
        if not dry_run:
            # Update/Create 3rd Sem Result (Always update status)
            self._create_or_update_exam_result(student, cia_passed)
            
            # If 3rd Sem CIA passed, handle registration (Skip if exists, Create if not)
            if cia_passed:
                self._create_exam_registration(student)

    def _create_exam_registration(self, student: PGStudentProfile):
        """
        Create exam registration (form fillup) for Semester 3 ESE.
        Only for students who passed CIA.

        Policy:
          - If a PGExamRegistration entry already EXISTS  → SKIP (do not update)
          - If it does NOT exist                          → CREATE only
        """
        # Semester 3 is explicitly handled here
        sem_int = 3

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

        # No existing entry — CREATE a new one
        PGExamRegistration.objects.create(
            student=student,
            sem=sem_int,
            session=self.session,
            status='PENDING',
            is_open=True,
            exam_type='REGULAR' # Default for this script
        )
        self.stats['exam_registrations_created'] += 1


def run_cia_processing_sem3(batch: str = None, session: str = None, dry_run: bool = False, include_all_batches: bool = False, registration_no: str = None, ignore_eligibility: bool = True) -> Dict:
    """Convenience function for Sem 3 specialized processing"""
    service = PGCIAResultProcessingServiceSem3(batch, session, include_all_batches, registration_no, ignore_eligibility)
    return service.process(dry_run=dry_run)
