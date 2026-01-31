"""
Step 2: Final Result Processing Service (Post-ESE)

Processes final semester results after ESE marks entry:
1. Calculates combined marks (CIA + ESE) and grades for each course
2. Updates StudentCourseAssessment with final course-level data
3. Calculates SGPA and Semester Result (PASS/FAIL/PROMOTED)
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
    
    def __init__(self, batch: str, semester: str, session: str, registration_no: Optional[str] = None):
        self.batch = batch
        self.semester = semester
        self.session = session
        self.registration_no = registration_no
        # Add internal resume tracking
        self.resume = False 
        self.stats = {
            'total_students': 0,
            'processed': 0,
            'passed': 0,
            'promoted': 0,
            'failed': 0,
            'registrations_created': 0,
        }
        
        # Optimization: Cache CourseStructure
        self.course_map = {}
        self._load_course_map()

    def _load_course_map(self):
        """Load CourseStructure for batch/semester into memory to avoid N+1 queries"""
        # ... existing implementation

    def process(self, dry_run: bool = False, resume: bool = False) -> Dict:
        """Main processing method"""
        self.resume = resume
        self._print_header()
        
        if self.registration_no:
            # Process single student
            students = UGStudentProfile.objects.filter(
                batch=self.batch, 
                registration_no=self.registration_no
            )
            print(f"\n🔍 Processing SINGLE student: {self.registration_no}")
        else:
            # Process entire batch
            # Optimization: 
            active_ids = StudentCourseAssessment.objects.filter(
                semester=self.semester
            ).values_list('student_id', flat=True).distinct()
            
            students = UGStudentProfile.objects.filter(
                id__in=active_ids,
                batch=self.batch
            ).order_by('registration_no')
            
            # --- RESUME LOGIC ---
            if self.resume:
                print("⏭️  RESUMING: Skipping already processed students...")
                # Filter out students who already have a FINAL result (PASS/FAIL/PROMOTED)
                # PENDING result means Step 1 ran but Step 2 didn't finish.
                processed_ids = UGExamResult.objects.filter(
                    semester=self.semester,
                    session=self.session,
                    semester_result__in=['PASS', 'FAIL', 'PROMOTED']
                ).values_list('student_id', flat=True)
                
                initial_count = students.count()
                students = students.exclude(id__in=processed_ids)
                remaining_count = students.count()
                print(f"   Skipped: {initial_count - remaining_count:,} students")
                print(f"   Remaining: {remaining_count:,} students")

        self.stats['total_students'] = students.count()
        print(f"\n📊 Found {self.stats['total_students']:,} students to process")
        print(f"{'='*100}\n")
        
        # Use simple iteration with atomic blocks for chunks if batch is large
        # We handle transactions inside _process_all_students with chunks to avoid lock timeouts
        if not dry_run:
            self._process_all_students(students, dry_run=False)
        else:
            print("🔍 DRY RUN MODE - No database changes will be made\n")
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
                print(f"  ⏳ Processed {idx:,}/{self.stats['total_students']:,} students...")

        # Process remaining
        if current_chunk:
            self._process_student_chunk(current_chunk, dry_run)
            print(f"  ⏳ Processed {idx:,}/{self.stats['total_students']:,} students...")

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
        
        # Optimization: Fetch ALL assessments for this student & semester ONCE
        assessments_qs = StudentCourseAssessment.objects.filter(
            student=student, semester=self.semester
        )
        all_assessments = list(assessments_qs)
        
        if not all_assessments:
            return

        # 1. Individual Level (Already done via Save/Step 1)
        # self._process_individual_level(student) 
        
        # 2. Combined Level (Theory+Practical Aggregation)
        # Pass the list for processing logic, but we still need QuerySets for UPDATE
        # Because we need .update().
        # So we pass the QuerySet 'assessments_qs' or refetch where needed?
        # Ideally, we calculate in memory, then update.
        # But for 'update()', we need a queryset.
        # Given 'update()' is fast, we can use the main queryset filtered by paper_code.
        self._process_combined_level(student, assessments_qs, all_assessments, dry_run)
        
        # 3. Course Level (Final Grade & Credits)
        self._process_course_level(student, assessments_qs, all_assessments, dry_run)
        
        # 4. Semester Level (SGPA & Result Status)
        self._process_semester_level(student, assessments_qs, all_assessments, dry_run)

    ################################################################################
    # #### Individual Level ####
    ################################################################################
    
    def _process_individual_level(self, student):
        """
        Validates individual marks and pass status.
        Mostly handled by Model.save() or Step 1.
        Placeholder.
        """
        pass

    ################################################################################
    # #### Combined Level ####
    ################################################################################

    def _process_combined_level(self, student, assessments_qs, all_assessments_list, dry_run):
        """
        Aggregates components (CIA + ESE) for 'comb_' fields.
        Separates logic for Theory vs Practical components.
        """
        # Use in-memory list to find unique paper codes
        paper_codes = set(a.paper_code for a in all_assessments_list if a.paper_code)
        
        for paper_code in paper_codes:
            # Filter in-memory for logic (if we had complex python logic)
            # But here we need to write to DB.
            # Using queryset update is efficient.
            # assessments_qs.filter(paper_code=paper_code) uses the existing connection?
            # It adds a WHERE clause.
            
            # Group into Theory and Practical buckets (In-Memory for check, QuerySet for update)
            paper_assessments_list = [a for a in all_assessments_list if a.paper_code == paper_code]
            
            # Logic: Calculate sums
            theory_list = [a for a in paper_assessments_list if self._is_theory(a.label)]
            practical_list = [a for a in paper_assessments_list if self._is_practical(a.label)]
            
            # Get course_max_credit from course structure
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
        """
        Helper to calculate and update combined stats in DB
        
        USER REQUIREMENT (2026-01-31):
        Works for BOTH legacy data (json_data) AND future data (direct entry):
        - If fields exist (comb_max_credits, comb_credit_obtained, comb_grade_point) → PRESERVE
        - If fields missing/zero → CALCULATE from course structure
        - Always update marks (derived from ind_ fields)
        
        This makes the script batch/semester agnostic.
        """
        from decimal import Decimal
        from ug.services.result_calculator import UGResultCalculator
        
        total_max = sum(a.ind_max_marks or 0 for a in component_list)
        total_obtained = sum(a.ind_marks_obtained or 0 for a in component_list)
        total_pass_marks = sum(a.ind_pass_marks or 0 for a in component_list)
        
        # Targeted filter
        if type_str == 'Theory':
            filters = Q(label__icontains='Theory') | Q(label='MID_TERM') | Q(label='END_TERM')
        else:
            filters = Q(label__icontains='Practical') | Q(label='LAB') | Q(label='END2_TERM')
        
        # STEP 1: Always update marks (derived from ind_ fields)
        base_qs.filter(paper_code=paper_code).filter(filters).update(
            comb_max_marks=total_max,
            comb_marks_obtained=total_obtained,
            comb_pass_marks=total_pass_marks,
        )
        
        # STEP 2: Conditionally update credits and grade points
        # Check if values already exist in ANY component (not just the first)
        if not component_list:
            return
        
        # Check each component to see if values are already populated
        has_any_existing_values = False
        for comp in component_list:
            comp.refresh_from_db()
            if comp.comb_max_credits and Decimal(comp.comb_max_credits) > 0:
                if comp.comb_grade_point and Decimal(comp.comb_grade_point) > 0:
                    # At least one component has valid values
                    has_any_existing_values = True
                    break
        
        # If ANY component has values, DON'T overwrite (preserve from json_data or direct entry)
        if has_any_existing_values:
            # Values already populated in at least one component, skip calculation
            return
        
        # STEP 3: Calculate values (for future data without json_data)
        # Calculate component-specific max_credit
        component_max_credit = 0
        if course_max_credit and has_both_components:
            # Split credits based on component type
            if course_max_credit == 6:
                component_max_credit = 4 if type_str == 'Theory' else 2
            elif course_max_credit == 5:
                component_max_credit = 3 if type_str == 'Theory' else 2
            elif course_max_credit == 3:
                component_max_credit = 2 if type_str == 'Theory' else 1
            else:
                # Default split: roughly 2/3 for theory, 1/3 for practical
                component_max_credit = int(course_max_credit * (2/3) if type_str == 'Theory' else course_max_credit * (1/3))
        elif course_max_credit:
            # Only one component, use full credit
            component_max_credit = course_max_credit
        
        # Calculate component grade
        component_grade, component_numeric_grade = UGResultCalculator.calculate_grade(
            total_obtained, 
            total_max
        )
        
        # Check if component passed
        component_passed = total_obtained >= total_pass_marks if total_pass_marks > 0 else (total_obtained > 0)
        
        # Calculate credits earned
        component_credit_obtained = Decimal(component_max_credit) if component_passed else Decimal(0)
        
        # Calculate grade point = NumGrade × ComponentCredit
        component_grade_point = Decimal(component_numeric_grade) * Decimal(component_max_credit)
        
        # Update calculated values
        base_qs.filter(paper_code=paper_code).filter(filters).update(
            comb_max_credits=component_max_credit,
            comb_numeric_grade=component_numeric_grade,
            comb_credit_obtained=component_credit_obtained,
            comb_grade_point=component_grade_point,
        )

    ################################################################################
    # #### Course Level ####
    ################################################################################

    def _process_course_level(self, student, assessments_qs, all_assessments_list, dry_run):
        """
        Calculates final Course results: Grade, Credit, Status.
        Updates 'course_' fields.
        """
        paper_codes = set(a.paper_code for a in all_assessments_list if a.paper_code)
        
        for paper_code in paper_codes:
            # OPTIMIZATION: Use Cached Course Structure and In-Memory Assessments
            # Find cached course
            course_obj = self.course_map.get(paper_code)
            if not course_obj:
                # Fallback: Try numeric part match
                import re
                numeric_part = re.search(r'\d+$', paper_code)
                if numeric_part:
                     course_obj = self.course_map.get(numeric_part.group())

            # Calculate Result (Pure Memory Operation now!)
            result_data = UGResultCalculator.calculate_course_result(
                student.id, 
                self.semester, 
                paper_code,
                assessments=all_assessments_list, # Pass full list, it filters
                course_structure=course_obj
            )
            
            if not dry_run:
                # Update 'course_' fields on ALL rows for this paper
                base_qs_filtered = assessments_qs.filter(paper_code=paper_code)
                
                # Check if we should preserve existing grades (Legacy Trust)
                # We assume if comb_numeric_grade is set, it's correct (from migration)
                # But we ALWAYS update marks/credits/max_marks if they are calculated
                
                paper_assessments_list = [a for a in all_assessments_list if a.paper_code == paper_code]
                
                # Fetch first to check existing
                existing_rec = paper_assessments_list[0] if paper_assessments_list else None
                existing_grade = existing_rec.comb_numeric_grade if existing_rec else None
                 
                update_payload = {
                    'course_final_marks_obtained': result_data['total_marks'],
                    'course_credit_obtained': result_data['credits_earned'],
                    # 'course_grade_point': result_data['grade_point'], # Conditional
                    'course_max_credits': result_data['max_credit'],
                    'course_max_marks': result_data['total_max_marks'],
                    # 'comb_numeric_grade': result_data['grade_point'], # Conditional
                    # 'comb_credit_obtained': result_data['credits_earned'], # Set by combined-level!
                    # 'comb_max_credits': result_data['max_credit'], # Set by combined-level with split!
                    'comb_final_marks_obtained': result_data['total_marks']
                }
                
                # CONDITIONAL GRADE UPDATE (LEGACY TRUST)
                # If existing grade > 0, trust it. Else use calculated.
                final_grade_point = result_data['grade_point']
                
                if existing_grade is not None and Decimal(existing_grade) > 0:
                    # Preserve existing (Legacy Trust)
                    final_grade_point = existing_grade
                else:
                    # Use calculated
                    update_payload['comb_numeric_grade'] = final_grade_point

                # USER REQUIREMENT (2026-01-30):
                # DO NOT UPDATE comb_grade_point for legacy data!
                # Legacy has individual subject_gp per assessment row (CIA-Theory, ESE-Theory, etc.)
                # My bulk update would overwrite these with a single course-level value
                # SGPA = Sum(ALL individual subject_gp rows) / earned_credits
                
                # For in-memory SGPA calculation, we need the weighted point
                # But we use existing values from DB, not recalculated
                weighted_point_for_memory = Decimal(final_grade_point) * Decimal(result_data['credits_earned'])

                base_qs_filtered.update(**update_payload)
                
                # CRITICAL: Update In-Memory Objects with FINAL values
                # For comb_grade_point: DO NOT update DB, but update memory for current calculation
                paper_assessments_list = [a for a in all_assessments_list if a.paper_code == paper_code]
                for a in paper_assessments_list:
                    a.course_final_marks_obtained = result_data['total_marks']
                    a.course_credit_obtained = result_data['credits_earned']
                    
                    a.comb_numeric_grade = final_grade_point # 0-10
                    # Keep existing comb_grade_point from DB (don't overwrite)
                    # a.comb_grade_point stays as-is from migration
                    
                    a.course_max_credits = result_data['max_credit']
                    a.course_max_marks = result_data['total_max_marks']
                    
                    # Also update 'comb_' fields in memory
                    a.comb_numeric_grade = final_grade_point # Use determined final
                    a.comb_credit_obtained = result_data['credits_earned']
                    a.comb_max_credits = result_data['max_credit']
                    a.comb_final_marks_obtained = result_data['total_marks']

    ################################################################################
    # #### Semester Level ####
    ################################################################################

    def _process_semester_level(self, student, assessments_qs, all_assessments_list, dry_run):
        """
        Calculates SGPA, Semester Result, and Promotion Eligibility.
        Updates UGExamResult and creates SemesterRegistration.
        """
        # OPTIMIZATION: Pass cached data
        # 1. Calculate SGPA (Pure Memory)
        sgpa = UGResultCalculator.calculate_sgpa(
            student.id, 
            self.semester,
            assessments=all_assessments_list,
            course_map=self.course_map
        ) or Decimal('0.00')
        
        # 2. Determine Result Status (Pure Memory)
        sem_result_status = UGResultCalculator.determine_semester_result(
            student.id, 
            self.semester,
            assessments=all_assessments_list
        )
        
        # 3. Check Promotion Eligibility (Still needs DB for history, but specific query)
        is_eligible, eligibility_reason = UGResultCalculator.check_promotion_eligibility(
            student.id, self.semester, current_result_status=sem_result_status
        )
        
        # Update Stats
        if sem_result_status == 'PASS':
            self.stats['passed'] += 1
        elif sem_result_status == 'PROMOTED':
            self.stats['promoted'] += 1
        else:
            self.stats['failed'] += 1

        if not dry_run:
            # Check if we should proceed (must have CIA data or existing result)
            has_cia = any('CIA' in (a.label or '') for a in all_assessments_list)
            
            existing_result_exists = UGExamResult.objects.filter(
                student=student, semester=self.semester, session=self.session
            ).exists()
            
            if not has_cia and not existing_result_exists:
                print(f"      ⚠️ SKIPPING: No CIA data and no existing result for {student.registration_no}")
                return

            # Update Exam Result
            self._update_exam_result_db(student, sgpa, sem_result_status, is_eligible, eligibility_reason, all_assessments_list)
            
            # Update Semester Fields on Assessments
            self._update_assessment_semester_fields_db(student, sgpa, sem_result_status)
            
            # Create Next Sem Registration
            if is_eligible:
                self._create_next_sem_registration(student)

    def _update_exam_result_db(self, student, sgpa, status, is_eligible, reason, all_assessments_list):
        """Update UGExamResult table"""

        # Calculate semester totals FROM MEMORY LIST
        paper_codes = set(a.paper_code for a in all_assessments_list if a.paper_code)
        sem_max_credits = Decimal(0)
        sem_credits_earned = Decimal(0)
        
        for paper_code in paper_codes:
            # Find one assessment for this paper to get course stats
            # Stats might not be in the objects in 'all_assessments_list' because
            # we just updated the DB using .update() but didn't refresh the objects.
            # Critical Point: .update() does NOT update in-memory objects.
            # So 'all_assessments_list' still has old values for 'course_max_credits' etc.
            # BUT, we just calculated them in `_process_course_level` memory result.
            # We can re-calculate or just fetch? Re-fetching defeats optimization.
            # Better: We can rely on `UGResultCalculator` logic again?
            
            # Option 2: Since we know the logic (Course Map + Passed Flag), we can Compute it.
            # Retrieve cached course
            course_obj = self.course_map.get(paper_code)
            if not course_obj:
               import re
               numeric_part = re.search(r'\d+$', paper_code)
               if numeric_part:
                    course_obj = self.course_map.get(numeric_part.group())
            
            # Re-calculate result in memory (Fast)
            result_data = UGResultCalculator.calculate_course_result(
                student.id, 
                self.semester, 
                paper_code,
                assessments=all_assessments_list, 
                course_structure=course_obj
            )
            
            sem_max_credits += Decimal(result_data['max_credit'] or 0)
            sem_credits_earned += Decimal(result_data['credits_earned'] or 0)

        # OFFICIAL RULE (ug_passing_rules.txt, lines 104-106):
        # "A candidate SHALL NOT be awarded or calculated ANY SGPA if he/she 
        # FAILS to earn the TOTAL prescribed credits in that particular semester."
        # 
        # Therefore:
        # - PASS → Calculate SGPA
        # - PROMOTED → SGPA = None (didn't earn total credits)
        # - FAILED → SGPA = None
        final_sgpa = sgpa if status == 'PASS' else None
        
        UGExamResult.objects.update_or_create(
            student=student,
            semester=self.semester,
            session=self.session,
            defaults={
                'sgpa': final_sgpa,
                'semester_result': status,
                'semester_credit_earned': sem_credits_earned,
                'semester_max_credit': sem_max_credits,
                'ese_pass': True if status == 'PASS' else False,
                'next_sem_status': 'ELIGIBLE' if is_eligible else 'NOT_ELIGIBLE'
            }
        )

    def _update_assessment_semester_fields_db(self, student, sgpa, result_status):
        """Update semester fields on StudentCourseAssessment"""
        # Fetch the just-updated Exam Result to get totals? 
        # Or calculate again? Database read is safer for consistency.
        # It's one read.
        exam_result = UGExamResult.objects.filter(
            student=student, semester=self.semester, session=self.session
        ).first()
        
        sem_max = exam_result.semester_max_credit if exam_result else 0
        sem_earned = exam_result.semester_credit_earned if exam_result else 0
        
        # Apply official rule: SGPA only for PASS students
        final_sgpa = sgpa if result_status == 'PASS' else None
        
        # Batch Update
        StudentCourseAssessment.objects.filter(
            student=student, semester=self.semester
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
            SemesterRegistration.objects.get_or_create(
                student=student,
                sem=next_sem,
                session=self.session,
                defaults={
                    'status': 'PENDING',
                    'is_open': True,
                    'exam_eligible': False,
                    'remarks': f'Promoted from {self.semester}'
                }
            )
            self.stats['registrations_created'] += 1

    ################################################################################
    # UTILITIES
    ################################################################################

    def _get_next_semester(self, current_sem_str: str) -> Optional[int]:
        mapping = {
            '1ST': 2, '2ND': 3, '3RD': 4, '4TH': 5, 
            '5TH': 6, '6TH': 7, '7TH': 8
        }
        return mapping.get(current_sem_str)

    def _print_header(self):
        print("\n" + "="*100)
        print("📊 STEP 2: FINAL RESULT PROCESSING (POST-ESE)")
        print("="*100)
        print(f"Batch:    {self.batch}")
        print(f"Semester: {self.semester}")
        print(f"Session:  {self.session}")
        print("="*100)

    def _print_summary(self):
        print("\n" + "="*100)
        print("📊 FINAL PROCESSING COMPLETE - SUMMARY")
        print("="*100)
        print(f"Total Students:        {self.stats['total_students']:,}")
        print(f"Processed:             {self.stats['processed']:,}")
        print(f"✅ PASSED:              {self.stats['passed']:,}")
        print(f"⚠️ PROMOTED:            {self.stats['promoted']:,}")
        print(f"❌ FAILED:              {self.stats['failed']:,}")
        print(f"📋 Next Sem Registers:  {self.stats['registrations_created']:,}")
        print("="*100)

def run_final_processing(batch: str, semester: str, session: str, registration_no: Optional[str] = None, dry_run: bool = False, resume: bool = False) -> Dict:
    service = FinalResultProcessingService(batch, semester, session, registration_no)
    return service.process(dry_run=dry_run, resume=resume)
