import time
from django.core.management.base import BaseCommand
from django.db import transaction
from pgoldresult.models import PGOldStudentProfile, PGOldResult
from staging.models import PGResultCurrent
from accounts.models import UserAccount
from colleges.models import College

class Command(BaseCommand):
    help = 'Load PG result data from staging into pgoldresult app models'

    def handle(self, *args, **options):
        self.stdout.write("Loading PG old result data...")

        # Cache colleges
        college_cache = {str(c.college_code): c for c in College.objects.all()}
        
        batch_size = 2000
        
        # Only include batch 2023-25 and earlier. Exclude 2024-26 and onwards.
        staging_qs = PGResultCurrent.objects.exclude(batch_code__startswith='2024').exclude(batch_code__startswith='2025')
        
        total = staging_qs.count()
        processed = 0
        created_profiles = 0
        created_results = 0

        self.stdout.write(f"Found {total} records in PGResultCurrent staging (excluding 2024+ batches).")

        # Dictionary to cache profiles to avoid multiple queries per reg_no
        profile_cache = {}
        # Preload existing profiles to memory to avoid duplicate creation
        self.stdout.write("Loading existing profiles into memory...")
        for p in PGOldStudentProfile.objects.all().iterator(chunk_size=5000):
            profile_cache[p.registration_no] = p

        results_bulk = []

        self.stdout.write("Processing staging records...")
        for record in staging_qs.iterator(chunk_size=2000):
            reg_no = record.college_reg_no
            if not reg_no:
                processed += 1
                continue

            college_obj = college_cache.get(str(record.institute_code)) if record.institute_code else None

            # Get or create profile in memory/db
            profile = profile_cache.get(reg_no)
            if not profile:
                user_acc = UserAccount.objects.filter(username=reg_no).first()
                profile = PGOldStudentProfile.objects.create(
                    registration_no=reg_no,
                    user=user_acc,
                    roll_no=record.college_roll_no,
                    student_name=record.student_name or '',
                    student_name_hindi=record.student_name_hindi,
                    fathers_name=record.fathers_name,
                    mothers_name=record.mothers_name,
                    college=college_obj,
                    course_code=record.course_code,
                    discipline_code=record.discipline_code,
                    pg_faculty=record.faculty,
                    batch_code=record.batch_code,
                    current_semester=record.semester_code,
                    final_result=record.final_result,
                    gpa=record.gpa,
                    cgpa=record.cgpa,
                    total_percentage=record.total_per,
                    source_user_id=record.user_id,
                )
                profile_cache[reg_no] = profile
                created_profiles += 1

            results_bulk.append(PGOldResult(
                student_profile=profile,
                source_id=record.source_id,
                user_id=record.user_id,
                college_roll_no=record.college_roll_no,
                college_reg_no=record.college_reg_no,
                student_name=record.student_name,
                fathers_name=record.fathers_name,
                mothers_name=record.mothers_name,
                semester_code=record.semester_code,
                batch_code=record.batch_code,
                session_code=record.session_code,
                course_code=record.course_code,
                discipline_code=record.discipline_code,
                paper_code=record.paper_code,
                subject_code=record.subject_code,
                subject_name=record.subject_name,
                faculty=record.faculty,
                status=record.status,
                exam_type_his=record.exam_type_his,
                exam_type=record.exam_type,
                maximum_mark=record.maximum_mark,
                pass_mark=record.pass_mark,
                mark_secured=record.mark_secured,
                subject_total_mark=record.subject_total_mark,
                subject_ca=record.subject_ca,
                subject_ng=record.subject_ng,
                subject_ce=record.subject_ce,
                subject_gp=record.subject_gp,
                total_ca=record.total_ca,
                total_ce=record.total_ce,
                subject_result=record.subject_result,
                final_result=record.final_result,
                grand_total_mark=record.grand_total_mark,
                total_secured_mark=record.total_secured_mark,
                total_per=record.total_per,
                institute_code=record.institute_code,
                gpa=record.gpa,
                cgpa=record.cgpa,
                numrical_let_grad=record.numrical_let_grad,
                let_grad_sub=record.let_grad_sub,
                let_grad=record.let_grad,
                dsc_grad=record.dsc_grad,
                agreegate=record.agreegate,
                grade=record.grade,
                record_status=record.record_status,
                final_sheet_status=record.final_sheet_status,
                student_name_hindi=record.student_name_hindi,
                max_total_mark=record.max_total_mark,
                college=college_obj,
                pg_faculty=record.faculty,
                copied_from_staging=True
            ))

            processed += 1
            if len(results_bulk) >= batch_size:
                PGOldResult.objects.bulk_create(results_bulk)
                created_results += len(results_bulk)
                results_bulk = []
                self.stdout.write(f"Processed {processed}/{total} records... (Profiles created so far: {created_profiles})")

        # Create remaining
        if results_bulk:
            PGOldResult.objects.bulk_create(results_bulk)
            created_results += len(results_bulk)
            self.stdout.write(f"Processed {processed}/{total} records... (Profiles created so far: {created_profiles})")

        self.stdout.write(self.style.SUCCESS(f"Finished! Total Profiles Created: {created_profiles}, Total Results Created: {created_results}"))
