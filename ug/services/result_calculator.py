"""
UG Result Calculator Service

Implements official UG CBCS passing criteria and result calculations
following the rules from ug_passing_rules.txt
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from django.db.models import Q


class UGResultCalculator:
    """
    Official UG CBCS Result Calculator
    
    Based on: UG CBCS Ordinance & Regulations (Pages 18-21)
    """

    ################################################################################
    # 0. GRADING SYSTEM AND CONSTANTS
    ################################################################################
    
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

    ################################################################################
    # #### Individual Level ####
    ################################################################################
    
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
    
    ################################################################################
    # #### Combined Level #### (Component Aggregation)
    ################################################################################
    
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
        Check if student eligible for ESE exam (Passed All CIA)
        
        Args:
            student_id: Student ID
            semester: Semester
            paper_code: Paper code
            
        Returns:
            Dict with eligibility status
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

    ################################################################################
    # #### Course Level ####
    ################################################################################
    
    @staticmethod
    def calculate_course_result(
        student_id: int, 
        semester: str, 
        paper_code: str,
        assessments: Optional[List] = None,
        course_structure: Optional[Any] = None
    ) -> Dict:
        """
        Calculate complete course result (Final Grade, Credits, Pass Status)
        
        Args:
            student_id: Student ID
            semester: Semester
            paper_code: Paper code
            assessments: Optional list of pre-fetched assessments (Optimization)
            course_structure: Optional pre-fetched CourseStructure object (Optimization)
            
        Returns:
            Dict with course result details
        """
        from ug.models import StudentCourseAssessment, CourseStructure
        from django.db.models import Q
        import re
        
        # 1. Get Assessments (DB or Pre-fetched)
        if assessments is None:
            assessments_qs = StudentCourseAssessment.objects.filter(
                student_id=student_id,
                semester=semester,
                paper_code=paper_code
            ).order_by('label')
            assessment_list = list(assessments_qs)
        else:
            # Use pre-fetched list
            assessment_list = [a for a in assessments if a.paper_code == paper_code]
            # Simple sorting by label if needed, or assume pre-sorted
            assessment_list.sort(key=lambda x: x.label)
        
        if not assessment_list:
            return {
                'paper_code': paper_code,
                'passed': False,
                'reason': 'No assessments found'
            }
        
        # 2. Get Course Structure (DB or Pre-fetched)
        course = course_structure
        
        if not course:
            # Check DB if not provided
            course = CourseStructure.objects.filter(paper_code=paper_code).first()
            if not course:
                # Flexible lookup
                numeric_part = re.search(r'\d+$', paper_code)
                if numeric_part:
                    stripped_code = numeric_part.group()
                    course = CourseStructure.objects.filter(paper_code=stripped_code).first()
        
        # 3. Processing Components
        theory_assessments = []
        practical_assessments = []
        
        for a in assessment_list:
            label_lower = a.label.lower() if a.label else ''
            if 'theory' in label_lower or a.label in ['MID_TERM', 'END_TERM']:
                theory_assessments.append(a)
            elif 'practical' in label_lower or a.label in ['LAB', 'END2_TERM']:
                practical_assessments.append(a)
        
        # Calculate total marks and max marks
        total_marks = sum(a.ind_marks_obtained or 0 for a in assessment_list)
        total_max_marks = sum(a.ind_max_marks or 0 for a in assessment_list)
        
        # Calculate grade
        final_grade, grade_point = UGResultCalculator.calculate_grade(
            total_marks, 
            total_max_marks
        )
        
        # Check if passed (all components must pass)
        theory_passed = True
        practical_passed = True
        
        if theory_assessments:
            theory_passed = all(UGResultCalculator.check_individual_pass(a) for a in theory_assessments)
        
        if practical_assessments:
            practical_passed = all(UGResultCalculator.check_individual_pass(a) for a in practical_assessments)
        
        course_passed = theory_passed and practical_passed
        
        # Calculate credits earned
        credits_earned = Decimal(0)
        max_credit = Decimal(0)
        
        # USER REQUIREMENT (2026-01-30):
        # Get course_max_credit from CourseStructure (matching last 4 chars)
        # Fallback to json_data for legacy data
        # If course has BOTH Theory AND Practical, split credits:
        #   6 credits → 4 (Theory) + 2 (Practical)
        #   5 credits → 3 (Theory) + 2 (Practical)
        #   3 credits → 2 (Theory) + 1 (Practical)
        
        course_max_credit = Decimal(0)
        
        # 1. Try to get from course structure
        if course and course.max_credit:
            course_max_credit = Decimal(course.max_credit)
        else:
            # 2. Fallback to assessment fields
            for a in assessment_list:
                if a.course_max_credits:
                    course_max_credit = Decimal(a.course_max_credits)
                    break
                elif a.comb_max_credits:
                    course_max_credit = Decimal(a.comb_max_credits)
                    break
        
        # 3. Fallback to json_data for legacy data
        if course_max_credit == 0:
            for a in assessment_list:
                if a.json_data:
                    # Legacy data stores individual component credits in subject_ce
                    # We need the COURSE-level credit (total for all components)
                    # Look for max_credit or similar field in json_data
                    if 'max_credit' in a.json_data:
                        try:
                            course_max_credit = Decimal(str(a.json_data['max_credit']))
                            break
                        except (ValueError, TypeError):
                            pass
                    elif 'subject_ce' in a.json_data:
                        # subject_ce is component-level, we need to sum them
                        # But for now, we can use it if nothing else is available
                        try:
                            val = a.json_data['subject_ce']
                            if val and str(val).strip():
                                course_max_credit = Decimal(str(val))
                                break
                        except (ValueError, TypeError):
                            pass
        
        # Check if course has BOTH Theory AND Practical
        has_theory = len(theory_assessments) > 0
        has_practical = len(practical_assessments) > 0
        has_both = has_theory and has_practical
        
        # For a course with both components, we return TWO separate results
        # But this function returns ONE result per course
        # So we use course_max_credit as the total, and it gets split during combined processing
        
        max_credit = course_max_credit
        
        # Award credits if course passed
        if course_passed:
            credits_earned = max_credit
        
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
            'max_credit': max_credit,
            'has_theory': has_theory,
            'has_practical': has_practical
        }

    ################################################################################
    # #### Semester Level ####
    ################################################################################
    
    @staticmethod
    def calculate_sgpa(
        student_id: int, 
        semester: str,
        assessments: Optional[List] = None,
        course_map: Optional[Dict] = None
    ) -> Optional[Decimal]:
        """
        Calculate SGPA for a semester
        
        Formula: SGPA = Σ(grade_point × credit) / Σ(credit)
        
        Args:
            student_id: Student ID
            semester: Semester
            assessments: Optional list of all assessments for student (Optimization)
            course_map: Optional dict of {paper_code: CourseStructure} (Optimization)
            
        Returns:
            SGPA value or None
        """
        from ug.models import StudentCourseAssessment
        
        if assessments is None:
            paper_codes_qs = StudentCourseAssessment.objects.filter(
                student_id=student_id,
                semester=semester
            ).values_list('paper_code', flat=True)
            paper_codes = set(paper_codes_qs)
            # Need to fetch if not provided... but calling calculate_course_result will fetch per course
            # This path is unoptimized if assessments=None
        else:
            paper_codes = set(a.paper_code for a in assessments if a.paper_code)
        total_points = Decimal(0)
        total_registered_credits = Decimal(0)
        total_earned_credits = Decimal(0)
        
        # For legacy: Each assessment row (CIA-Theory, ESE-Theory, etc.) has individual subject_gp
        # We need to sum ALL rows, not deduplicate by paper!
        processed_papers_for_credits = set()  # Only for credit counting
        
        # Iterate provided assessments (OPTIMIZED PATH)
        if assessments:
            for a in assessments:
                # USER CLARIFICATION (2026-01-30):
                # Legacy has individual subject_gp per assessment row
                # SGPA = Sum(ALL subject_gp rows) / earned_credits
                # Do NOT deduplicate by paper for grade points!
                
                # Fetch fields updated by Step 2 or Migration
                # NOTE: Step 2 now stores WEIGHTED POINT (Grade*Credit) in comb_grade_point
                weighted_point_field = Decimal(a.comb_grade_point or 0) 
                
                # Add weighted point from THIS row (not deduplicated)
                total_points += weighted_point_field
                
                # For credits: deduplicate by paper (only count once per course)
                if a.paper_code and a.paper_code not in processed_papers_for_credits:
                    max_credit = Decimal(a.comb_max_credits or 0)
                    earned_credit = Decimal(a.comb_credit_obtained or 0)
                    
                    # Skip if no credits defined (e.g. non-credit course)
                    if max_credit > 0:
                        total_registered_credits += max_credit
                        total_earned_credits += earned_credit
                    
                    processed_papers_for_credits.add(a.paper_code)
                
        else:
             pass 

        # SGPA Calculation
        # USER CLARIFICATION (2026-01-30): Use EARNED CREDITS as denominator (legacy logic)
        # This means students who fail courses get higher SGPA (failed courses don't count in denominator)
        if total_earned_credits == 0:
            return None
            
        sgpa = total_points / total_earned_credits
        
        return round(sgpa, 2)
    
    @staticmethod
    def determine_semester_result(
        student_id: int, 
        semester: str,
        assessments: Optional[List] = None
    ) -> str:
        """
        Determine semester result: PASS / PROMOTED / FAIL
        
        Args:
            student_id: Student ID
            semester: Semester
            assessments: Optional pre-fetched list (Optimization)
            
        Returns:
            Result status string
        """
        from ug.models import StudentCourseAssessment
        
        if assessments is None:
             # DB Fallback
            assessments = StudentCourseAssessment.objects.filter(
                student_id=student_id,
                semester=semester
            )
            assessment_list = list(assessments)
        else:
            assessment_list = assessments

        # Filter from list
        cia_assessments = [a for a in assessment_list if 'CIA' in (a.label or '')]
        
        # Check if all CIA passed
        all_cia_passed = False
        if cia_assessments:
            all_cia_passed = all(UGResultCalculator.check_individual_pass(a) for a in cia_assessments)
        
        # Get theory assessments
        theory_assessments = [
            a for a in assessment_list 
            if 'ESE-Theory' in (a.label or '') or a.label == 'END_TERM'
        ]
        
        # Check if all theory passed
        all_theory_passed = True
        if theory_assessments:
            all_theory_passed = all(UGResultCalculator.check_individual_pass(a) for a in theory_assessments)
        
        # Determine result
        if all_cia_passed and all_theory_passed:
            return 'PASS'
        elif all_cia_passed and not all_theory_passed:
            return 'PROMOTED'
        else:
            return 'FAIL'

    @staticmethod
    def check_promotion_eligibility(
        student_id: int, 
        current_semester: str, 
        current_result_status: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check eligibility for promotion to next semester based on rules
        
        Rules:
        - Sem 1 -> 2: Pass/Promoted in Sem 1
        - Sem 2 -> 3: All CIA passed AND >= 28 Credits (Sem 1+2)
        - Sem 3 -> 4: Pass/Promoted in Sem 3
        - Sem 4 -> 5: All CIA passed AND Sem 1+2 fully passed (40 credits) AND >= 68 Credits (Sem 1-4)
        - Sem 5 -> 6: Pass/Promoted in Sem 5
        """
        from ug.models import UGExamResult
        
        # Standard Next Semester Mapping
        next_sem_map = {
            '1ST': '2ND', '2ND': '3RD', '3RD': '4TH', 
            '4TH': '5TH', '5TH': '6TH', '6TH': '7TH',
            '7TH': '8TH', '8TH': None
        }
        
        target_sem = next_sem_map.get(current_semester)
        if not target_sem:
            return False, "No next semester"

        # Determine Result Status (Use arg if provided, else DB)
        status_to_check = current_result_status
        
        if not status_to_check:
            # Fallback to DB
            current_result_obj = UGExamResult.objects.filter(
                student_id=student_id, semester=current_semester
            ).order_by('-created_at').first()
            
            if not current_result_obj:
                return False, f"Result for {current_semester} not found"
            
            status_to_check = current_result_obj.semester_result
            
        if status_to_check == 'FAIL':
            return False, f"Failed in {current_semester}"

        # 2. Special Rules for moving to Sem 3 (Year 2)
        if target_sem == '3RD':
            # Rule: At least 28 Credits in Sem 1 + 2
            results = UGExamResult.objects.filter(
                student_id=student_id, 
                semester__in=['1ST', '2ND']
            )
            # CAUTION: If current_semester is 2ND, the DB might be stale for 2ND credits.
            # But usually we handle credits calculation before this.
            # If we need to account for current semester credits that aren't in DB yet,
            # we'd need another argument. For now, assuming standard flow where this comes later or is 1st sem.
            # Step 2 updates ExamResult at the END.
            # So if we are in Sem 2, we might have issue.
            # But the User Request primarily concerns Sem 1 (1->2).
            # For 1->2, we just need status.
            total_credits = sum(r.semester_credit_earned or 0 for r in results)
            
            if total_credits < 28:
                return False, f"Insufficient Credits: {total_credits}/28 (Sem 1+2)"
            return True, "Eligible"

        # 3. Special Rules for moving to Sem 5 (Year 3)
        if target_sem == '5TH':
            # Rule: Total credits of 40 in Sem 1 & 2
            # Rule: At least 68 credits in Sem 1, 2, 3, 4
            results_1_2 = UGExamResult.objects.filter(
                student_id=student_id, 
                semester__in=['1ST', '2ND']
            )
            credits_1_2 = sum(r.semester_credit_earned or 0 for r in results_1_2)
            
            if credits_1_2 < 40:
                return False, f"Sem 1 & 2 Not Cleared: {credits_1_2}/40 Credits"
            
            results_1_4 = UGExamResult.objects.filter(
                student_id=student_id, 
                semester__in=['1ST', '2ND', '3RD', '4TH']
            )
            total_credits = sum(r.semester_credit_earned or 0 for r in results_1_4)
            
            if total_credits < 68:
                return False, f"Insufficient Credits: {total_credits}/68 (Sem 1-4)"
            return True, "Eligible"

        # 4. Standard Promotion (1->2, 3->4, 5->6)
        # Using status_to_check
        if status_to_check in ['PASS', 'PROMOTED']:
            return True, "Eligible"
            
        return False, "Not Eligible"
