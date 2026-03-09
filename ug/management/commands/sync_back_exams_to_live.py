import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync StudentCourseAssessment and ExamRegistration for BACK exams from default DB to live DB'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--reg-nos',
            nargs='+',
            type=str,
            help='List of registration numbers to sync'
        )
        group.add_argument(
            '--file',
            type=str,
            help='Path to a text file with one registration number per line'
        )
        parser.add_argument(
            '--session',
            type=str,
            default='2025-26',
            help='Target session (default: 2025-26)'
        )
        parser.add_argument(
            '--semester',
            type=str,
            default='1ST',
            help='Target semester string (e.g. 1ST)'
        )
        parser.add_argument(
            '--sem-int',
            type=int,
            default=1,
            help='Target semester integer for ExamRegistration (e.g. 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Simulate the sync without writing to live DB'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_session = options['session']
        target_sem_str = options['semester']
        target_sem_int = options['sem_int']

        # Collect registration numbers
        if options['reg_nos']:
            reg_nos = [r.strip() for r in options['reg_nos'] if r.strip()]
        else:
            try:
                with open(options['file'], 'r') as f:
                    reg_nos = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                raise CommandError(f"File not found: {options['file']}")

        if not reg_nos:
            raise CommandError("No registration numbers provided.")

        self.stdout.write(f"📋 Found {len(reg_nos)} registration number(s) to sync")
        self.stdout.write(f"⚙️ Target Session: {target_session} | Semester: {target_sem_str} | Exam Type: BACK")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️ DRY RUN — no changes will be written to live DB"))

        # Import models
        from ug.models import UGStudentProfile, StudentCourseAssessment, ExamRegistration, UGDepartment, UGBatch

        stats = {'students_processed': 0, 'assessments_created': 0, 'registrations_created': 0, 'errors': 0}

        for reg_no in reg_nos:
            self.stdout.write(f"\n── Processing Student: {reg_no}")

            # 1. Check if student exists in live DB
            try:
                live_profile = UGStudentProfile.objects.using('live').get(registration_no=reg_no)
            except UGStudentProfile.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"  ✗ Student NOT FOUND in live DB for: {reg_no}. Run sync_students_to_live first!"))
                stats['errors'] += 1
                continue
                
            stats['students_processed'] += 1
                
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"  ✓ [DRY RUN] Would process student {reg_no}"))
                continue

            try:
                with transaction.atomic(using='live'):
                    # 2. Handle ExamRegistration
                    # Check if any ExamRegistration already exists for this session and sem
                    live_exam_reg_exists = ExamRegistration.objects.using('live').filter(
                        student=live_profile,
                        session=target_session,
                        sem=target_sem_int
                    ).exists()

                    if live_exam_reg_exists:
                        self.stdout.write(f"  ⏭ ExamRegistration already exists for {reg_no} in session {target_session} — skipping.")
                    else:
                        # Fetch from local
                        local_exam_reg = ExamRegistration.objects.using('default').filter(
                            student__registration_no=reg_no,
                            session=target_session,
                            sem=target_sem_int
                        ).first()

                        if local_exam_reg:
                            ExamRegistration.objects.using('live').create(
                                student=live_profile,
                                start_date=local_exam_reg.start_date,
                                end_date=local_exam_reg.end_date,
                                is_open=local_exam_reg.is_open,
                                fees=600,
                                sem=local_exam_reg.sem,
                                status=local_exam_reg.status,
                                session=local_exam_reg.session,
                                exam_type='BACK',
                            )
                            self.stdout.write(self.style.SUCCESS(f"  ✓ Created ExamRegistration on live DB."))
                            stats['registrations_created'] += 1
                        else:
                            self.stdout.write(f"  ⚠ No local ExamRegistration found to sync for {reg_no}.")

                    # 3. Handle StudentCourseAssessment
                    local_assessments = StudentCourseAssessment.objects.using('default').filter(
                        student__registration_no=reg_no,
                        session=target_session,
                        semester=target_sem_str,
                        exam_type='BACK'
                    )
                    
                    if not local_assessments.exists():
                        self.stdout.write(f"  ⚠ No local BACK assessments found for session {target_session}.")
                        continue

                    created_assessments_count = 0
                    
                    for a in local_assessments:
                        # Ensure no duplicate for same paper, label, session, exam_type
                        a_exists = StudentCourseAssessment.objects.using('live').filter(
                            student=live_profile,
                            session=target_session,
                            semester=target_sem_str,
                            exam_type='BACK',
                            paper_code=a.paper_code,
                            label=a.label
                        ).exists()
                        
                        if a_exists:
                            continue
                            
                        # Resolve Foreign Keys on live
                        live_department = None
                        if a.department_id:
                            # using department code
                            local_dept = UGDepartment.objects.using('default').filter(id=a.department_id).first()
                            if local_dept:
                                live_department = UGDepartment.objects.using('live').filter(code=local_dept.code).first()
                                
                        live_batch = None
                        if a.batch_id:
                            local_batch = UGBatch.objects.using('default').filter(id=a.batch_id).first()
                            if local_batch:
                                live_batch = UGBatch.objects.using('live').filter(name=local_batch.name).first()

                        StudentCourseAssessment.objects.using('live').create(
                            course_name=a.course_name,
                            course_short_name=a.course_short_name,
                            student=live_profile,
                            course_type=a.course_type,
                            course_code=a.course_code,
                            paper_code=a.paper_code,
                            semester=a.semester,
                            label=a.label,
                            department=live_department,
                            degree=a.degree,
                            session=a.session,
                            batch=live_batch,
                            college_code=a.college_code,
                            exam_type=a.exam_type,
                            
                            ind_max_marks=a.ind_max_marks,
                            ind_pass_marks=a.ind_pass_marks,
                            ind_is_absent=a.ind_is_absent,
                            ind_marks_obtained=a.ind_marks_obtained,
                            ind_grace_obtained=a.ind_grace_obtained,
                            ind_final_marks_obtained=a.ind_final_marks_obtained,
                            ind_is_pass=a.ind_is_pass,
                            
                            comb_max_marks=a.comb_max_marks,
                            comb_max_credits=a.comb_max_credits,
                            comb_pass_marks=a.comb_pass_marks,
                            comb_marks_obtained=a.comb_marks_obtained,
                            comb_grace_obtained=a.comb_grace_obtained,
                            comb_final_marks_obtained=a.comb_final_marks_obtained,
                            comb_credit_obtained=a.comb_credit_obtained,
                            comb_numeric_grade=a.comb_numeric_grade,
                            comb_letter_grade=a.comb_letter_grade,
                            comb_grade_point=a.comb_grade_point,
                            
                            course_max_marks=a.course_max_marks,
                            course_max_credits=a.course_max_credits,
                            course_pass_marks=a.course_pass_marks,
                            course_marks_obtained=a.course_marks_obtained,
                            course_grace_obtained=a.course_grace_obtained,
                            course_final_marks_obtained=a.course_final_marks_obtained,
                            course_credit_obtained=a.course_credit_obtained,
                            course_grade_point=a.course_grade_point,
                            
                            sem_max_credit=a.sem_max_credit,
                            sem_credit_obtained=a.sem_credit_obtained,
                            sgpa=a.sgpa,
                            sem_result=a.sem_result,
                            next_sem_status=a.next_sem_status,
                            sem_grace_obtained=a.sem_grace_obtained,
                            
                            is_cia_filled=a.is_cia_filled,
                            cia_filled_on=a.cia_filled_on,
                        )
                        created_assessments_count += 1
                        stats['assessments_created'] += 1
                        
                    if created_assessments_count > 0:
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Created {created_assessments_count} new BACK assessments on live DB."))
                    else:
                        self.stdout.write(f"  ⏭ No new BACK assessments to create for session {target_session}.")
            
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  ✗ Failed for {reg_no}: {e}"))
                logger.exception(f"sync_back_exams_to_live error for {reg_no}")
                stats['errors'] += 1

        # Summary
        self.stdout.write("\n" + "═" * 50)
        self.stdout.write(f"✅ Students Processed:      {stats['students_processed']}")
        self.stdout.write(f"✅ Registrations Created:   {stats['registrations_created']}")
        self.stdout.write(f"✅ Assessments Created:     {stats['assessments_created']}")
        self.stdout.write(f"❌ Errors:                  {stats['errors']}")
        self.stdout.write("═" * 50)
