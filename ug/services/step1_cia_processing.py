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


class CIAResultProcessingService:
    """
    Step 1: CIA Result Processing
    
    Processes CIA results and creates UGExamResult entries
    """
    
    ################################################################################
    # 1. INITIALIZATION & SETUP
    ################################################################################
    
    def __init__(self, batch: str, semester: str, session: str):
        """
        Initialize service
        
        Args:
            batch: Batch code (e.g., '2024-28')
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
    
    def process(self, dry_run: bool = False) -> Dict:
        """
        Main processing method
        
        Args:
            dry_run: If True, don't save to database (testing mode)
            
        Returns:
            Dictionary with processing statistics
        """
        self._print_header()
        
        # Get all students in batch who have assessments in this semester
        students = UGStudentProfile.objects.filter(
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
        # Get all CIA assessments for this student in semester
        cia_assessments = StudentCourseAssessment.objects.filter(
            student=student,
            semester=self.semester,
            label__icontains='CIA'
        )
        
        if not cia_assessments.exists():
            # No CIA assessments found - skip
            return
        
        self.stats['students_with_cia'] += 1
        
        # Check if student passed ALL CIA assessments
        cia_passed = self._check_cia_passed(cia_assessments)
        
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
        
        Args:
            student: UGStudentProfile instance
            cia_passed: Whether student passed CIA
        """
        result, created = UGExamResult.objects.get_or_create(
            student=student,
            semester=self.semester,
            session=self.session,
            defaults={
                'cia_pass': cia_passed,
                # 'ese_pass': False,  # ESE not yet processed
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
            result.save(update_fields=['cia_pass', 'updated_at'])
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
        print(f"\nUGExamResult Entries Created: {self.stats['exam_results_created']:,}")
        print(f"UGExamResult Entries Updated: {self.stats['exam_results_updated']:,}")
        print(f"ExamRegistrations Created:    {self.stats['exam_registrations_created']:,}")
        print("="*100)
    
    def _percentage(self, count: int) -> str:
        """Calculate percentage of students with CIA data"""
        if self.stats['students_with_cia'] == 0:
            return "0.00"
        return f"{(count / self.stats['students_with_cia']) * 100:.2f}"


def run_cia_processing(batch: str, semester: str, session: str, dry_run: bool = False) -> Dict:
    """
    Convenience function to run Step 1: CIA Result Processing
    
    Args:
        batch: Batch code (e.g., '2024-28')
        semester: Semester code (e.g., '1ST')
        session: Academic session (e.g., '2024-25')
        dry_run: If True, don't save to databases
        
    Returns:
        Dictionary with processing statistics
    """
    service = CIAResultProcessingService(batch, semester, session)
    return service.process(dry_run=dry_run)
