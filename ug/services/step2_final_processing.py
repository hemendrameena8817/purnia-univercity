"""
Step 2: Final Result Processing Service (Post-ESE)

Processes final semester results after ESE marks entry:
1. Calculates combined marks (CIA + ESE) and grades for each course
2. Updates StudentCourseAssessment with final course-level data
3. Calculates SGPA and Semester Result (PASS/FAIL/PROMOTED/QUALIFIED/DISQUALIFIED)
4. Updates UGExamResult with final stats
5. Creates SemesterRegistration for next semester if eligible

Run this script after ALL ESE marks have been entered.
"""

from decimal import Decimal
from typing import Dict, List, Optional
from django.db import transaction
from django.db.models import Q
import datetime

from ug.models import (
    UGStudentProfile,
    StudentCourseAssessment,
    UGExamResult,
    SemesterRegistration,
    CourseStructure
)
from ug.services.result_calculator import UGResultCalculator


class FinalResultProcessingService:
    """
    Step 2: Final Result Processing
    """
    
    def __init__(self, batch: str, semester: str, session: str, registration_no: Optional[str] = None, exam_type: str = 'REGULAR'):
        self.batch = batch
        self.semester = semester
        self.session = session
        self.registration_no = registration_no
        self.exam_type = exam_type.upper()
        # Add internal resume tracking
        self.resume = False 
        self.stats = {
            'total_students': 0,
            'processed': 0,
            'passed': 0,
            'promoted': 0,
            'failed': 0,
            'qualified': 0,
            'partly_qualified': 0,
            'disqualified': 0,
            'overall_updated': 0,
            'registrations_created': 0,
            'missing_papers': 0
        }
        
        # Optimization: Cache CourseStructure
        self.course_map = {}
        self._load_course_map()

    def _load_course_map(self):
        """Load CourseStructure into memory to avoid N+1 queries"""
        from ug.models import CourseStructure
        import re
        
        all_courses = CourseStructure.objects.all()
        for cs in all_courses:
            self.course_map[cs.paper_code] = cs
        
        # Also build reverse mapping: for assessment paper codes like 'BA1005',
        # map to the numeric-only CourseStructure '1005'
        # We'll add these as we encounter them in processing
        print(f"  [+] Loaded {len(self.course_map)} courses into cache")

    def process(self, dry_run: bool = False, resume: bool = False) -> Dict:
        """Main processing method"""
        self.resume = resume
        self._print_header()
        
        if self.registration_no:
            # Process single student
            filters = {'registration_no': self.registration_no}
            if self.batch:
                filters['batch__name'] = self.batch
            students = UGStudentProfile.objects.filter(**filters)
            print(f"\n[INFO] Processing SINGLE student: {self.registration_no}")
        else:
            # Process by session
            active_ids = StudentCourseAssessment.objects.filter(
                session=self.session,
                semester=self.semester,
                exam_type=self.exam_type
            ).values_list('student_id', flat=True).distinct()
            
            if self.batch:
                # Filter to specific batch
                students = UGStudentProfile.objects.filter(
                    id__in=active_ids,
                    batch__name=self.batch
                ).order_by('registration_no')
            else:
                # All batches in this session
                students = UGStudentProfile.objects.filter(
                    id__in=active_ids
                ).order_by('registration_no')
            
            # --- RESUME LOGIC ---
            if self.resume:
                print(f"\n[INFO] Resuming. Skipping previously processed students...")
                # Filter out students who already have a FINAL result (PASS/FAIL/PROMOTED)
                # PENDING result means Step 1 ran but Step 2 didn't finish.
                processed_ids = UGExamResult.objects.filter(
                    semester=self.semester,
                    session=self.session,
                    semester_result__in=['PASS', 'FAIL', 'PROMOTED', 'QUALIFIED', 'PARTLY_QUALIFIED', 'DISQUALIFIED']
                ).values_list('student_id', flat=True)
                
                initial_count = students.count()
                students = students.exclude(id__in=processed_ids)
                remaining_count = students.count()
                print(f"   Skipped: {initial_count - remaining_count:,} students")
                print(f"   Remaining: {remaining_count:,} students")

        self.stats['total_students'] = students.count()
        print(f"\n[INFO] Found {self.stats['total_students']:,} students to process")
        print(f"{'='*100}\n")
        
        # Use simple iteration with atomic blocks for chunks if batch is large
        # We handle transactions inside _process_all_students with chunks to avoid lock timeouts
        if not dry_run:
            self._process_all_students(students, dry_run=False)
        else:
            print("\n[INFO] DRY RUN MODE - No database changes will be made\n")
            self._process_all_students(students, dry_run=True)
            
        self._print_summary()
        return self.stats

    def _process_all_students(self, students, dry_run: bool = False):
        """Iterate and process batch of students with chunked caching/transactions"""
        chunk_size = 100
        current_chunk = []
        
        # Iterate over iterator to save memory
        for idx, student in enumerate(students.iterator(), 1):
            current_chunk.append(student)
            
            if len(current_chunk) >= chunk_size:
                self._process_student_chunk(current_chunk, dry_run)
                current_chunk = []
                print(f"  Processed {idx:,}/{self.stats['total_students']:,} students...")

        # Process remaining
        if current_chunk:
            self._process_student_chunk(current_chunk, dry_run)
            print(f"  Processed {self.stats['processed']:,}/{self.stats['total_students']:,} students...")

    def _process_student_chunk(self, chunk: List, dry_run: bool):
        """Process a chunk of students within a single transaction (if not dry_run)"""
        if dry_run:
             for student in chunk:
                 self._process_student(student, dry_run=True)
        else:
             with transaction.atomic():
                 for student in chunk:
                     self._process_student(student, dry_run=False)

    ################################################################################
    # MAIN PROCESSING PIPELINE
    ################################################################################

    def _process_student(self, student: UGStudentProfile, dry_run: bool = False):
        """Process individual student result through all levels"""
        self.stats['processed'] += 1
        
        # Optimization: Fetch assessments for this student + semester + session + exam_type
        assessments_qs = StudentCourseAssessment.objects.filter(
            student=student, 
            semester=self.semester,
            session=self.session,
            exam_type=self.exam_type
        )
        all_assessments = list(assessments_qs)
        
        if not all_assessments:
            return

        # 0. RECALCULATE ind_is_pass for every assessment (migrated data may have wrong values)
        pass_fixes = []
        for a in all_assessments:
            correct_pass = UGResultCalculator.check_individual_pass(a)
            if a.ind_is_pass != correct_pass:
                a.ind_is_pass = correct_pass
                pass_fixes.append(a)
        
        if pass_fixes and not dry_run:
            StudentCourseAssessment.objects.bulk_update(
                pass_fixes, ['ind_is_pass'], batch_size=500
            )

        # 1. Individual Level - Apply Grace Marks (NEW: Automatic calculation)
        # Must happen BEFORE combined/course processing so grace is included in all calculations
        all_assessments = UGResultCalculator.calculate_and_apply_grace(
            student.id,
            self.semester,
            all_assessments
        )
        
        # Ensure ind_final_marks_obtained is ALWAYS set for every assessment
        # - If grace applied (ind_grace_obtained > 0): final = marks + grace
        # - If no grace (0 or None): final = marks
        assessments_to_update = []
        for a in all_assessments:
            if a.ind_marks_obtained is not None:
                grace = a.ind_grace_obtained or 0
                expected_final = a.ind_marks_obtained + grace
                if a.ind_final_marks_obtained != expected_final:
                    a.ind_final_marks_obtained = expected_final
                    assessments_to_update.append(a)
        
        if assessments_to_update and not dry_run:
            StudentCourseAssessment.objects.bulk_update(
                assessments_to_update, ['ind_final_marks_obtained'], batch_size=100
            )
        
        # 2. Combined Level (Theory+Practical Aggregation)
        self._process_combined_level(student, assessments_qs, all_assessments, dry_run)
        
        # 3. Course Level (Final Grade & Credits)
        self._process_course_level(student, assessments_qs, all_assessments, dry_run)
        
        # 4. Semester Level (SGPA & Result Status)
        self._process_semester_level(student, assessments_qs, all_assessments, dry_run)

    ################################################################################
    # #### Combined Level ####
    ################################################################################

    def _process_combined_level(self, student, assessments_qs, all_assessments_list, dry_run):
        """
        Aggregates components (CIA + ESE) for 'comb_' fields.
        Separates logic for Theory vs Practical components.
        """
        paper_codes = set(a.paper_code for a in all_assessments_list if a.paper_code)
        
        for paper_code in paper_codes:
            paper_assessments_list = [a for a in all_assessments_list if a.paper_code == paper_code]
            
            theory_list = [a for a in paper_assessments_list if self._is_theory(a.label)]
            practical_list = [a for a in paper_assessments_list if self._is_practical(a.label)]
            
            course_obj = self.course_map.get(paper_code)
            if not course_obj:
                 import re
                 numeric_part = re.search(r'\d+$', paper_code)
                 if numeric_part:
                     course_obj = self.course_map.get(numeric_part.group())
            
            course_max_credit = course_obj.max_credit if course_obj else None
            has_both = len(theory_list) > 0 and len(practical_list) > 0
            
            if not dry_run:
                # Update Theory Rows
                if theory_list:
                    self._update_combined_stats_db(assessments_qs, paper_code, 'Theory', theory_list, 
                                                  course_max_credit=course_max_credit, 
                                                  has_both_components=has_both)
                
                # Update Practical Rows
                if practical_list:
                    self._update_combined_stats_db(assessments_qs, paper_code, 'Practical', practical_list,
                                                  course_max_credit=course_max_credit,
                                                  has_both_components=has_both)

    def _is_theory(self, label):
        l = (label or '').lower()
        return 'theory' in l or label in ['MID_TERM', 'END_TERM']

    def _is_practical(self, label):
        l = (label or '').lower()
        return 'practical' in l or label in ['LAB', 'END2_TERM']

    def _update_combined_stats_db(self, base_qs, paper_code, type_str, component_list, course_max_credit=None, has_both_components=False):
        """Helper to calculate and update combined stats in DB"""
        from decimal import Decimal
        from ug.services.result_calculator import UGResultCalculator
        
        total_max = sum(a.ind_max_marks or 0 for a in component_list)
        total_obtained = sum(a.ind_final_marks_obtained or 0 for a in component_list)
        total_pass_marks = sum(a.ind_pass_marks or 0 for a in component_list)
        total_grace = sum(a.ind_grace_obtained or 0 for a in component_list)
        
        if type_str == 'Theory':
            filters = Q(label__icontains='Theory') | Q(label='MID_TERM') | Q(label='END_TERM')
        else:
            filters = Q(label__icontains='Practical') | Q(label='LAB') | Q(label='END2_TERM')
        
        base_qs.filter(paper_code=paper_code).filter(filters).update(
            comb_max_marks=total_max,
            comb_marks_obtained=total_obtained,
            comb_pass_marks=total_pass_marks,
            comb_grace_obtained=total_grace,
        )
        
        if not component_list:
            return
        
        component_max_credit = 0
        if course_max_credit and has_both_components:
            if course_max_credit == 6:
                component_max_credit = 4 if type_str == 'Theory' else 2
            elif course_max_credit == 5:
                component_max_credit = 3 if type_str == 'Theory' else 2
            elif course_max_credit == 4:
                component_max_credit = 3 if type_str == 'Theory' else 1
            elif course_max_credit == 3:
                component_max_credit = 2 if type_str == 'Theory' else 1
            else:
                component_max_credit = int(course_max_credit * (2/3) if type_str == 'Theory' else course_max_credit * (1/3))
        elif course_max_credit:
            component_max_credit = course_max_credit
        else:
            for comp in component_list:
                if comp.comb_max_credits and Decimal(comp.comb_max_credits) > 0:
                    component_max_credit = comp.comb_max_credits
                    break
        
        component_grade, component_numeric_grade = UGResultCalculator.calculate_grade(
            total_obtained, 
            total_max
        )
        
        component_passed = total_obtained >= total_pass_marks if total_pass_marks > 0 else (total_obtained > 0)
        component_credit_obtained = Decimal(component_max_credit) if component_passed else Decimal(0)
        component_grade_point = Decimal(component_numeric_grade) * Decimal(component_max_credit)
        
        base_qs.filter(paper_code=paper_code).filter(filters).update(
            comb_max_credits=component_max_credit,
            comb_numeric_grade=component_numeric_grade,
            comb_letter_grade=component_grade,
            comb_credit_obtained=component_credit_obtained,
            comb_grade_point=component_grade_point,
        )

    ################################################################################
    # #### Course Level ####
    ################################################################################

    def _process_course_level(self, student, assessments_qs, all_assessments_list, dry_run):
        """Calculates final Course results: Grade, Credit, Status."""
        paper_codes = set(a.paper_code for a in all_assessments_list if a.paper_code)
        
        for paper_code in paper_codes:
            course_obj = self.course_map.get(paper_code)
            if not course_obj:
                import re
                numeric_part = re.search(r'\d+$', paper_code)
                if numeric_part:
                     course_obj = self.course_map.get(numeric_part.group())

            result_data = UGResultCalculator.calculate_course_result(
                student.id, 
                self.semester, 
                paper_code,
                assessments=all_assessments_list,
                course_structure=course_obj
            )
            
            if not dry_run:
                base_qs_filtered = assessments_qs.filter(paper_code=paper_code)
                paper_assessments_list = [a for a in all_assessments_list if a.paper_code == paper_code]
                
                total_pass_marks = sum(a.ind_pass_marks or 0 for a in paper_assessments_list)
                total_grace = sum(a.ind_grace_obtained or 0 for a in paper_assessments_list)
                
                final_grade_point = result_data['grade_point']
                weighted_grade_point = Decimal(final_grade_point) * Decimal(result_data['max_credit'])
                
                update_payload = {
                    'course_final_marks_obtained': result_data['total_marks'],
                    'course_marks_obtained': result_data['total_marks'],
                    'course_credit_obtained': result_data['credits_earned'],
                    'course_grade_point': weighted_grade_point,
                    'course_max_credits': result_data['max_credit'],
                    'course_max_marks': result_data['total_max_marks'],
                    'course_pass_marks': total_pass_marks,
                    'course_grace_obtained': total_grace if total_grace > 0 else 0,
                    'comb_final_marks_obtained': result_data['total_marks'],
                }
                base_qs_filtered.update(**update_payload)
                
                for a in paper_assessments_list:
                    a.course_final_marks_obtained = result_data['total_marks']
                    a.course_marks_obtained = result_data['total_marks']
                    a.course_credit_obtained = result_data['credits_earned']
                    a.course_grade_point = weighted_grade_point
                    a.course_max_credits = result_data['max_credit']
                    a.course_max_marks = result_data['total_max_marks']
                    a.course_pass_marks = total_pass_marks
                    a.comb_final_marks_obtained = result_data['total_marks']

    ################################################################################
    # #### Semester Level ####
    ################################################################################

    def _process_semester_level(self, student, assessments_qs, all_assessments_list, dry_run):
        """Calculates SGPA, Semester Result, and Promotion Eligibility."""
        fresh_assessments = list(StudentCourseAssessment.objects.filter(
            student=student,
            semester=self.semester,
            session=self.session,
            exam_type=self.exam_type
        ))
        
        sgpa = UGResultCalculator.calculate_sgpa(
            student.id, 
            self.semester,
            assessments=fresh_assessments,
            course_map=self.course_map
        ) or Decimal('0.00')
        
        is_rejoined = False
        if student and student.batch:
            is_rejoined = not StudentCourseAssessment.objects.filter(
                student=student,
                semester=self.semester,
                batch__name=student.batch.name,
                exam_type='REGULAR'
            ).exists()

        if self.exam_type == 'BACK':
            if is_rejoined:
                sem_result_status = UGResultCalculator.determine_semester_result(
                    student.id, self.semester, assessments=fresh_assessments
                )
            else:
                sem_result_status = UGResultCalculator.determine_back_result(
                    student.id, self.semester, back_assessments=fresh_assessments
                )
        else:
            sem_result_status = UGResultCalculator.determine_semester_result(
                student.id, self.semester, assessments=fresh_assessments
            )

        # Determine Result Status (Session vs Cumulative)
        if self.exam_type == 'BACK':
             # Calculate best possible outcome across ALL attempts
             overall_data = UGResultCalculator.recalculate_overall_semester_result(
                student.id, self.semester
            )
             result_for_exam_result = overall_data['result'] # Cumulative (Qualified/etc)
             sgpa_for_exam_result = overall_data['sgpa']
             max_credit_for_exam_result = overall_data['semester_max_credit']
             earned_credit_for_exam_result = overall_data['semester_credit_earned']

             # For the assessment record of the current session, we show the improved standing
             assessment_sem_result = result_for_db = overall_data['result'] 
             assessment_sgpa = overall_data['sgpa']
        else:
             result_for_exam_result = assessment_sem_result = sem_result_status
             sgpa_for_exam_result = assessment_sgpa = sgpa
             max_credit_for_exam_result = sum(a.comb_max_credits or 0 for a in fresh_assessments if a.label.startswith('ESE'))
             earned_credit_for_exam_result = sum(a.comb_credit_obtained or 0 for a in fresh_assessments if a.label.startswith('ESE'))

        # Update Stats for this session result
        if self.exam_type == 'BACK':
            if result_for_exam_result == 'QUALIFIED': self.stats['qualified'] += 1
            elif result_for_exam_result == 'PARTLY_QUALIFIED': self.stats['partly_qualified'] += 1
            else: self.stats['disqualified'] += 1
            self.stats['overall_updated'] += 1
        else:
            if result_for_exam_result == 'PASS': self.stats['passed'] += 1
            elif result_for_exam_result == 'PROMOTED': self.stats['promoted'] += 1
            else: self.stats['failed'] += 1

        if not dry_run:

            # 2. Save Exam Result (Always update/create exactly ONE entry per semester for the student)
            # Use filter on student and semester only to maintain a single record
            exam_result_defaults = {
                'session': self.session,
                'semester_result': result_for_exam_result,
                'sgpa': sgpa_for_exam_result if result_for_exam_result in ['PASS', 'QUALIFIED'] else None,
                'semester_max_credit': max_credit_for_exam_result,
                'semester_credit_earned': earned_credit_for_exam_result,
                'ese_pass': True if result_for_exam_result in ['PASS', 'QUALIFIED', 'PROMOTED', 'PARTLY_QUALIFIED'] else False,
            }
            
            exam_result_obj = UGExamResult.objects.filter(
                student=student, semester=self.semester
            ).first()
            
            if exam_result_obj:
                for attr, value in exam_result_defaults.items():
                    setattr(exam_result_obj, attr, value)
                exam_result_obj.save()
            else:
                exam_result_obj = UGExamResult.objects.create(
                    student=student, semester=self.semester, **exam_result_defaults
                )

            # 3. Update CURRENT session assessments ONLY (Leave previous sessions untouched as per USER)
            self._update_assessment_semester_fields_db(student, assessment_sgpa, assessment_sem_result)

            # 4. Promotion Check
            check_status = result_for_exam_result
            is_eligible, eligibility_reason = UGResultCalculator.check_promotion_eligibility(
                student.id, self.semester, current_result_status=check_status
            )
            
            # Update the status on the singleton record
            UGExamResult.objects.filter(id=exam_result_obj.id).update(
                next_sem_status='ELIGIBLE' if is_eligible else 'NOT_ELIGIBLE'
            )
                
            if is_eligible:
                self._create_next_sem_registration(student)

    def _update_assessment_semester_fields_db(self, student, sgpa, result_status):
        """Update semester fields on StudentCourseAssessment (Strictly for current session entries)"""
        # Fetch credits from the latest state of the singleton result
        exam_result = UGExamResult.objects.filter(
            student=student, semester=self.semester
        ).first()
        
        sem_max = exam_result.semester_max_credit if exam_result else 0
        sem_earned = exam_result.semester_credit_earned if exam_result else 0
        
        # Determine SGPA to show (ONLY for PASS/QUALIFIED status as per user requirement)
        final_sgpa = sgpa if result_status in ['PASS', 'QUALIFIED'] else None
        
        StudentCourseAssessment.objects.filter(
            student=student, 
            semester=self.semester, 
            session=self.session, 
            exam_type=self.exam_type
        ).update(
            sgpa=final_sgpa,
            sem_result=result_status,
            sem_max_credit=sem_max,
            sem_credit_obtained=sem_earned
        )

    def _create_next_sem_registration(self, student):
        """Create SemesterRegistration for next semester"""
        next_sem = self._get_next_semester(self.semester)
        if next_sem:
            existing_qs = SemesterRegistration.objects.filter(
                student=student,
                sem=next_sem
            )
            if not existing_qs.exists():
                SemesterRegistration.objects.create(
                    student=student, sem=next_sem, session=self.session, batch=student.batch,
                    status='PENDING', is_open=True, exam_eligible=False,
                    remarks=f'Promoted from {self.semester}'
                )
                self.stats['registrations_created'] += 1

    def _get_next_semester(self, current_sem_str: str) -> Optional[int]:
        mapping = {'1ST': 2, '2ND': 3, '3RD': 4, '4TH': 5, '5TH': 6, '6TH': 7, '7TH': 8}
        return mapping.get(current_sem_str)

    def _print_header(self):
        print("\n" + "="*100)
        print("[STEP 2] FINAL RESULT PROCESSING (POST-ESE)")
        print("="*100)
        print(f"Batch:     {self.batch}")
        print(f"Semester:  {self.semester}")
        print(f"Session:   {self.session}")
        print(f"Exam Type: {self.exam_type}")
        print("="*100)

    def _print_summary(self):
        print("\n" + "="*100)
        print("[SUMMARY] FINAL PROCESSING COMPLETE")
        print("="*100)
        print(f"Total Students:        {self.stats['total_students']:,}")
        print(f"Processed:             {self.stats['processed']:,}")
        if self.exam_type == 'REGULAR':
            print(f"[+] PASSED:              {self.stats['passed']:,}")
            print(f"[!] PROMOTED:            {self.stats['promoted']:,}")
            print(f"[-] FAILED:              {self.stats['failed']:,}")
            print(f"[*] Registrations Created: {self.stats['registrations_created']:,}")
        else:
            print(f"[+] QUALIFIED:           {self.stats['qualified']:,}")
            print(f"[!] PARTLY QUALIFIED:    {self.stats['partly_qualified']:,}")
            print(f"[-] DISQUALIFIED:        {self.stats['disqualified']:,}")
            print(f"[*] Overall Results Updated: {self.stats['overall_updated']:,}")
        print(f"[SKIP] Missing Papers:       {self.stats['missing_papers']:,}")
        print("="*100 + "\n")

def run_final_processing(batch: str, semester: str, session: str, registration_no: Optional[str] = None, exam_type: str = 'REGULAR', dry_run: bool = False, resume: bool = False) -> Dict:
    service = FinalResultProcessingService(batch, semester, session, registration_no, exam_type)
    return service.process(dry_run=dry_run, resume=resume)
