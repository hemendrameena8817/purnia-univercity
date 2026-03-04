from django.core.management.base import BaseCommand
from pg.models import PGExamRegistration, PGStudentCourseAssessment, PGStudentProfile, PGBatch, PGExamResult
from django.db import transaction
from pg.services.create_exam_registration_from_result import SEMESTER_STR_TO_INT

"""
Usage:
    # Dry Run
    python manage.py create_pg_back_ese_entries \
        --batch 2024-26 \
        --source-session 2024-25 \
        --source-semester 1 \
        --target-session 2025-26 \
        --target-semester 1 \
        --dry-run

    # Execute
    python manage.py create_pg_back_ese_entries \
        --batch 2024-26 \
        --source-session 2024-25 \
        --source-semester 1 \
        --target-session 2025-26 \
        --target-semester 1 \
        --execute
"""

class Command(BaseCommand):
    help = 'Create blank ESE entries for PG Back students'

    def add_arguments(self, parser):
        parser.add_argument('--batch', required=True, help='Batch name (e.g. 2023-25)')
        parser.add_argument('--source-session', required=True, help='Session where student failed (e.g. 2024-25)')
        parser.add_argument('--source-semester', required=True, help='Semester number where student failed (1, 2, 3, or 4)')
        parser.add_argument('--target-session', required=True, help='Session for new back entries (e.g. 2025-26)')
        parser.add_argument('--target-semester', required=True, help='Semester number for new entries (1, 2, 3, or 4)')
        parser.add_argument('--registration-no', help='Filter for single student')
        parser.add_argument('--dry-run', action='store_true', default=False, help='Dry run')
        parser.add_argument('--execute', action='store_true', help='Actually save to DB')

    def get_semester_variants(self, sem):
        """Return common variants for semester filtering."""
        sem_str = str(sem).upper()
        variants = [sem_str]
        if sem_str == '1' or sem_str == '1ST' or sem_str == 'FIRST':
            variants.extend(['1', '1ST', 'I', 'FIRST'])
        elif sem_str == '2' or sem_str == '2ND' or sem_str == 'SECOND':
            variants.extend(['2', '2ND', 'II', 'SECOND'])
        elif sem_str == '3' or sem_str == '3RD' or sem_str == 'THIRD':
            variants.extend(['3', '3RD', 'III', 'THIRD'])
        elif sem_str == '4' or sem_str == '4TH' or sem_str == 'FOURTH':
            variants.extend(['4', '4TH', 'IV', 'FOURTH'])
        return list(set(variants))

    def handle(self, *args, **options):
        batch_name = options['batch']
        source_session = options['source_session']
        source_semester = options['source_semester']
        target_session = options['target_session']
        target_semester = options['target_semester']
        registration_no = options.get('registration_no')
        
        execute = options['execute']
        dry_run = options['dry_run'] or not execute

        # 1. Get sem_int for registration creation
        target_sem_label = str(target_semester)
        if target_sem_label == '1': target_sem_label = '1ST'
        elif target_sem_label == '2': target_sem_label = '2ND'
        elif target_sem_label == '3': target_sem_label = '3RD'
        elif target_sem_label == '4': target_sem_label = '4TH'
        
        sem_int = SEMESTER_STR_TO_INT.get(target_sem_label)

        self.stdout.write("=" * 100)
        self.stdout.write("CREATE BLANK ESE ENTRIES FOR FAILED/PROMOTED STUDENTS (BACK)")
        self.stdout.write("=" * 100)
        self.stdout.write(f"Batch            : {batch_name}")
        self.stdout.write(f"Source Session   : {source_session}")
        self.stdout.write(f"Source Semester  : {source_semester}")
        self.stdout.write(f"Target Session   : {target_session}")
        self.stdout.write(f"Target Semester  : {target_semester}")
        self.stdout.write(f"Mode             : {'DRY RUN' if dry_run else 'EXECUTE'}")
        self.stdout.write("=" * 100)

        # 1. Get variants for semester filtering
        source_sem_variants = self.get_semester_variants(source_semester)
        
        # 2. Identify Students to process (those with 'PROMOTED' status)
        # As requested: "only for promoted"
        target_statuses = ['PROMOTED']
        
        result_qs = PGExamResult.objects.filter(
            student__batch__iexact=batch_name,
            session=source_session,
            semester__in=source_sem_variants,
            semester_result__in=target_statuses
        )

        if registration_no:
            result_qs = result_qs.filter(student__registration_no=registration_no)

        if not result_qs.exists():
            self.stdout.write(self.style.WARNING(f"No non-PASS (FAIL/PROMOTED etc.) results found for Batch {batch_name}, Sem {source_semester}, Session {source_session}"))
            return

        self.stdout.write(f"Found {result_qs.count()} students with backlogs/failures.")

        stats = {
            'processed': 0,
            'entries_created': 0,
            'already_existed': 0,
            'no_source_data': 0
        }

        # 3. Semester label for new entries
        target_sem_label = str(target_semester)
        if target_sem_label == '1': target_sem_label = '1ST'
        elif target_sem_label == '2': target_sem_label = '2ND'
        elif target_sem_label == '3': target_sem_label = '3RD'
        elif target_sem_label == '4': target_sem_label = '4TH'

        for res in result_qs.select_related('student'):
            student = res.student
            self.stdout.write(f"\nProcessing [{student.registration_no}] {student.get_full_name()} | Result: {res.semester_result}")

            # 4. Create BACK Registration if missing
            self.ensure_back_registration(student, sem_int, target_session, dry_run, stats)

            # 5. Scan source assessments to identify failed papers
            source_ese_assessments = PGStudentCourseAssessment.objects.filter(
                student=student,
                semester__in=source_sem_variants,
                session=source_session,
                label__icontains='ESE'
            )

            if not source_ese_assessments.exists():
                self.stdout.write(f"  ⚠️ No ESE assessments found in session {source_session}")
                stats['no_source_data'] += 1
                continue

            for prev_ese in source_ese_assessments:
                paper_code = prev_ese.paper_code
                
                # Check for failure in this paper
                is_failed = False
                if prev_ese.ind_is_pass is False:
                    is_failed = True
                elif prev_ese.ind_marks_obtained is not None and prev_ese.ind_pass_marks is not None:
                    if prev_ese.ind_marks_obtained < prev_ese.ind_pass_marks:
                        is_failed = True
                
                if not is_failed:
                    self.stdout.write(f"    [Pass] {paper_code} - Assessment marked as pass")
                    continue

                # 6. Create blank ESE entry in target
                self.create_back_entry(prev_ese, target_session, target_sem_label, dry_run, stats)
            
            stats['processed'] += 1

        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 100)
        self.stdout.write(f"Students Processed   : {stats['processed']}")
        self.stdout.write(f"Reg Created/Exists   : {stats.get('reg_created', 0)} / {stats.get('reg_existed', 0)}")
        self.stdout.write(f"ESE Entries Created  : {stats['entries_created']}")
        self.stdout.write(f"Already Existed      : {stats['already_existed']}")
        self.stdout.write(f"Skipped (No Source)  : {stats['no_source_data']}")
        self.stdout.write("=" * 100)

    def ensure_back_registration(self, student, sem_int, session, dry_run, stats):
        from pg.services.create_exam_registration_from_result import REGISTRATION_START, REGISTRATION_END
        
        reg_exists = PGExamRegistration.objects.filter(
            student=student,
            sem=sem_int,
            session=session,
            exam_type='BACK'
        ).exists()

        if reg_exists:
            self.stdout.write(f"  [Reg] Already exists")
            stats['reg_existed'] = stats.get('reg_existed', 0) + 1
            return

        if not dry_run:
            PGExamRegistration.objects.create(
                student=student,
                sem=sem_int,
                session=session,
                exam_type='BACK',
                status='OPEN',
                is_open=True,
                start_date=REGISTRATION_START,
                end_date=REGISTRATION_END
            )
            self.stdout.write(self.style.SUCCESS(f"  [Reg] Created BACK registration"))
        else:
            self.stdout.write(f"  [Reg] Would Create BACK registration")
        
        stats['reg_created'] = stats.get('reg_created', 0) + 1

    def create_back_entry(self, prev, target_session, target_sem, dry_run, stats):
        # Check if already exists
        exists = PGStudentCourseAssessment.objects.filter(
            student=prev.student,
            semester=target_sem,
            paper_code=prev.paper_code,
            label=prev.label,
            session=target_session,
            exam_type='BACK'
        ).exists()

        if exists:
            self.stdout.write(f"    [Skip] {prev.paper_code} | {prev.label} - Already exists")
            stats['already_existed'] += 1
            return

        if not dry_run:
            PGStudentCourseAssessment.objects.create(
                student=prev.student,
                course_name=prev.course_name,
                course_short_name=prev.course_short_name,
                course_type=prev.course_type,
                course_code=prev.course_code,
                paper_code=prev.paper_code,
                semester=target_sem,
                label=prev.label,
                department=prev.department,
                degree=prev.degree,
                batch=prev.batch, 
                college_code=prev.college_code,
                session=target_session,
                exam_type='BACK',
                ind_max_marks=prev.ind_max_marks,
                ind_pass_marks=prev.ind_pass_marks,
                ind_marks_obtained=None, 
                ind_is_absent=False, 
                ind_is_pass=None,
                is_cia_fill=False,
                is_ese_fill=False,
            )
            self.stdout.write(self.style.SUCCESS(f"    [Created] {prev.paper_code} | {prev.label}"))
        else:
            self.stdout.write(f"    [Would Create] {prev.paper_code} | {prev.label} | Type: BACK")
        
        stats['entries_created'] += 1
