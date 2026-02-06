"""
PG Result Processing Service

Complete result calculation and processing system for PG students.
Handles individual, combined, course, and semester level calculations.

Result Determination Logic:
    PASS: All CIA passed AND All ESE passed
        - Student successfully completed the semester
        - Can move to next semester with all courses cleared
    
    PROMOTED: All CIA passed BUT Some/All ESE failed
        - Student is promoted to next semester
        - Must clear failed ESE papers later (backlog)
        - CIA passing is mandatory for promotion
    
    FAIL: Some/All CIA failed
        - Student cannot be promoted
        - Must repeat the semester
        - ESE status doesn't matter if CIA failed

Usage:
    from pg.services.result_service import PGResultService
    
    # Process all students in a semester
    PGResultService.process_semester(
        semester="1",
        session="2024",
        dry_run=True
    )
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.db.models import Q


class PGResultService:
    """
    Complete PG Result Processing Service
    
    Handles:
    - Grade calculations
    - Pass/fail determination
    - SGPA calculation
    - Database updates
    - Batch processing
    """
    
    # =========================================================================
    # GRADING SYSTEM
    # =========================================================================
    
    # =========================================================================
    # GRADING SYSTEM (Choice-Based Credit System - CBCS)
    # =========================================================================
    # Tuple Format: (Percentage Threshold, Letter Grade, Grade Point, Description)
    GRADE_THRESHOLDS = [
        (91, 'O', 10, 'Outstanding'),
        (81, 'A++', 9, 'Excellent'),
        (71, 'A+', 8, 'Very Good'),
        (61, 'A', 7, 'Good'),
        (51, 'B+', 6, 'Average'),
        (45, 'B', 5, 'Pass'),
        (0, 'F', 0, 'Fail'),
    ]
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    @staticmethod
    def is_non_credit_course(paper_code: str, semester: str, department_name: str = None) -> bool:
        """
        Check if course is non-credit (AECC/Environmental)
        
        Pattern:
        - Sem 1: PG-105
        - Sem 2: PG-206
        - Sem 3: PG-306
        - Sem 4: None
        """
        if not paper_code:
            return False
        
        # Music department may have different pattern
        if department_name and department_name.lower() == "music":
            return False
        
        # Check PG-xxx pattern
        if paper_code.startswith("PG-"):
            code_num = paper_code.replace("PG-", "").strip()
            if semester == "1" and code_num == "PG105":
                return True
            elif semester == "2" and code_num == "PG206":
                return True
            elif semester == "3" and code_num == "PG306":
                return True
        
        return False
    
    @staticmethod
    def calculate_grade(marks: Decimal, max_marks: Decimal, is_absent: bool = False) -> Tuple[str, int]:
        """
        Calculate letter grade and grade point from marks.
        
        Logic:
        1. If marked as absent -> 'Ab' (0 points)
        2. Calculate percentage
        3. Match against GRADE_THRESHOLDS list
        """
        if is_absent:
            return ('Ab', 0)
        
        if max_marks == 0:
            return ('F', 0)
        
        percentage = (Decimal(marks) / Decimal(max_marks)) * 100
        
        # Iterate through thresholds (highest to lowest)
        for threshold, grade, points, _ in PGResultService.GRADE_THRESHOLDS:
            if percentage >= threshold:
                return (grade, points)
        
        return ('F', 0)
    
    @staticmethod
    def _is_cia(label):
        """Check if label indicates CIA (Internal)"""
        if not label: return False
        l = label.upper()
        return 'CIA' in l or l == 'MID_TERM'

    @staticmethod
    def _is_ese(label):
        """Check if label indicates ESE (External)"""
        if not label: return False
        l = label.upper()
        return 'ESE' in l or l == 'END_TERM' or l == 'END2_TERM'
    
    # =========================================================================
    # LEVEL 1: INDIVIDUAL ASSESSMENT (CIA/ESE)
    # =========================================================================
    
    @staticmethod
    def check_individual_pass(assessment) -> bool:
        """
        Check if a single assessment record (e.g., just CIA Theory) is passed.
        
        Logic:
        - Must not be absent
        - Must have marks_obtained
        - If pass_marks is defined (e.g., 40% target), marks must be >= pass_marks
        """
        if assessment.ind_is_absent:
            return False
        
        if assessment.ind_marks_obtained is None:
            return False
        
        if assessment.ind_pass_marks is None:
            return True
        
        return assessment.ind_marks_obtained >= assessment.ind_pass_marks
    
    # =========================================================================
    # LEVEL 2: COMBINED ASSESSMENT (CIA + ESE)
    # =========================================================================
    
    @staticmethod
    def calculate_combined(cia_assessment, ese_assessment) -> Dict:
        """
        Combine CIA (Internal) and ESE (External) results for a single paper.
        
        Rules:
        - Total Marks = CIA + ESE
        - Total Status = CIA Passed AND ESE Passed AND Combined Marks >= Combined Pass Marks
        """
        cia_marks = cia_assessment.ind_marks_obtained or Decimal(0)
        ese_marks = ese_assessment.ind_marks_obtained or Decimal(0)
        
        cia_max = cia_assessment.ind_max_marks or 0
        ese_max = ese_assessment.ind_max_marks or 0
        
        cia_pass = cia_assessment.ind_pass_marks or Decimal(0)
        ese_pass = ese_assessment.ind_pass_marks or Decimal(0)
        
        comb_marks = cia_marks + ese_marks
        comb_max = cia_max + ese_max
        comb_pass_marks = cia_pass + ese_pass
        
        # Verify individual pass status for both components
        cia_passed = PGResultService.check_individual_pass(cia_assessment)
        ese_passed = PGResultService.check_individual_pass(ese_assessment)
        
        # Overall course-level pass requirement
        combined_passed = cia_passed and ese_passed and (comb_marks >= comb_pass_marks)
        
        return {
            'comb_marks_obtained': comb_marks,
            'comb_max_marks': comb_max,
            'comb_pass_marks': comb_pass_marks,
            'cia_passed': cia_passed,
            'ese_passed': ese_passed,
            'combined_passed': combined_passed
        }
    
    # =========================================================================
    # LEVEL 3: COURSE LEVEL (Grade, Credits)
    # =========================================================================
    
    @staticmethod
    def calculate_course_result(
        student_id: int,
        semester: str,
        paper_code: str,
        session: str = None,
        assessments: Optional[List] = None
    ) -> Dict:
        """
        Aggregates multiple assessment labels (CIA-Theory, CIA-Practical, ESE-Theory, etc.)
        into a final course-level result (Grade and Credits).
        
        Logic:
        1. Identify the Course Structure to find "Max Credit" and "Effective Credit".
        2. Identify if the course is non-credit (Environmental, etc.).
        3. Determine if ALL CIA components and ALL ESE components were passed.
        4. Calculate the letter grade based on total marks.
        5. Award credits only if the course is passed (PASS = EARNED).
        """
        from pg.models import PGStudentCourseAssessment, PGCourseStructure
        
        # [Assessments Fetching] ...
        if assessments is None:
            filters = {
                'student_id': student_id,
                'semester': semester,
                'paper_code': paper_code
            }
            if session:
                filters['session'] = session
            
            assessment_list = list(
                PGStudentCourseAssessment.objects.filter(**filters).order_by('label')
            )
        else:
            assessment_list = [
                a for a in assessments 
                if a.paper_code == paper_code and a.semester == semester
            ]
            assessment_list.sort(key=lambda x: x.label or '')
        
        if not assessment_list:
            return {
                'paper_code': paper_code,
                'passed': False,
                'reason': 'No assessments found',
                'is_non_credit': False
            }
        
        # [Normalizing Paper Code] for PGCourseStructure lookup
        # Staging data often has 'PG-' prefixes or suffixes unlike the structure table.
        lookup_paper_code = paper_code
        if paper_code.startswith('PG-'):
            lookup_paper_code = paper_code[3:]  # Remove 'PG-'
        elif paper_code.startswith('PG'):
            lookup_paper_code = paper_code[2:]  # Remove 'PG'
        
        # Normalize semester strings (e.g. '1ST' -> '1')
        lookup_semester = semester
        if semester.endswith('ST') or semester.endswith('ND') or semester.endswith('RD') or semester.endswith('TH'):
            lookup_semester = semester[0]
        
        # Lookup course structure (with department priority)
        department = assessment_list[0].department if assessment_list[0].department else None
        
        course_structure = None
        if department:
            course_structure = PGCourseStructure.objects.filter(
                paper_code=lookup_paper_code,
                semester=lookup_semester,
                department=department
            ).first()
        
        if not course_structure:
            course_structure = PGCourseStructure.objects.filter(
                paper_code=lookup_paper_code,
                semester=lookup_semester
            ).first()
        
        # Detect non-credit status
        department_name = None
        if assessment_list[0].department:
            department_name = assessment_list[0].department.name
        
        is_non_credit = PGResultService.is_non_credit_course(
            paper_code, semester, department_name
        )
        
        # [Separating Components]
        cia_assessments = [a for a in assessment_list if PGResultService._is_cia(a.label)]
        ese_assessments = [a for a in assessment_list if PGResultService._is_ese(a.label)]
        
        total_marks = sum(a.ind_marks_obtained or 0 for a in assessment_list)
        total_max_marks = sum(a.ind_max_marks or 0 for a in assessment_list)
        
        # Pass status check: Must pass every separate CIA and every separate ESE
        all_cia_passed = all(PGResultService.check_individual_pass(a) for a in cia_assessments) if cia_assessments else True
        all_ese_passed = all(PGResultService.check_individual_pass(a) for a in ese_assessments) if ese_assessments else True
        
        course_passed = all_cia_passed and all_ese_passed
        
        # CBCS Grade Calculation
        final_grade, grade_point = PGResultService.calculate_grade(
            total_marks,
            total_max_marks,
            is_absent=any(a.ind_is_absent for a in assessment_list)
        )
        
        # [Credit Allocation]
        # effective_credit = 0 for compulsory non-credit papers (like AEC/SEC)
        effective_credit = Decimal(0)
        max_credit = Decimal(0)
        
        if course_structure:
            if course_structure.effective_credit is not None:
                effective_credit = Decimal(course_structure.effective_credit)
            elif course_structure.max_credit:
                effective_credit = Decimal(course_structure.max_credit)
            
            if course_structure.max_credit:
                max_credit = Decimal(course_structure.max_credit)
        elif assessment_list[0].comb_max_credits:
            effective_credit = Decimal(assessment_list[0].comb_max_credits)
            max_credit = Decimal(assessment_list[0].comb_max_credits)
        
        # Core Rule: 0 credits if course failed (except non-credit which are always 0)
        credits_earned = effective_credit if course_passed else Decimal(0)
        
        # Course Grade Point = GP (7) * Credits Earned (5) = 35
        course_grade_point = Decimal(grade_point) * credits_earned
        
        return {
            'paper_code': paper_code,
            'course_name': assessment_list[0].course_name,
            'passed': course_passed,
            'cia_passed': all_cia_passed,
            'ese_passed': all_ese_passed,
            'total_marks': total_marks,
            'total_max_marks': total_max_marks,
            'final_grade': final_grade,
            'grade_point': grade_point,
            'max_credit': max_credit,
            'effective_credit': effective_credit,
            'credits_earned': credits_earned,
            'course_grade_point': course_grade_point,
            'is_non_credit': is_non_credit
        }
    
    # =========================================================================
    # LEVEL 4: SEMESTER LEVEL (SGPA, Result)
    # =========================================================================
    
    @staticmethod
    def calculate_sgpa(
        student_id: int,
        semester: str,
        session: str = None,
        assessments: Optional[List] = None
    ) -> Optional[Decimal]:
        """
        Calculate the Semester Grade Point Average (SGPA).
        
        Formula: SGPA = Σ(Grade Point × Credits) / Σ(Credits)
        
        Rules:
        - Only passed courses contribute earned credits and points.
        - Non-credit courses (effective_credit=0) are completely ignored.
        - Result is rounded to 2 decimal places.
        """
        from pg.models import PGStudentCourseAssessment
        
        # [Assessments Fetching] ...
        if assessments is None:
            filters = {'student_id': student_id, 'semester': semester}
            if session: filters['session'] = session
            assessments = list(PGStudentCourseAssessment.objects.filter(**filters))
        
        paper_codes = set(a.paper_code for a in assessments if a.paper_code)
        
        total_grade_points = Decimal(0)
        total_credits_earned = Decimal(0)
        
        # Mandatory Rule: If student fails in ANY course, SGPA is 0
        all_passed = True
        
        for paper_code in paper_codes:
            # Re-use the course level logic to get validated credits and grade points
            course_result = PGResultService.calculate_course_result(
                student_id=student_id,
                semester=semester,
                paper_code=paper_code,
                session=session,
                assessments=assessments
            )
            
            if not course_result.get('passed', False):
                all_passed = False
            
            # Non-credit courses do not affect SGPA calculation
            if course_result.get('effective_credit', 0) == 0:
                continue
            
            # Sum up points (GP * Credits) and Credits
            total_grade_points += course_result['course_grade_point']
            total_credits_earned += course_result['credits_earned']
        
        if not all_passed:
            return Decimal('0.00')
            
        if total_credits_earned == 0:
            return None
        
        # Division to find average
        sgpa = total_grade_points / total_credits_earned
        return round(sgpa, 2)
    
    @staticmethod
    def determine_semester_result(
        student_id: int,
        semester: str,
        session: str = None,
        assessments: Optional[List] = None
    ) -> str:
        """
        Determine the final Semester-level result status (PASS / PROMOTED / FAIL).
        
        New Logic (Based on Paper Counts):
        - PASS: All courses passed.
        - PROMOTED:
            - If 6 Papers: Must pass at least 4.
            - If 5 Papers: Must pass at least 3.
            - If 4 Papers: Must pass at least 3.
            - Otherwise FAIL.
        - FAIL: If not satisfying above conditions.
        """
        from pg.models import PGStudentCourseAssessment
        
        # [Assessments Fetching] ...
        if assessments is None:
            filters = {'student_id': student_id, 'semester': semester}
            if session: filters['session'] = session
            assessments = list(PGStudentCourseAssessment.objects.filter(**filters))
        
        if not assessments:
            return 'FAIL'
        
        # Group assessments by paper_code to count total courses
        paper_codes = set(a.paper_code for a in assessments if a.paper_code)
        
        total_courses = 0
        passed_courses_count = 0
        
        for paper_code in paper_codes:
            # We need to Calculate course result for each paper to know if it's passed
            # Re-using calculate_course_result logic or just checking pre-calculated values if available?
            # Ideally, we should re-calculate to be safe, but this might be expensive if called repeatedly.
            # However, calculate_semester_summary calls this, and inside process_student we call summary.
            # IMPORTANT: process_student calls calculate_semester_summary which calls THIS method.
            # So inside calculate_semester_summary, we already calculated course_results!
            # But here we only have 'assessments' list.
            
            # Let's perform a lightweight check based on the assessments passed in.
            # A course is passed if ALL its components (CIA/ESE) are passed and (Combined Total >= Passed).
            # But wait, `calculate_course_result` does the exact complex logic (CBCS thresholds etc).
            # We should probably use `calculate_course_result` to be consistent.
            
            result = PGResultService.calculate_course_result(
                student_id=student_id,
                semester=semester,
                paper_code=paper_code,
                session=session,
                assessments=assessments
            )
            
            # We only count credit/main courses? The user didn't specify excluding non-credit.
            # But usually result status depends on all papers including AECC.
            # User said "if there is 5 paper...".
            
            # Checking if the course is passed
            if result['passed']:
                passed_courses_count += 1
            
            total_courses += 1
            
        print(f"DEBUG: Student {student_id} Sem {semester}: Total {total_courses}, Passed {passed_courses_count}")
        
        # 1. PASS Condition: All courses passed
        if passed_courses_count == total_courses:
            return 'PASS'
            
        # 2. PROMOTED Condition
        is_promoted = False
        
        if total_courses == 6:
            if passed_courses_count >= 4:
                is_promoted = True
        elif total_courses == 5:
            if passed_courses_count >= 3:
                is_promoted = True
        elif total_courses == 4:
             if passed_courses_count >= 3:
                 is_promoted = True
                 
        if is_promoted:
            return 'PROMOTED'
            
        # 3. FAIL
        return 'FAIL'
    
    @staticmethod
    def calculate_semester_summary(
        student_id: int,
        semester: str,
        session: str = None
    ) -> Dict:
        """
        Calculate complete semester summary
        
        Returns all calculations in one call
        """
        from pg.models import PGStudentCourseAssessment
        
        filters = {
            'student_id': student_id,
            'semester': semester
        }
        if session:
            filters['session'] = session
        
        assessments = list(PGStudentCourseAssessment.objects.filter(**filters))
        
        paper_codes = set(a.paper_code for a in assessments if a.paper_code)
        
        course_results = []
        total_max_credits = Decimal(0)
        total_credits_earned = Decimal(0)
        
        for paper_code in paper_codes:
            result = PGResultService.calculate_course_result(
                student_id=student_id,
                semester=semester,
                paper_code=paper_code,
                session=session,
                assessments=assessments
            )
            course_results.append(result)
            
            # Sum physical credits (max_credit) for the semester total
            total_max_credits += result['max_credit']
            total_credits_earned += result['credits_earned']
        
        sgpa = PGResultService.calculate_sgpa(
            student_id=student_id,
            semester=semester,
            session=session,
            assessments=assessments
        )
        
        semester_result = PGResultService.determine_semester_result(
            student_id=student_id,
            semester=semester,
            session=session,
            assessments=assessments
        )
        
        
        # Calculate semester-level CIA/ESE pass status
        # A student passes CIA/ESE for the semester if they pass it in ALL courses.
        # Note: We only consider courses that HAVE a pass/fail status (i.e., not just 'passed'=False due to missing assessments)
        # However, for simplicity and strictness:
        # cia_passed = ALL courses have cia_passed=True
        # ese_passed = ALL courses have ese_passed=True
        
        # We need to leverage the boolean flags returned by calculate_course_result
        all_cia_passed = all(r['cia_passed'] for r in course_results) if course_results else False
        all_ese_passed = all(r['ese_passed'] for r in course_results) if course_results else False

        return {
            'student_id': student_id,
            'semester': semester,
            'session': session,
            'course_results': course_results,
            'total_courses': len(course_results),
            'courses_passed': sum(1 for r in course_results if r['passed']),
            'courses_failed': sum(1 for r in course_results if not r['passed']),
            'total_max_credits': total_max_credits,
            'total_credits_earned': total_credits_earned,
            'sgpa': sgpa,
            'semester_result': semester_result,
            'cia_passed': all_cia_passed,
            'ese_passed': all_ese_passed
        }
    
    # =========================================================================
    # DATABASE UPDATE METHODS
    # =========================================================================
    
    @staticmethod
    @transaction.atomic
    def process_student(
        student_id: int,
        semester: str,
        session: str,
        dry_run: bool = False
    ) -> Dict:
        """
        The Main Entry Point (Orchestrator) for result processing for a single student.
        
        This method performs a comprehensive calculation and update process for a student's
        semester results, including individual assessment statuses, course-level aggregates,
        and overall semester summary (SGPA, result status).
        
        Steps:
        1. Calculates all course-level results (grades, credits earned, pass/fail status).
        2. Aggregates these course results into a Semester-Level summary (SGPA, overall PASS/PROMOTED/FAIL).
        3. Updates individual `PGStudentCourseAssessment` records with calculated values
           (e.g., `ind_is_pass`, combined marks, grade points, credits).
        4. Creates or updates the `PGExamResult` summary record for the semester.
        5. Automatically creates a `PGSemesterRegistration` record for the next semester
           if the student is eligible (PASS/PROMOTED).
        
        Args:
            student_id (int): The ID of the student to process.
            semester (str): The semester string (e.g., '1ST', '2ND').
            session (str): The academic session string.
            dry_run (bool, optional): If True, calculations are performed but no changes
                                      are saved to the database. Defaults to False.
        
        Returns:
            Dict: A dictionary containing processing status, student ID, and the calculated summary.
                  Includes 'success' (bool), 'student_id' (int), and 'summary' (Dict) or 'error' (str).
        """
        from pg.models import PGStudentCourseAssessment, PGExamResult, PGStudentProfile
        
        try:
            # =================================================================
            # 0. PRE-CALCULATION CHECKS
            # =================================================================
            
            sem_map_int = {'1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4}
            current_sem_num = sem_map_int.get(semester.upper())
            
            # CHECK 1: PREVIOUS SEMESTER PROMOTION (For Sem > 1)
            if current_sem_num and current_sem_num > 1:
                prev_sem_num = current_sem_num - 1
                prev_sem_str = next((k for k, v in sem_map_int.items() if v == prev_sem_num), None)
                
                if prev_sem_str:
                    # Filter by student & prev semester, order by updated_at desc to get latest
                    prev_result = PGExamResult.objects.filter(
                        student_id=student_id,
                        semester=prev_sem_str
                    ).order_by('-updated_at').first()
                    
                    if not prev_result:
                        return {
                            'success': False,
                            'error': f"SKIPPING: No result record found for previous semester {prev_sem_str}"
                        }
                    
                    if prev_result.semester_result not in ['PASS', 'PROMOTED']:
                        return {
                            'success': False,
                            'error': f"SKIPPING: Student not promoted from {prev_sem_str} (Status: {prev_result.semester_result})"
                        }

            # CHECK 2: CURRENT SEMESTER CIA PASS STATUS
            # The PGExamResult record should have been created by Step 1 (CIA Processing)
            current_result_pre = PGExamResult.objects.filter(
                student_id=student_id,
                semester=semester,
                session=session
            ).first()
            
            if not current_result_pre:
                return {
                    'success': False,
                    'error': f"SKIPPING: No CIA/Initial result record found for current semester {semester}. Run CIA Step 1 first."
                }
                
            if not current_result_pre.cia_pass:
                return {
                    'success': False,
                    'error': f"SKIPPING: Student failed in CIA for current semester {semester}."
                }

            # =================================================================
            # END CHECKS
            # =================================================================
            
            # Step A: Perform all necessary calculations for the semester summary
            summary = PGResultService.calculate_semester_summary(
                student_id=student_id,
                semester=semester,
                session=session
            )
            
            # Step B: Load all relevant PGStudentCourseAssessment records for the student and semester.
            # These records will be updated with the calculated values.
            assessments = PGStudentCourseAssessment.objects.filter(
                student_id=student_id,
                semester=semester,
                session=session
            )
            
            # Step C: Iterate through each paper (course) and update its associated assessment records.
            # This involves setting individual pass status, combined marks, grade points, and credits.
            paper_codes = set(a.paper_code for a in assessments if a.paper_code)
            
            for paper_code in paper_codes:
                # 1. Isolate the binary components (CIA vs ESE) for this specific paper_code.
                # We assume each paper has at least one CIA and one ESE component for combined calculation.
                cia = assessments.filter(
                    Q(label__icontains='CIA') | Q(label='MID_TERM'),
                    paper_code=paper_code
                ).first()
                
                ese = assessments.filter(
                    Q(label__icontains='ESE') | Q(label='END_TERM') | Q(label='END2_TERM'),
                    paper_code=paper_code
                ).first()
                
                # If either component is missing, we cannot calculate combined results for this paper.
                if not cia or not ese: continue
                
                # 2. Retrieve the pre-calculated combined and course-level results for this paper.
                combined = PGResultService.calculate_combined(cia, ese)
                course_result = next((r for r in summary['course_results'] if r['paper_code'] == paper_code), None)
                
                # If course result is missing from summary, skip this paper.
                if not course_result: continue
                
                # 3. Update both the CIA and ESE assessment records with combined and course-level data.
                for assessment in [cia, ese]:
                    # Update individual pass status for the assessment component.
                    assessment.ind_is_pass = PGResultService.check_individual_pass(assessment)
                    
                    # Populate combined fields based on the `calculate_combined` result.
                    assessment.comb_marks_obtained   = combined['comb_marks_obtained']
                    assessment.comb_max_marks         = combined['comb_max_marks']
                    assessment.comb_pass_marks        = combined['comb_pass_marks']
                    
                    # `comb_max_credits` stores the raw physical credit weight (e.g., 5.0)
                    assessment.comb_max_credits      = course_result['max_credit']
                    
                    # `comb_credit_obtained` stores the effective credit earned (e.g., 5.0 or 0.0)
                    assessment.comb_credit_obtained   = course_result['credits_earned']
                    
                    # Populate grade point fields. `comb_numeric_grade` is the raw GP (e.g., 7),
                    # `comb_grade_point` is the weighted GP (GP * Credits).
                    assessment.comb_numeric_grade    = course_result['grade_point'] # GP (e.g. 7)
                    assessment.comb_grade_point      = course_result['course_grade_point'] # Course GP (e.g. 35)

                    # Semester Redundancy: Store SGPA and semester result directly on assessment records
                    # for easier reporting and data access without needing to join to PGExamResult.
                    assessment.sgpa = summary['sgpa']
                    assessment.sem_result = summary['semester_result']

                    # New Fields: Semester Max Credit and Earned Credit
                    assessment.sem_max_credit = summary['total_max_credits'] 
                    assessment.sem_credit_obtained = summary['total_credits_earned']
                    
                    # Save the updated assessment record if not in dry-run mode.
                    if not dry_run:
                        assessment.save()
            
            # Step D: Finalize the semester summary record in PGExamResult and handle next semester registration.
            if not dry_run:
                # Fetch student profile for foreign key relationship.
                student = PGStudentProfile.objects.get(id=student_id)
                
                # Determine the next semester value based on the current semester.
                next_sem_val = PGResultService._get_next_semester(semester)
                
                # Determine the student's eligibility status for the next semester.
                # 'ELIGIBLE' if PASS/PROMOTED and a next semester exists.
                # 'COMPLETED' if PASS/PROMOTED but no further semesters are defined (e.g., end of program).
                # 'NOT_ELIGIBLE' if FAIL.
                next_sem_status = 'NOT_ELIGIBLE'
                if summary['semester_result'] in ['PASS', 'PROMOTED']:
                    next_sem_status = 'ELIGIBLE' if next_sem_val else 'COMPLETED'
                
                # Create or update the PGExamResult record with the semester's overall summary.
                PGExamResult.objects.update_or_create(
                    student=student,
                    semester=semester,
                    session=session,
                    defaults={
                        'semester_result': summary['semester_result'],
                        'semester_max_credit': int(summary['total_max_credits']),
                        'semester_credit_earned': int(summary['total_credits_earned']),
                        'sgpa': summary['sgpa'],
                        'next_semester': next_sem_val if next_sem_status == 'ELIGIBLE' else None,
                        'next_sem_status': next_sem_status,
                        'cia_pass': summary['cia_passed'],
                        'ese_pass': summary['ese_passed']
                    }
                )
                
                # [Automation] If the student is eligible for the next semester,
                # create a PGSemesterRegistration record to facilitate their enrollment.
                if next_sem_status == 'ELIGIBLE' and next_sem_val:
                    PGResultService._create_next_sem_registration(student, next_sem_val, session, semester)
            
            # Return success status and the calculated summary.
            return {'success': True, 'student_id': student_id, 'summary': summary}

        except Exception as e:
            # If any error occurs during processing, return a failure status with the error message.
            return {'success': False, 'student_id': student_id, 'error': str(e)}

    @staticmethod
    def _get_next_semester(current_sem_str):
        """Map current semester string to next semester integer"""
        mapping = {
            '1ST': 2, 'I': 2, '1': 2,
            '2ND': 3, 'II': 3, '2': 3,
            '3RD': 4, 'III': 4, '3': 4,
            '4TH': 5, 'IV': 5, '4': 5
        }
        return mapping.get(current_sem_str.upper())

    @staticmethod
    def _get_next_session(current_session, current_sem_val, next_sem_val):
        """
        Calculate the next session based on semester transition.
        
        For 2-year PG courses (4 semesters):
        - Year 1: Sem 1 (2024-25), Sem 2 (2024-25)
        - Year 2: Sem 3 (2025-26), Sem 4 (2025-26)
        
        Session increments when moving from even semester to odd semester (new year).
        
        Args:
            current_session (str): Current session like '2024-25'
            current_sem_val (int): Current semester number (1-4)
            next_sem_val (int): Next semester number (2-5)
        
        Returns:
            str: Next session string
        """
        # If moving from even semester to odd semester (e.g., 2→3, 4→5), increment year
        # This represents moving to a new academic year
        if current_sem_val % 2 == 0 and next_sem_val % 2 == 1:
            # Parse current session (e.g., '2024-25')
            try:
                parts = current_session.split('-')
                if len(parts) == 2:
                    start_year = int(parts[0])
                    end_year = int(parts[1])
                    
                    # Increment both years
                    new_start = start_year + 1
                    new_end = end_year + 1
                    
                    return f"{new_start}-{new_end:02d}"
            except (ValueError, AttributeError):
                pass
        
        # Otherwise, keep the same session
        return current_session

    @staticmethod
    def _create_next_sem_registration(student, next_sem_val, session, current_sem_str):
        """
        Create PGSemesterRegistration for next semester with correct session.
        """
        from pg.models import PGSemesterRegistration, PGDegree
        
        try:
            # Check if 2-year program (4 semesters)
            # If student passed 4th, don't register for 5th unless program allows
            if next_sem_val > 4: 
                # Ideally check student.degree.total_semesters
                # Creating safeguards
                if student.degree and student.degree.total_semesters:
                    if next_sem_val > student.degree.total_semesters:
                        return

            # Calculate the correct session for next semester
            # Get current semester number
            sem_map = {'1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4}
            current_sem_val = sem_map.get(current_sem_str.upper(), 1)
            
            # Determine next session based on year transition
            next_session = PGResultService._get_next_session(session, current_sem_val, next_sem_val)

            PGSemesterRegistration.objects.get_or_create(
                student=student,
                sem=next_sem_val,
                session=next_session,  # Use calculated next session
                defaults={
                    'status': 'PENDING',
                    'is_open': True,
                    'exam_eligible': False,
                    'remarks': f'Promoted from {current_sem_str} ({session}) to Sem {next_sem_val} ({next_session})'
                }
            )
        except Exception as e:
            # Log error but don't fail the whole result process
            print(f"Error creating registration for {student.registration_no}: {e}")
    
    # =========================================================================
    # BATCH PROCESSING
    # =========================================================================
    
    @staticmethod
    def process_semester(
        semester: str,
        session: str,
        dry_run: bool = False,
        limit: Optional[int] = None,
        verbose: bool = True
    ) -> Dict:
        """
        Process all students in a semester
        
        Args:
            semester: Semester to process
            session: Session to process
            dry_run: If True, don't save to database
            limit: Optional limit on number of students
            verbose: If True, print progress
        
        Returns:
            Dict with processing summary
        """
        from pg.models import PGStudentCourseAssessment
        
        if verbose:
            print("=" * 80)
            print("PG RESULT PROCESSING")
            print("=" * 80)
            print(f"Semester: {semester}")
            print(f"Session: {session}")
            print(f"Dry Run: {dry_run}")
            if limit:
                print(f"Limit: {limit} students")
            print("=" * 80)
            print()
        
        # Get students
        student_ids = PGStudentCourseAssessment.objects.filter(
            semester=semester,
            session=session
        ).values_list('student_id', flat=True).distinct()
        
        if limit:
            student_ids = list(student_ids)[:limit]
        else:
            student_ids = list(student_ids)
        
        total_students = len(student_ids)
        
        if verbose:
            print(f"Found {total_students} students with assessments")
            print()
        
        # Process each student
        success_count = 0
        error_count = 0
        
        results_summary = {
            'PASS': 0,
            'PROMOTED': 0,
            'FAIL': 0
        }
        
        for idx, student_id in enumerate(student_ids, 1):
            if verbose:
                print(f"[{idx}/{total_students}] Processing Student ID: {student_id}...", end=" ")
            
            result = PGResultService.process_student(
                student_id=student_id,
                semester=semester,
                session=session,
                dry_run=dry_run
            )
            
            if result['success']:
                success_count += 1
                sem_result = result['summary']['semester_result']
                results_summary[sem_result] = results_summary.get(sem_result, 0) + 1
                
                if verbose:
                    sgpa = result['summary']['sgpa']
                    sgpa_str = f"{sgpa:.2f}" if sgpa else "N/A"
                    print(f"✓ {sem_result} | SGPA: {sgpa_str}")
            else:
                error_count += 1
                if verbose:
                    print(f"✗ ERROR: {result['error']}")
        
        # Print summary
        if verbose:
            print()
            print("=" * 80)
            print("PROCESSING SUMMARY")
            print("=" * 80)
            print(f"Total Students: {total_students}")
            print(f"Successfully Processed: {success_count}")
            print(f"Errors: {error_count}")
            print()
            print("Result Distribution:")
            print(f"  PASS: {results_summary.get('PASS', 0)}")
            print(f"  PROMOTED: {results_summary.get('PROMOTED', 0)}")
            print(f"  FAIL: {results_summary.get('FAIL', 0)}")
            print("=" * 80)
            
            if dry_run:
                print()
                print("⚠️  DRY RUN MODE - No changes were saved to the database")
                print("   Run without dry_run=True to save results")
        
        return {
            'total_students': total_students,
            'success_count': success_count,
            'error_count': error_count,
            'results_summary': results_summary
        }
