"""
Step 1: CIA Result Processing Service

Processes CIA assessment results for a batch and semester:
1. Checks if students passed ALL CIA assessments
2. Creates UGExamResult entries with cia_pass flag
3. Creates ExamRegistration entries for ESE if CIA passed
4. Sets initial values for ESE processing

This is the FIRST step in the result processing pipeline.
Run this after CIA marks have been entered for all students.
"""

from decimal import Decimal
from typing import Dict, List
from django.db import transaction
from django.db.models import Q

from ug.models import (
    UGStudentProfile,
    StudentCourseAssessment,
    UGExamResult,
    ExamRegistration,
)
from ug.services.result_calculator import UGResultCalculator


class CIAResultProcessingService:
    """
    Step 1: CIA Result Processing
    
    Processes CIA results and creates UGExamResult entries
    """
    
    ################################################################################
    # 1. INITIALIZATION & SETUP
    ################################################################################
    
    def __init__(self, batch: str, semester: str, session: str, exam_type: str = 'REGULAR'):
        """
        Initialize service
        
        Args:
            batch: Batch code (e.g., '2024-28') - used as primary filter for REGULAR,
                   but for BACK, all students in session are included
            semester: Semester code (e.g., '1ST', '2ND')
            session: Academic session (e.g., '2024-25')
            exam_type: 'REGULAR' or 'BACK'
        """
        self.batch = batch
        self.semester = semester
        self.session = session
        self.exam_type = exam_type.upper()
        self.stats = {
            'total_students': 0,
            'students_with_cia': 0,
            'cia_pass': 0,
            'cia_fail': 0,
            'exam_results_created': 0,
            'exam_results_updated': 0,
            'exam_registrations_created': 0,
        }
    
    def process(self, dry_run: bool = False) -> Dict:
        """
        Main processing method
        
        Args:
            dry_run: If True, don't save to database (testing mode)
            
        Returns:
            Dictionary with processing statistics
        """
        self._print_header()
        
        # Get students by session
        active_student_ids = StudentCourseAssessment.objects.filter(
            session=self.session,
            semester=self.semester,
            exam_type=self.exam_type,
            label__icontains='CIA'
        ).values_list('student_id', flat=True).distinct()
        
        if self.batch:
            # Filter to specific batch
            students = UGStudentProfile.objects.filter(
                id__in=active_student_ids,
                batch__name=self.batch
            )
        else:
            # All batches in this session
            students = UGStudentProfile.objects.filter(
                id__in=active_student_ids
            )
        self.stats['total_students'] = students.count()
        
        print(f"\n📊 Found {self.stats['total_students']:,} students [{self.exam_type}] in session {self.session} for semester {self.semester}")
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
        for idx, student in enumerate(students.iterator(), 1):
            self._process_student(student, dry_run=dry_run)
            
            # Progress indicator every 1000 students
            if idx % 1000 == 0:
                print(f"  ⏳ Processed {idx:,}/{self.stats['total_students']:,} students...")

    ################################################################################
    # 2. STUDENT CIA RESULT PROCESSING LOGIC
    ################################################################################
    
    def _process_student(self, student: UGStudentProfile, dry_run: bool = False):
        """
        Process CIA results for a single student
        
        Args:
            student: UGStudentProfile instance
            dry_run: If True, don't save to database
        """
        # Get CIA assessments for this student in semester + exam_type + session
        cia_assessments = StudentCourseAssessment.objects.filter(
            student=student,
            semester=self.semester,
            session=self.session,
            exam_type=self.exam_type,
            label__icontains='CIA'
        )
        
        if not cia_assessments.exists() and self.exam_type == 'BACK':
            # USER REQUIREMENT (2026-03-06): CIA Carry-Forward for Regular Back Students
            # If a student did not fail previously in CIA, the old CIA marks should be carried forward.
            # 1. Get all papers the student is appearing for in BACK exam
            back_papers = StudentCourseAssessment.objects.filter(
                student=student,
                semester=self.semester,
                session=self.session,
                exam_type='BACK'
            ).values_list('paper_code', flat=True).distinct()
            
            # Correct Rejoined logic (Assessment-based in Batch context)
            is_rejoined = False
            if student.batch:
                is_rejoined = not StudentCourseAssessment.objects.filter(
                    student=student,
                    semester=self.semester,
                    batch__name=student.batch.name,
                    exam_type='REGULAR'
                ).exists()

            if not is_rejoined:
                for paper_code in back_papers:
                    # Check if student CIA should be carried forward based on the 3 rules
                    can_carry = UGResultCalculator.should_cia_carry_forward(student.id, self.semester, paper_code)
                    
                    if can_carry:
                        # Fetch CIA assessments from previous session
                        old_cia = StudentCourseAssessment.objects.filter(
                            student=student,
                            semester=self.semester,
                            paper_code=paper_code,
                            label__icontains='CIA'
                        ).exclude(session=self.session).order_by('-created_at')
                        
                        if old_cia.exists():
                            # Create new CIA entries for current session by copying old ones
                            new_cia_list = []
                            for old in old_cia:
                                # Avoid duplicates if already created
                                if not StudentCourseAssessment.objects.filter(
                                    student=student, semester=self.semester, session=self.session,
                                    paper_code=paper_code, label=old.label, exam_type='BACK'
                                ).exists():
                                    old.pk = None # Clone
                                    old.session = self.session
                                    old.exam_type = 'BACK'
                                    old.is_cia_filled = True
                                    # Note: created_at/updated_at will be auto-set
                                    new_cia_list.append(old)
                            
                            if new_cia_list and not dry_run:
                                StudentCourseAssessment.objects.bulk_create(new_cia_list)
                                print(f"  📎 Carried forward CIA for {student.registration_no} - {paper_code}")
            
            # Re-fetch CIA assessments after carry-forward
            cia_assessments = StudentCourseAssessment.objects.filter(
                student=student,
                semester=self.semester,
                session=self.session,
                exam_type=self.exam_type,
                label__icontains='CIA'
            )

        if not cia_assessments.exists():
            # No CIA assessments found (and none carried forward) - skip
            return
        
        self.stats['students_with_cia'] += 1
        
        # Fix ind_is_pass from raw marks (migrated data may have wrong values)
        cia_list = list(cia_assessments)
        pass_fixes = []
        for a in cia_list:
            correct_pass = UGResultCalculator.check_individual_pass(a)
            if a.ind_is_pass != correct_pass:
                a.ind_is_pass = correct_pass
                pass_fixes.append(a)
        
        if pass_fixes and not dry_run:
            StudentCourseAssessment.objects.bulk_update(
                pass_fixes, ['ind_is_pass'], batch_size=500
            )
        
        # Check if student passed ALL CIA assessments
        cia_passed = self._check_cia_passed(cia_list)
        
        # Update stats
        if cia_passed:
            self.stats['cia_pass'] += 1
        else:
            self.stats['cia_fail'] += 1
        
        # Create or update UGExamResult and ExamRegistration
        if not dry_run:
            self._create_or_update_exam_result(student, cia_passed)
            
            # If CIA passed, create exam registration
            if cia_passed:
                self._create_exam_registration(student)

    ################################################################################
    # 3. HELPER UPDATERS & CHECKS
    ################################################################################
    
    def _check_cia_passed(self, cia_assessments) -> bool:
        """
        Check if student passed ALL CIA assessments
        
        Passing Criteria:
        - Student must pass EVERY CIA assessment (Theory, Practical, etc.)
        - Uses ind_is_pass field (already calculated in model save)
        
        Args:
            cia_assessments: QuerySet of CIA assessments
            
        Returns:
            True if passed all CIA, False otherwise
        """
        # Check each assessment
        for assessment in cia_assessments:
            # If ind_is_pass is None or False, student failed
            if not assessment.ind_is_pass:
                return False
        
        # Passed all CIA assessments
        return True
    
    def _create_or_update_exam_result(self, student: UGStudentProfile, cia_passed: bool):
        """
        Create or update UGExamResult entry
        
        ONE record per student per semester (session is metadata, not key).
        
        Args:
            student: UGStudentProfile instance
            cia_passed: Whether student passed CIA
        """
        result, created = UGExamResult.objects.get_or_create(
            student=student,
            semester=self.semester,
            defaults={
                'session': self.session,
                'cia_pass': cia_passed,
                'semester_result': 'PENDING',
                'semester_max_credit': 0,
                'semester_credit_earned': 0,
                'sgpa': Decimal('0.00'),
                'is_legacy': False,
            }
        )
        
        if created:
            self.stats['exam_results_created'] += 1
        else:
            # Update existing entry
            result.cia_pass = cia_passed
            result.session = self.session  # Update session to latest
            result.save(update_fields=['cia_pass', 'session', 'updated_at'])
            self.stats['exam_results_updated'] += 1
            
    def _create_exam_registration(self, student: UGStudentProfile):
        """
        Create exam registration (form fillup) for ESE
        Only for students who passed CIA
        """
        # Convert semester string to integer (1ST -> 1, 2ND -> 2, etc.)
        sem_map = {
            '1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4,
            '5TH': 5, '6TH': 6, '7TH': 7, '8TH': 8
        }
        sem_int = sem_map.get(self.semester, 1)  # Default to 1 if not found
        
        # Check if registration already exists
        registration, created = ExamRegistration.objects.get_or_create(
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
        print("📊 STEP 1: CIA RESULT PROCESSING")
        print("="*100)
        print(f"Batch:     {self.batch}")
        print(f"Semester:  {self.semester}")
        print(f"Session:   {self.session}")
        print(f"Exam Type: {self.exam_type}")
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
        print(f"\nUGExamResult Entries Created: {self.stats['exam_results_created']:,}")
        print(f"UGExamResult Entries Updated: {self.stats['exam_results_updated']:,}")
        print(f"ExamRegistrations Created:    {self.stats['exam_registrations_created']:,}")
        print("="*100)
    
    def _percentage(self, count: int) -> str:
        """Calculate percentage of students with CIA data"""
        if self.stats['students_with_cia'] == 0:
            return "0.00"
        return f"{(count / self.stats['students_with_cia']) * 100:.2f}"


def run_cia_processing(batch: str, semester: str, session: str, exam_type: str = 'REGULAR', dry_run: bool = False) -> Dict:
    """
    Convenience function to run Step 1: CIA Result Processing
    
    Args:
        batch: Batch code (e.g., '2024-28')
        semester: Semester code (e.g., '1ST')
        session: Academic session (e.g., '2024-25')
        exam_type: 'REGULAR' or 'BACK'
        dry_run: If True, don't save to databases
        
    Returns:
        Dictionary with processing statistics
    """
    service = CIAResultProcessingService(batch, semester, session, exam_type)
    return service.process(dry_run=dry_run)
