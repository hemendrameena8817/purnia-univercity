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
        """Calculate letter grade and grade point from marks"""
        if is_absent:
            return ('Ab', 0)
        
        if max_marks == 0:
            return ('F', 0)
        
        percentage = (Decimal(marks) / Decimal(max_marks)) * 100
        
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
        Check if individual assessment passed
        
        Criteria:
        - Not absent
        - Marks >= Pass marks
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
        Calculate combined CIA + ESE for a course
        
        Returns:
            Dict with combined marks and pass status
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
        
        cia_passed = PGResultService.check_individual_pass(cia_assessment)
        ese_passed = PGResultService.check_individual_pass(ese_assessment)
        
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
        Calculate complete course result
        
        Returns:
            Dict with grade, credits, pass status
        """
        from pg.models import PGStudentCourseAssessment, PGCourseStructure
        
        # Get assessments
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
        
        # Get course structure
        # Strip 'PG' or 'PG-' prefix from paper_code if present
        # Assessment has 'PG105' but course structure has '105'
        lookup_paper_code = paper_code
        if paper_code.startswith('PG-'):
            lookup_paper_code = paper_code[3:]  # Remove 'PG-'
        elif paper_code.startswith('PG'):
            lookup_paper_code = paper_code[2:]  # Remove 'PG'
        
        # Normalize semester: '1ST' -> '1', '2ND' -> '2', etc.
        lookup_semester = semester
        if semester.endswith('ST') or semester.endswith('ND') or semester.endswith('RD') or semester.endswith('TH'):
            lookup_semester = semester[0]  # Get first character
        
        # Get department for filtering
        department = assessment_list[0].department if assessment_list[0].department else None
        
        # Lookup course structure with department filter
        # Different departments may have different credits for same paper code
        course_structure = None
        if department:
            course_structure = PGCourseStructure.objects.filter(
                paper_code=lookup_paper_code,
                semester=lookup_semester,
                department=department
            ).first()
        
        # Fallback: try without department filter
        if not course_structure:
            course_structure = PGCourseStructure.objects.filter(
                paper_code=lookup_paper_code,
                semester=lookup_semester
            ).first()
        
        # Check if non-credit
        department_name = None
        if assessment_list[0].department:
            department_name = assessment_list[0].department.name
        
        is_non_credit = PGResultService.is_non_credit_course(
            paper_code, semester, department_name
        )
        
        # Separate CIA and ESE
        cia_assessments = [
            a for a in assessment_list 
            if PGResultService._is_cia(a.label)
        ]
        ese_assessments = [
            a for a in assessment_list 
            if PGResultService._is_ese(a.label)
        ]
        
        # Calculate total marks
        total_marks = sum(a.ind_marks_obtained or 0 for a in assessment_list)
        total_max_marks = sum(a.ind_max_marks or 0 for a in assessment_list)
        
        # Check pass status
        all_cia_passed = all(
            PGResultService.check_individual_pass(a) for a in cia_assessments
        ) if cia_assessments else True
        
        all_ese_passed = all(
            PGResultService.check_individual_pass(a) for a in ese_assessments
        ) if ese_assessments else True
        
        course_passed = all_cia_passed and all_ese_passed
        
        # Calculate grade
        final_grade, grade_point = PGResultService.calculate_grade(
            total_marks,
            total_max_marks,
            is_absent=any(a.ind_is_absent for a in assessment_list)
        )
        
        # Get credits from PGCourseStructure
        # Use effective_credit (not max_credit) for actual credit calculation
        # effective_credit = 0 means non-credit course (like Environmental)
        # effective_credit = 5 means regular credit course
        effective_credit = Decimal(0)
        max_credit = Decimal(0)
        
        if course_structure:
            # Primary source: effective_credit from course structure
            if course_structure.effective_credit is not None:
                effective_credit = Decimal(course_structure.effective_credit)
            # Fallback: max_credit if effective_credit not set
            elif course_structure.max_credit:
                effective_credit = Decimal(course_structure.max_credit)
            
            # max_credit is for reference only
            if course_structure.max_credit:
                max_credit = Decimal(course_structure.max_credit)
        elif assessment_list[0].comb_max_credits:
            # Fallback to assessment data if no course structure
            effective_credit = Decimal(assessment_list[0].comb_max_credits)
            max_credit = Decimal(assessment_list[0].comb_max_credits)
        
        # Award credits based on effective_credit
        # If effective_credit = 0, no credits awarded (non-credit course)
        # If effective_credit > 0, award credits only if course passed
        credits_earned = effective_credit if course_passed else Decimal(0)
        
        # Calculate grade point using effective_credit
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
        Calculate semester SGPA
        
        Formula: SGPA = Σ(grade_point × credit) / Σ(credits_earned)
        Note: Excludes non-credit courses
        """
        from pg.models import PGStudentCourseAssessment
        
        if assessments is None:
            filters = {
                'student_id': student_id,
                'semester': semester
            }
            if session:
                filters['session'] = session
            
            assessments = list(PGStudentCourseAssessment.objects.filter(**filters))
        
        paper_codes = set(a.paper_code for a in assessments if a.paper_code)
        
        total_grade_points = Decimal(0)
        total_credits_earned = Decimal(0)
        
        for paper_code in paper_codes:
            course_result = PGResultService.calculate_course_result(
                student_id=student_id,
                semester=semester,
                paper_code=paper_code,
                session=session,
                assessments=assessments
            )
            
            # Skip courses with effective_credit = 0 (non-credit courses)
            # These courses must be passed but don't contribute to SGPA
            if course_result.get('effective_credit', 0) == 0:
                continue
            
            # Add grade points and credits earned (only for passed courses)
            # If course failed, credits_earned = 0, so it won't contribute to SGPA
            total_grade_points += course_result['course_grade_point']
            total_credits_earned += course_result['credits_earned']
        
        if total_credits_earned == 0:
            return None
        
        # SGPA = Σ(grade_point × credits_earned) / Σ(credits_earned)
        # Only passed courses contribute to SGPA
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
        Determine semester result based on CIA and ESE performance
        
        Rules:
        1. PASS: All CIA passed AND All ESE passed
           - Student successfully completed the semester
           - Can move to next semester with all courses cleared
        
        2. PROMOTED: All CIA passed BUT Some/All ESE failed
           - Student is promoted to next semester
           - Must clear failed ESE papers later (backlog)
           - CIA passing is mandatory for promotion
        
        3. FAIL: Some/All CIA failed
           - Student cannot be promoted
           - Must repeat the semester
           - ESE status doesn't matter if CIA failed
        
        Important:
        - CIA (Continuous Internal Assessment) is mandatory
        - ESE (End Semester Exam) can be cleared later if CIA passed
        - Absent in CIA = FAIL (no promotion)
        - Absent in ESE = PROMOTED (if CIA passed)
        """
        from pg.models import PGStudentCourseAssessment
        
        if assessments is None:
            filters = {
                'student_id': student_id,
                'semester': semester
            }
            if session:
                filters['session'] = session
            
            assessments = list(PGStudentCourseAssessment.objects.filter(**filters))
        
        if not assessments:
            return 'FAIL'
        
        # Separate CIA and ESE assessments
        cia_assessments = [
            a for a in assessments 
            if PGResultService._is_cia(a.label)
        ]
        ese_assessments = [
            a for a in assessments 
            if PGResultService._is_ese(a.label)
        ]
        
        # Check if ALL CIA assessments passed
        # CIA is mandatory - if any CIA fails, student cannot be promoted
        all_cia_passed = all(
            PGResultService.check_individual_pass(a) 
            for a in cia_assessments
        ) if cia_assessments else False
        
        # Check if ALL ESE assessments passed
        # ESE can fail - student will be promoted but must clear ESE later
        all_ese_passed = all(
            PGResultService.check_individual_pass(a) 
            for a in ese_assessments
        ) if ese_assessments else False
        
        # Determine final result
        if all_cia_passed and all_ese_passed:
            # Perfect! All assessments cleared
            return 'PASS'
        elif all_cia_passed and not all_ese_passed:
            # CIA passed but ESE failed - promote with backlog
            return 'PROMOTED'
        else:
            # CIA failed - cannot proceed to next semester
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
            
            # Use effective_credit for total calculation
            # This ensures non-credit courses (effective_credit=0) don't count
            total_max_credits += result.get('effective_credit', result['max_credit'])
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
            'semester_result': semester_result
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
        Process and save results for one student
        
        Updates:
        - PGStudentCourseAssessment (all calculated fields)
        - PGExamResult (semester summary)
        """
        from pg.models import PGStudentCourseAssessment, PGExamResult, PGStudentProfile
        
        try:
            # Calculate summary
            summary = PGResultService.calculate_semester_summary(
                student_id=student_id,
                semester=semester,
                session=session
            )
            
            # Get assessments
            assessments = PGStudentCourseAssessment.objects.filter(
                student_id=student_id,
                semester=semester,
                session=session
            )
            
            # Update individual pass status
            for assessment in assessments:
                assessment.ind_is_pass = PGResultService.check_individual_pass(assessment)
                if not dry_run:
                    assessment.save(update_fields=['ind_is_pass'])
            
            # Update combined and course fields
            paper_codes = set(a.paper_code for a in assessments if a.paper_code)
            
            for paper_code in paper_codes:
                cia = assessments.filter(
                    Q(label__icontains='CIA') | Q(label='MID_TERM'),
                    paper_code=paper_code
                ).first()
                
                ese = assessments.filter(
                    Q(label__icontains='ESE') | Q(label='END_TERM') | Q(label='END2_TERM'),
                    paper_code=paper_code
                ).first()
                
                if not cia or not ese:
                    continue
                
                # Calculate combined
                combined = PGResultService.calculate_combined(cia, ese)
                
                # Get course result
                course_result = next(
                    (r for r in summary['course_results'] if r['paper_code'] == paper_code),
                    None
                )
                
                if not course_result:
                    continue
                
                # Update both CIA and ESE
                for assessment in [cia, ese]:
                    # Combined fields
                    assessment.comb_marks_obtained = combined['comb_marks_obtained']
                    assessment.comb_max_marks = combined['comb_max_marks']
                    assessment.comb_pass_marks = combined['comb_pass_marks']
                    
                    # Credit population logic requested by user:
                    # - If Pass in CIA but Fail in ESE -> Credit = 0
                    # - If Pass, credit = max_credit
                    # This logic is already handled by 'course_passed' in calculate_course_result:
                    # course_passed = all_cia_passed and all_ese_passed
                    # credits_earned = effective_credit if course_passed else 0
                    
                    # Set comb_max_credits explicitly from course structure/effective credit
                    assessment.comb_max_credits = course_result['effective_credit']
                    
                    # Set comb_credit_obtained explicitly based on earned credits
                    assessment.comb_credit_obtained = course_result['credits_earned']
                    
                    # GP mapping requested by user
                    assessment.comb_numeric_grade = course_result['grade_point'] # GP (e.g. 7)
                    assessment.comb_grade_point = course_result['course_grade_point'] # Course GP (e.g. 35)

                    # Course fields
                    assessment.course_max_marks = course_result['total_max_marks']
                    assessment.course_max_credits = course_result['max_credit']
                    assessment.course_marks_obtained = course_result['total_marks']
                    assessment.course_credit_obtained = course_result['credits_earned']
                    assessment.course_grade_point = course_result['course_grade_point']
                    
                    # Semester fields
                    assessment.sem_max_credit = summary['total_max_credits']
                    assessment.sem_credit_obtained = summary['total_credits_earned']
                    assessment.sgpa = summary['sgpa']
                    assessment.sem_result = summary['semester_result']
                    
                    if not dry_run:
                        assessment.save()
            
            # Create/update PGExamResult
            if not dry_run:
                student = PGStudentProfile.objects.get(id=student_id)
                
                cia_assessments = [a for a in assessments if PGResultService._is_cia(a.label)]
                ese_assessments = [a for a in assessments if PGResultService._is_ese(a.label)]
                
                cia_pass = all(a.ind_is_pass for a in cia_assessments) if cia_assessments else None
                ese_pass = all(a.ind_is_pass for a in ese_assessments) if ese_assessments else None
                

                # Calculate next semester value
                next_sem_val = PGResultService._get_next_semester(semester)
                
                # Determine next semester status
                next_sem_status = 'NOT_ELIGIBLE'
                if summary['semester_result'] in ['PASS', 'PROMOTED']:
                    if next_sem_val:
                         # Check if degree complete logic (optional, but good for validation)
                         next_sem_status = 'ELIGIBLE'
                    else:
                         next_sem_status = 'COMPLETED' # Or similar if no next sem
                
                PGExamResult.objects.update_or_create(
                    student=student,
                    semester=semester,
                    session=session,
                    defaults={
                        'cia_pass': cia_pass,
                        'ese_pass': ese_pass,
                        'semester_result': summary['semester_result'],
                        'semester_max_credit': int(summary['total_max_credits']),
                        'semester_credit_earned': int(summary['total_credits_earned']),
                        'sgpa': summary['sgpa'],
                        'is_legacy': False,
                        'next_semester': next_sem_val if next_sem_status == 'ELIGIBLE' else None,
                        'next_sem_status': next_sem_status
                    }
                )
                
                # Create Next Semester Registration if Eligible
                if next_sem_status == 'ELIGIBLE' and next_sem_val:
                    PGResultService._create_next_sem_registration(student, next_sem_val, session, semester)
            
            return {
                'success': True,
                'student_id': student_id,
                'summary': summary
            }

        except Exception as e:
            return {
                'success': False,
                'student_id': student_id,
                'error': str(e)
            }

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
    def _create_next_sem_registration(student, next_sem_val, session, current_sem_str):
        """
        Create PGSemesterRegistration for next semester.
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

            PGSemesterRegistration.objects.get_or_create(
                student=student,
                sem=next_sem_val,
                session=session, # Kept same session as per instruction/UG logic
                defaults={
                    'status': 'PENDING',
                    'is_open': True,
                    'exam_eligible': False,
                    'remarks': f'Promoted from {current_sem_str}'
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
