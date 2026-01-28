"""
UG Result Calculator Service

Implements official UG CBCS passing criteria and result calculations
following the rules from ug_passing_rules.txt
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db.models import Q


class UGResultCalculator:
    """
    Official UG CBCS Result Calculator
    
    Based on: UG CBCS Ordinance & Regulations (Pages 18-21)
    """
    
    # Official Grading System (Table 4)
    GRADE_THRESHOLDS = [
        (90, 'O', 10, 'Outstanding'),
        (80, 'A+', 9, 'Excellent'),
        (70, 'A', 8, 'Very Good'),
        (60, 'B+', 7, 'Good'),
        (55, 'B', 6, 'Above Average'),
        (50, 'C', 5, 'Average'),
        (45, 'P', 4, 'Pass'),
        (0, 'F', 0, 'Fail'),
    ]
    
    @staticmethod
    def calculate_grade(marks: Decimal, max_marks: Decimal, is_absent: bool = False) -> Tuple[str, int]:
        """
        Calculate letter grade and numerical grade based on percentage
        
        Args:
            marks: Marks obtained
            max_marks: Maximum marks
            is_absent: Whether student was absent
            
        Returns:
            Tuple of (letter_grade, grade_point)
        """
        if is_absent:
            return ('Ab', 0)
        
        if max_marks == 0:
            return ('F', 0)
        
        # Calculate percentage
        percentage = (Decimal(marks) / Decimal(max_marks)) * 100
        
        # Find matching grade
        for threshold, grade, points, _ in UGResultCalculator.GRADE_THRESHOLDS:
            if percentage >= threshold:
                return (grade, points)
        
        return ('F', 0)
    
    @staticmethod
    def check_individual_pass(assessment) -> bool:
        """
        Check if individual assessment passed
        
        Uses ind_pass_marks field from assessment
        
        Args:
            assessment: StudentCourseAssessment instance
            
        Returns:
            True if passed, False otherwise
        """
        # Absent = Fail
        if assessment.ind_is_absent:
            return False
        
        # No marks obtained = Fail
        if not assessment.ind_marks_obtained:
            return False
        
        # No pass marks defined = assume pass
        if not assessment.ind_pass_marks:
            return True
        
        # Check against pass marks
        return assessment.ind_marks_obtained >= assessment.ind_pass_marks
    
    @staticmethod
    def check_combined_pass(assessments: List) -> bool:
        """
        Check if combined assessments passed
        
        For Theory+Practical courses: CIA-Theory + CIA-Practical
        
        Args:
            assessments: List of StudentCourseAssessment for same type (CIA or ESE)
            
        Returns:
            True if combination passed
        """
        if not assessments:
            return False
        
        # Sum marks obtained
        total_marks = sum(
            a.ind_marks_obtained or 0 
            for a in assessments
        )
        
        # Get combined pass marks (should be same for all)
        comb_pass_marks = assessments[0].comb_pass_marks or 0
        
        return total_marks >= comb_pass_marks
    
    @staticmethod
    def check_exam_eligibility(student_id: int, semester: str, paper_code: str) -> Dict:
        """
        Check if student eligible for ESE exam
        
        Rule: Must pass ALL CIA components
        
        Args:
            student_id: Student ID
            semester: Semester (e.g. '1ST')
            paper_code: Paper code
            
        Returns:
            Dict with eligibility status and details
        """
        from ug.models import StudentCourseAssessment
        
        # Get all CIA assessments for this course
        cia_assessments = StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester,
            paper_code=paper_code,
            label__contains='CIA'
        )
        
        if not cia_assessments.exists():
            return {
                'eligible': False,
                'reason': 'No CIA assessments found'
            }
        
        # Check each CIA component
        failed_components = []
        for cia in cia_assessments:
            if not UGResultCalculator.check_individual_pass(cia):
                failed_components.append(cia.label)
        
        if failed_components:
            return {
                'eligible': False,
                'reason': f'Failed CIA components: {", ".join(failed_components)}'
            }
        
        return {
            'eligible': True,
            'reason': None
        }
    
    @staticmethod
    def calculate_course_result(student_id: int, semester: str, paper_code: str) -> Dict:
        """
        Calculate complete course result
        
        Args:
            student_id: Student ID
            semester: Semester
            paper_code: Paper code
            
        Returns:
            Dict with course result details
        """
        from ug.models import StudentCourseAssessment, CourseStructure
        
        # Get all assessments for this course
        assessments = StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester,
            paper_code=paper_code
        ).order_by('label')
        
        if not assessments.exists():
            return {
                'paper_code': paper_code,
                'passed': False,
                'reason': 'No assessments found'
            }
        
        # Get course structure for credits
        course = CourseStructure.objects.filter(
            paper_code=paper_code
        ).first()
        
        # Separate by component
        theory_assessments = assessments.filter(
            Q(label__contains='Theory') | Q(label='MID_TERM') | Q(label='END_TERM')
        )
        practical_assessments = assessments.filter(
            Q(label__contains='Practical') | Q(label='LAB') | Q(label='END2_TERM')
        )
        
        # Calculate total marks and max marks
        total_marks = sum(a.ind_marks_obtained or 0 for a in assessments)
        total_max_marks = sum(a.ind_max_marks or 0 for a in assessments)
        
        # Calculate grade
        final_grade, grade_point = UGResultCalculator.calculate_grade(
            total_marks, 
            total_max_marks
        )
        
        # Check if passed (all components must pass)
        theory_passed = True
        practical_passed = True
        
        if theory_assessments.exists():
            theory_passed = all(
                UGResultCalculator.check_individual_pass(a) 
                for a in theory_assessments
            )
        
        if practical_assessments.exists():
            practical_passed = all(
                UGResultCalculator.check_individual_pass(a) 
                for a in practical_assessments
            )
        
        course_passed = theory_passed and practical_passed
        
        # Calculate credits earned
        credits_earned = Decimal(0)
        if course and course_passed:
            credits_earned = Decimal(course.max_credit or 0)
        
        return {
            'paper_code': paper_code,
            'passed': course_passed,
            'theory_passed': theory_passed,
            'practical_passed': practical_passed,
            'total_marks': total_marks,
            'total_max_marks': total_max_marks,
            'final_grade': final_grade,
            'grade_point': grade_point,
            'credits_earned': credits_earned,
            'max_credit': Decimal(course.max_credit or 0) if course else Decimal(0)
        }
    
    @staticmethod
    def calculate_sgpa(student_id: int, semester: str) -> Optional[Decimal]:
        """
        Calculate SGPA for a semester
        
        Formula: SGPA = Σ(grade_point × credit) / Σ(credit)
        
        Rule: SGPA = NULL if student doesn't earn ALL prescribed credits
        
        Args:
            student_id: Student ID
            semester: Semester
            
        Returns:
            SGPA value or None
        """
        from ug.models import StudentCourseAssessment
        
        # Get unique paper codes for student in semester
        paper_codes = StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester
        ).values_list('paper_code', flat=True).distinct()
        
        total_grade_points = Decimal(0)
        total_credits_earned = Decimal(0)
        total_prescribed_credits = Decimal(0)
        
        for paper_code in paper_codes:
            result = UGResultCalculator.calculate_course_result(
                student_id, semester, paper_code
            )
            
            total_prescribed_credits += result['max_credit']
            
            if result['passed']:
                total_credits_earned += result['credits_earned']
                total_grade_points += (
                    Decimal(result['grade_point']) * result['credits_earned']
                )
        
        # Rule: SGPA not awarded if not ALL credits earned
        if total_credits_earned < total_prescribed_credits:
            return None
        
        if total_credits_earned == 0:
            return None
        
        sgpa = total_grade_points / total_credits_earned
        return round(sgpa, 2)
    
    @staticmethod
    def determine_semester_result(student_id: int, semester: str) -> str:
        """
        Determine semester result: PASS / PROMOTED / FAIL
        
        Rules:
        - PASS: All CIA + All Theory passed
        - PROMOTED: All CIA passed BUT any Theory failed
        - FAIL: Any CIA failed
        
        Args:
            student_id: Student ID
            semester: Semester
            
        Returns:
            Result status string
        """
        from ug.models import StudentCourseAssessment
        
        # Get all CIA assessments
        cia_assessments = StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester,
            label__contains='CIA'
        )
        
        # Check if all CIA passed
        all_cia_passed = all(
            UGResultCalculator.check_individual_pass(a)
            for a in cia_assessments
        ) if cia_assessments.exists() else False
        
        # Get all theory assessments (ESE-Theory)
        theory_assessments = StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester
        ).filter(
            Q(label__contains='ESE-Theory') | Q(label='END_TERM')
        )
        
        # Check if all theory passed
        all_theory_passed = all(
            UGResultCalculator.check_individual_pass(a)
            for a in theory_assessments
        ) if theory_assessments.exists() else True
        
        # Determine result
        if all_cia_passed and all_theory_passed:
            return 'PASS'
        elif all_cia_passed and not all_theory_passed:
            return 'PROMOTED'
        else:
            return 'FAIL'
