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
    # GRACE MARKS CALCULATION
    ################################################################################
    
    @staticmethod
    def calculate_and_apply_grace(student_id: int, semester: str, assessments: List) -> List:
        """
        Automatically calculate and apply grace marks to failed assessments.
        
        CRITICAL RULE: Grace is ONLY applied if, after applying max 5 marks,
        the student will PASS ALL CIA and ALL ESE/Theory assessments.
        
        Grace Rules (ug_passing_rules.txt):
        - Maximum 5 marks total (can be split across subjects)
        - Only to clear failed subjects
        - Must result in passing ALL CIA and ALL ESE
        - Must NOT improve grade/SGPA (only to achieve passing)
        
        Algorithm:
        1. Separate assessments into CIA and ESE
        2. Find failed assessments within 5 marks of passing
        3. Simulate applying grace (max 5 marks)
        4. Check: Will student pass ALL CIA AND ALL ESE after grace?
        5. If YES → Apply grace permanently
           If NO → Don't apply any grace
        
        Args:
            student_id: Student ID
            semester: Semester
            assessments: List of StudentCourseAssessment instances
            
        Returns:
            Updated list of assessments with grace applied (if validation passed)
        """
        from decimal import Decimal
        
        # Separate CIA and ESE assessments
        cia_assessments = [a for a in assessments if 'CIA' in (a.label or '')]
        ese_assessments = [a for a in assessments if 'ESE' in (a.label or '') or 'END_TERM' in (a.label or '')]
        
        # Find candidates for grace marks (ONLY ESE assessments within 5 marks of passing)
        # RULE: Grace marks apply ONLY to ESE, NOT to CIA
        grace_candidates = []
        for a in ese_assessments:
            # Skip if absent, already passed, or no pass marks defined
            if a.ind_is_absent or a.ind_is_pass or not a.ind_pass_marks:
                continue
            
            ind_marks = a.ind_marks_obtained or Decimal(0)
            pass_marks = a.ind_pass_marks or Decimal(0)
            
            # Calculate shortfall
            shortfall = pass_marks - ind_marks
            
            # Only consider if within grace range (0 < shortfall <= 5)
            if shortfall > 0 and shortfall <= 5:
                grace_candidates.append({
                    'assessment': a,
                    'shortfall': shortfall,
                    'ind_marks': ind_marks,
                    'pass_marks': pass_marks
                })
        
        if not grace_candidates:
            return assessments  # No one needs grace
        
        # Sort by smallest shortfall first (optimize grace usage)
        grace_candidates.sort(key=lambda x: x['shortfall'])
        
        # SIMULATION: Allocate grace marks (max 5 total) to see if it helps
        simulated_grace = {}  # {assessment_id: grace_amount}
        total_grace_allocated = Decimal(0)
        MAX_GRACE = Decimal(5)
        
        for candidate in grace_candidates:
            assessment = candidate['assessment']
            shortfall = candidate['shortfall']
            
            # Check if we have enough grace remaining
            grace_available = MAX_GRACE - total_grace_allocated
            if grace_available <= 0:
                break  # No grace left
            
            # Allocate grace (minimum of shortfall or available grace)
            grace_to_give = min(shortfall, grace_available)
            simulated_grace[assessment.id] = grace_to_give
            total_grace_allocated += grace_to_give
        
        # VALIDATION: Check if all CIA and all ESE will pass after grace
        def will_pass_with_grace(assessment_list, grace_dict):
            """Check if all assessments in list will pass with simulated grace"""
            for a in assessment_list:
                if a.ind_is_absent:
                    return False  # Absent = always fail
                
                # Calculate final marks with simulated grace
                final_marks = (a.ind_marks_obtained or Decimal(0)) + grace_dict.get(a.id, Decimal(0))
                pass_marks = a.ind_pass_marks or Decimal(0)
                
                if pass_marks > 0 and final_marks < pass_marks:
                    return False  # Still fails even with grace
            
            return True  # All passed
        
        all_cia_pass = will_pass_with_grace(cia_assessments, simulated_grace)
        all_ese_pass = will_pass_with_grace(ese_assessments, simulated_grace)
        
        # CRITICAL DECISION: Only apply grace if student will pass EVERYTHING
        if not (all_cia_pass and all_ese_pass):
            print(f"  ⚠️ Grace NOT applied: Student won't pass all CIA and ESE even with {total_grace_allocated} grace marks")
            print(f"     CIA pass: {all_cia_pass}, ESE pass: {all_ese_pass}")
            return assessments  # Don't apply any grace
        
        # APPLY GRACE: Student will pass everything with grace
        for candidate in grace_candidates:
            assessment = candidate['assessment']
            grace_to_give = simulated_grace.get(assessment.id)
            
            if not grace_to_give:
                continue
            
            # Apply grace marks permanently
            assessment.ind_grace_obtained = grace_to_give
            assessment.ind_final_marks_obtained = candidate['ind_marks'] + grace_to_give
            assessment.ind_is_pass = (assessment.ind_final_marks_obtained >= candidate['pass_marks'])
            
            # Save to database
            assessment.save(update_fields=[
                'ind_grace_obtained',
                'ind_final_marks_obtained',
                'ind_is_pass'
            ])
            
            # Log for debugging
            print(f"  ✅ Grace applied: {assessment.student.registration_no} - "
                  f"{assessment.paper_code} {assessment.label}: "
                  f"{candidate['ind_marks']} + {grace_to_give} = {assessment.ind_final_marks_obtained} "
                  f"(pass: {candidate['pass_marks']})")
        
        print(f"  📊 Total grace allocated: {total_grace_allocated}/5 marks")
        print(f"  ✅ Validation passed: Student will pass ALL CIA and ALL ESE")
        
        return assessments

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
        
        # Use final marks (includes grace) for pass check
        final_marks = assessment.ind_final_marks_obtained or assessment.ind_marks_obtained or 0
        
        # No marks obtained = Fail
        if not final_marks:
            return False
        
        # No pass marks defined = assume pass
        if not assessment.ind_pass_marks:
            return True
        
        # FIXED: Check using final_marks (marks + grace) instead of just marks_obtained
        return final_marks >= assessment.ind_pass_marks
    
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
        # FIXED: Use ind_final_marks_obtained (includes grace) instead of ind_marks_obtained
        total_marks = sum(a.ind_final_marks_obtained or 0 for a in assessment_list)
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
        
        # FIXED: Award credits based on component-level pass/fail  
        # For papers with both Theory and Practical, award partial credits
        if has_both:
            # Split credits for Theory+Practical papers
            theory_credit = Decimal(0)
            practical_credit = Decimal(0)
            
            if course_max_credit == 6:
                theory_credit = Decimal(4)
                practical_credit = Decimal(2)
            elif course_max_credit == 5:
                theory_credit = Decimal(3)
                practical_credit = Decimal(2)
            elif course_max_credit == 3:
                theory_credit = Decimal(2)
                practical_credit = Decimal(1)
            else:
                # Default split: roughly 2/3 for theory, 1/3 for practical
                theory_credit = Decimal(course_max_credit) * Decimal('0.67')
                practical_credit = Decimal(course_max_credit) * Decimal('0.33')
            
            # Award credits based on individual component pass status
            credits_earned = Decimal(0)
            if theory_passed:
                credits_earned += theory_credit
            if practical_passed:
                credits_earned += practical_credit
        else:
            # Single component paper: all or nothing
            credits_earned = max_credit if course_passed else Decimal(0)
        
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
        # SGPA uses COMPONENT-level fields (comb_*) separated by Theory vs Practical
        # - component_grade_point = component_numeric_grade × component_max_credits
        # - component_max_credits = max credits for that specific component (Theory/Practical)
        # This properly computes separate contributions like: (Theory Grade * Theory Credits) + (Practical Grade * Practical Credits)
        processed_components = set()
        
        if assessments:
            for a in assessments:
                if not a.paper_code:
                    continue
                    
                label_lower = str(a.label).lower()
                if 'theory' in label_lower or a.label in ['MID_TERM', 'END_TERM']:
                    comp_type = 'Theory'
                else:
                    comp_type = 'Practical'
                
                comp_key = (a.paper_code, comp_type)
                
                if comp_key in processed_components:
                    continue
                
                # Use COMPONENT-level combined fields
                weighted_point = Decimal(a.comb_grade_point or 0)   # grade × component_credits
                max_credit = Decimal(a.comb_max_credits or 0)       # total component credits
                earned_credit = Decimal(a.comb_credit_obtained or 0)
                
                total_points += weighted_point
                
                if max_credit > 0:
                    total_registered_credits += max_credit
                    total_earned_credits += earned_credit
                
                processed_components.add(comp_key)
                
        else:
             pass 

        # SGPA Formula (Official Rule):
        # SGPA = Σ(mᵢ × oᵢ) / Σ(oᵢ)
        # where mᵢ = numeric grade, oᵢ = credits for EACH course (ALL courses, not just passed)
        # Failed courses: mᵢ=0, but oᵢ still counts in denominator
        if total_registered_credits == 0:
            return None
            
        sgpa = total_points / total_registered_credits
        
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
        
        # FIXED: Get ALL ESE assessments (Theory AND Practical)
        # Previously only checked 'ESE-Theory', missing ESE-Practical absences
        ese_assessments = [
            a for a in assessment_list 
            if 'ESE' in (a.label or '')  # Matches ESE-Theory, ESE-Practical, END_TERM
        ]
        
        # Check if all ESE passed
        all_ese_passed = True
        if ese_assessments:
            all_ese_passed = all(UGResultCalculator.check_individual_pass(a) for a in ese_assessments)
        
        # Determine result
        # PASS: All CIA passed AND all ESE passed (no failures/absences)
        # PROMOTED: All CIA passed BUT some ESE failed/absent  
        # FAIL: CIA failed
        if all_cia_passed and all_ese_passed:
            return 'PASS'
        elif all_cia_passed and not all_ese_passed:
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
            total_credits = sum(r.semester_credit_earned or 0 for r in results)
            
            if total_credits < 28:
                return False, f"Insufficient Credits: {total_credits}/28 (Sem 1+2)"
            return True, "Eligible"

        # 3. Special Rules for moving to Sem 5 (Year 3)
        if target_sem == '5TH':
            # Rule: Total credits of 40 in Sem 1 & 2
            results_1_2 = UGExamResult.objects.filter(
                student_id=student_id, 
                semester__in=['1ST', '2ND']
            )
            credits_1_2 = sum(r.semester_credit_earned or 0 for r in results_1_2)
            
            if credits_1_2 < 40:
                return False, f"Sem 1 & 2 Not Cleared: {credits_1_2}/40 Credits"
            
            # Rule: At least 68 credits in Sem 1, 2, 3, 4
            results_1_4 = UGExamResult.objects.filter(
                student_id=student_id, 
                semester__in=['1ST', '2ND', '3RD', '4TH']
            )
            total_credits = sum(r.semester_credit_earned or 0 for r in results_1_4)
            
            if total_credits < 68:
                return False, f"Insufficient Credits: {total_credits}/68 (Sem 1-4)"
            return True, "Eligible"
            
        # 4. Special Rules for moving to Sem 7 (Year 4)
        if target_sem == '7TH':
            # Rule: Sem 1+2 >= 40
            results_1_2 = UGExamResult.objects.filter(student_id=student_id, semester__in=['1ST', '2ND'])
            credits_1_2 = sum(r.semester_credit_earned or 0 for r in results_1_2)
            if credits_1_2 < 40:
                return False, f"Sem 1 & 2 Not Cleared: {credits_1_2}/40 Credits"

            # Rule: Sem 3+4 >= 40
            results_3_4 = UGExamResult.objects.filter(student_id=student_id, semester__in=['3RD', '4TH'])
            credits_3_4 = sum(r.semester_credit_earned or 0 for r in results_3_4)
            if credits_3_4 < 40:
                return False, f"Sem 3 & 4 Not Cleared: {credits_3_4}/40 Credits"

            # Rule: Sem 1-4 >= 80
            results_1_4 = UGExamResult.objects.filter(student_id=student_id, semester__in=['1ST', '2ND', '3RD', '4TH'])
            credits_1_4 = sum(r.semester_credit_earned or 0 for r in results_1_4)
            if credits_1_4 < 80:
                return False, f"Sem 1-4 Insufficient: {credits_1_4}/80 Credits"

            # Rule: Sem 1-6 >= 108
            results_1_6 = UGExamResult.objects.filter(
                student_id=student_id, 
                semester__in=['1ST', '2ND', '3RD', '4TH', '5TH', '6TH']
            )
            credits_1_6 = sum(r.semester_credit_earned or 0 for r in results_1_6)
            if credits_1_6 < 108:
                return False, f"Sem 1-6 Insufficient: {credits_1_6}/108 Credits"
            
            return True, "Eligible"

        # 5. Standard Promotion (1->2, 3->4, 5->6)
        # Using status_to_check (Incl. BACK statuses - QUALIFIED is like PASS, PARTLY_QUALIFIED like PROMOTED)
        if status_to_check in ['PASS', 'PROMOTED', 'QUALIFIED', 'PARTLY_QUALIFIED']:
            return True, "Eligible"
            
        return False, "Not Eligible"

    ################################################################################
    # #### BACK EXAM RESULT ####
    ################################################################################

    @staticmethod
    def determine_back_result(
        student_id: int,
        semester: str,
        back_assessments: Optional[List] = None
    ) -> str:
        """
        Determine back exam result: QUALIFIED / PARTLY_QUALIFIED / DISQUALIFIED
        
        Rules for Regular Back Students:
        - QUALIFIED: Passed ALL back subjects
        - PARTLY_QUALIFIED: Passed some subjects but fails in others
        - DISQUALIFIED: Failed in all back subjects
        
        Args:
            student_id: Student ID
            semester: Semester
            back_assessments: Pre-fetched list of BACK exam assessments
            
        Returns:
            Status string from SEMESTER_RESULT_CHOICES
        """
        from ug.models import StudentCourseAssessment

        if back_assessments is None:
            back_assessments = list(StudentCourseAssessment.objects.filter(
                student_id=student_id,
                semester=semester,
                exam_type='BACK'
            ))

        if not back_assessments:
            return 'DISQUALIFIED'

        # Group by paper_code to count "subjects"
        paper_codes = set(a.paper_code for a in back_assessments if a.paper_code)
        
        passed_papers_count = 0
        for paper_code in paper_codes:
            # Check if all components for this paper passed
            paper_assessments = [a for a in back_assessments if a.paper_code == paper_code]
            if all(UGResultCalculator.check_individual_pass(a) for a in paper_assessments):
                passed_papers_count += 1

        if passed_papers_count == len(paper_codes):
            return 'QUALIFIED'
        elif passed_papers_count > 0:
            return 'PARTLY_QUALIFIED'
        else:
            return 'DISQUALIFIED'

    @staticmethod
    def recalculate_overall_semester_result(
        student_id: int,
        semester: str,
    ) -> dict:
        """
        Recalculate the OVERALL semester result by combining REGULAR + BACK assessments.
        
        For each paper+label combo, takes the BEST result across exam types:
          - If REGULAR passed → use REGULAR
          - If REGULAR failed but BACK passed → use BACK
          - If both failed → still failed
        
        Special Rules for Back Students:
        - If student has appeared for the same paper previously (Regular Back):
          The result status for the back exam session itself is Qualified/Partly/Disqualified.
          However, this method calculates the CUMULATIVE status for the semester.
        
        Returns:
            dict with:
              - 'result': new semester result string
              - 'all_cia_passed': bool
              - 'all_ese_passed': bool
              - 'best_assessments': list of best assessment per paper+label
        """
        from ug.models import StudentCourseAssessment, UGStudentProfile

        # Determine result status logic:
        # Check student current batch to see if they gave REGULAR exams for this semester in this batch.
        # If no regular entries found in current batch, they are batch-restarted/rejoined.
        from ug.models import StudentCourseAssessment
        student = UGStudentProfile.objects.filter(id=student_id).first()
        is_rejoined = False
        if student and student.batch:
            is_rejoined = not StudentCourseAssessment.objects.filter(
                student=student,
                semester=semester,
                batch__name=student.batch.name,
                exam_type='REGULAR'
            ).exists()

        # Get ALL assessments (REGULAR + BACK) for this student+semester
        all_assessments = list(StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester,
        ))

        if not all_assessments:
            return {'result': 'FAIL', 'all_cia_passed': False, 'all_ese_passed': False, 'best_assessments': []}

        # Group by (paper_code, label) → pick the best result
        from collections import defaultdict
        groups = defaultdict(list)
        for a in all_assessments:
            key = (a.paper_code, a.label)
            groups[key].append(a)

        best_assessments = []
        for key, group in groups.items():
            # Sort: passed first, then by marks descending
            group.sort(
                key=lambda a: (
                    1 if UGResultCalculator.check_individual_pass(a) else 0,
                    a.ind_final_marks_obtained or a.ind_marks_obtained or 0
                ),
                reverse=True
            )
            best_assessments.append(group[0])  # Pick the best

        # Determine result from best assessments
        cia_best = [a for a in best_assessments if 'CIA' in (a.label or '')]
        ese_best = [a for a in best_assessments if 'ESE' in (a.label or '')]

        all_cia_passed = all(UGResultCalculator.check_individual_pass(a) for a in cia_best) if cia_best else False
        all_ese_passed = all(UGResultCalculator.check_individual_pass(a) for a in ese_best) if ese_best else True

        # Cumulative result logic (Terminology depends on student type and attempt history)
        has_back_attempts = any(a.exam_type == 'BACK' for a in all_assessments)
        
        if all_cia_passed and all_ese_passed:
            # Rejoined students always get PASS/PROMOTED/FAIL
            if is_rejoined:
                result = 'PASS'
            else:
                result = 'QUALIFIED' if has_back_attempts else 'PASS'
        elif all_cia_passed and not all_ese_passed:
            if is_rejoined:
                result = 'PROMOTED'
            else:
                result = 'PARTLY_QUALIFIED' if has_back_attempts else 'PROMOTED'
        else:
            if is_rejoined:
                result = 'FAIL'
            else:
                result = 'DISQUALIFIED' if has_back_attempts else 'FAIL'
        
        # Calculate overall SGPA from best assessments
        overall_sgpa = UGResultCalculator.calculate_sgpa(
            student_id, semester, assessments=best_assessments
        )

        semester_max_credit = sum(a.comb_max_credits or 0 for a in best_assessments if (a.label or '').startswith('ESE'))
        semester_credit_earned = sum(a.comb_credit_obtained or 0 for a in best_assessments if (a.label or '').startswith('ESE'))

        # USER REQUIREMENT (2026-03-07): We no longer update UGExamResult here.
        # This prevents overwritting historical 'REGULAR' results or session statuses.
        # The caller (step2_final_processing) is responsible for updating the specific session record.

        return {
            'result': result,
            'sgpa': overall_sgpa,
            'semester_max_credit': semester_max_credit,
            'semester_credit_earned': semester_credit_earned,
            'all_cia_passed': all_cia_passed,
            'all_ese_passed': all_ese_passed,
            'best_assessments': best_assessments,
        }

    @staticmethod
    def should_cia_carry_forward(student_id: int, semester: str, paper_code: str) -> bool:
        """
        Check if student CIA marks should be carried forward based on user rules:
        1. If student failed in previous session (of CIA), MUST retake.
        2. If student did not fail previously, carry forward.
        3. If student was 'PROMOTED' in last exam for this semester, carry forward.
        """
        from ug.models import StudentCourseAssessment, UGExamResult
        
        # Rule 3: Check if student was 'PROMOTED' in any previous session for this semester
        promoted_previously = UGExamResult.objects.filter(
            student_id=student_id,
            semester=semester,
            semester_result='PROMOTED'
        ).exists()
        if promoted_previously:
            return True

        # Rule 1 & 2: Check if CIA component failed in previous attempt
        # Find latest REGULAR or previous BACK entry for this CIA
        previous_cia_fails = StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester,
            paper_code=paper_code,
            label__icontains='CIA'
        ).filter(
            Q(ind_is_pass=False) | Q(ind_is_absent=True)
        )
        
        # If any previous CIA attempt failed, we must retake
        if previous_cia_fails.exists():
            return False
            
        # Otherwise, if they appeared before and didn't fail, carry forward
        has_appeared_before = StudentCourseAssessment.objects.filter(
            student_id=student_id,
            semester=semester,
            paper_code=paper_code,
            label__icontains='CIA'
        ).exists()
        
        return has_appeared_before

