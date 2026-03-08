"""
Create Blank CIA Entries for Failed Students

This script identifies students who failed a specific semester (source)
and creates blank CIA entries for them in a target session/semester.
It sets the exam_type to 'BACK' for these entries.

Arguments:
  --batch             : Batch name (e.g. 2023-25)
  --source-session    : Session where the student failed (e.g. 2023-24)
  --target-session    : Session for new blank entries (e.g. 2024-25)
  --target-semester   : Semester to create entries for (e.g. 1, 2, 3, 4)
  --registration-no   : (Optional) Single student filter
  --dry-run           : Preview without saving (default)
  --execute           : Save changes to database

Usage:
python manage.py create_failed_student_cia_entries \
    --batch 2024-26 \
    --source-session 2024-25 \
    --source-semester 1 \
    --target-session 2025-26 \
    --target-semester 1 \
    --result-status PENDING \
    --dry-run

    python manage.py create_failed_student_cia_entries \
    --batch 2023-25 \
    --source-session 2024-25 \
    --source-semester 1 \
    --target-session 2025-26 \
    --target-semester 1 \   
    --result-status PROMOTED \
    --execute
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from pg.models import (
    PGStudentProfile, 
    PGStudentCourseAssessment, 
    PGBatch, 
    PGCourseStructure, 
    PGExamResult
)
from decimal import Decimal

# python manage.py create_failed_student_cia_entries --batch 2024-26 --source-session 2024-25 --source-semester 1 --target-session 2025-26 --target-semester 1 --execute

class Command(BaseCommand):
    help = 'Create blank CIA entries for failed students'

    def add_arguments(self, parser):
        parser.add_argument('--batch', required=True, help='Batch name (e.g. 2023-25)')
        parser.add_argument('--source-session', required=True, help='Session where student failed')
        parser.add_argument('--source-semester', required=True, help='Semester number where student failed (1, 2, 3, or 4)')
        parser.add_argument('--target-session', required=True, help='Session for new entries')
        parser.add_argument('--target-semester', required=True, help='Semester number for new entries (1, 2, 3, or 4)')
        parser.add_argument('--registration-no', help='Filter for single student')
        parser.add_argument('--result-status', default='FAIL', help='Result status to filter by (e.g. FAIL, PROMOTED)')
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
        result_status = options.get('result_status', 'FAIL').upper()
        
        # Logic for dry_run: if --execute is NOT provided, it's a dry run.
        # If --dry-run is explicitly provided, it's also a dry run.
        execute = options['execute']
        dry_run = options['dry_run'] or not execute

        self.stdout.write("=" * 100)
        self.stdout.write("CREATE BLANK CIA ENTRIES FOR FAILED STUDENTS")
        self.stdout.write("=" * 100)
        self.stdout.write(f"Batch            : {batch_name}")
        self.stdout.write(f"Source Session   : {source_session}")
        self.stdout.write(f"Source Semester  : {source_semester}")
        self.stdout.write(f"Target Session   : {target_session}")
        self.stdout.write(f"Target Semester  : {target_semester}")
        self.stdout.write(f"Result Status    : {result_status}")
        self.stdout.write(f"Mode             : {'DRY RUN' if dry_run else 'EXECUTE'}")
        self.stdout.write("=" * 100)

        # 1. Get variants for semester filtering
        source_sem_variants = self.get_semester_variants(source_semester)
        target_sem_variants = self.get_semester_variants(target_semester)
        
        # 2. Filter Failed Students
        failed_results = PGExamResult.objects.filter(
            student__batch__iexact=batch_name,
            session=source_session,
            semester__in=source_sem_variants,
            semester_result=result_status
        )

        if registration_no:
            failed_results = failed_results.filter(student__registration_no=registration_no)

        total_failed = failed_results.count()
        self.stdout.write(f"Found {total_failed} students with {result_status} status in {batch_name} | Sem {source_semester} | {source_session}")

        if total_failed == 0:
            self.stdout.write(self.style.WARNING("No failed students found. Exiting."))
            return

        stats = {
            'processed': 0,
            'entries_created': 0,
            'already_existed': 0,
            'no_structure': 0
        }

        for result in failed_results.select_related('student', 'student__department'):
            student = result.student
            dept = student.department
            reg_no = student.registration_no

            self.stdout.write(f"\nProcessing [{reg_no}] {student.get_full_name()} | Dept: {dept.name if dept else 'N/A'}")

            # 3. Get Course Structure
            structures = PGCourseStructure.objects.filter(
                department=dept,
                semester__in=target_sem_variants,
                label='CIA'
            )

            if not structures.exists():
                # Try peer fallback if department structure is missing
                peer_assessments = PGStudentCourseAssessment.objects.filter(
                    batch__name=batch_name,
                    department=dept,
                    semester__in=target_sem_variants,
                    label='CIA'
                ).exclude(student=student)

                if peer_assessments.exists():
                    # Use unique paper codes from peers
                    seen_codes = set()
                    peer_templates = []
                    for p in peer_assessments:
                        if p.paper_code not in seen_codes:
                            peer_templates.append(p)
                            seen_codes.add(p.paper_code)
                    
                    self.stdout.write(f"  Using peer template (Found {len(peer_templates)} papers)")
                    self._process_entries(student, peer_templates, target_session, target_semester, dry_run, stats, is_structure=False)
                else:
                    self.stdout.write(self.style.WARNING(f"  ⚠️ No course structure or peer data found for {dept.name if dept else 'N/A'} Sem {target_semester}"))
                    stats['no_structure'] += 1
                    continue
            else:
                self.stdout.write(f"  Using PGCourseStructure (Found {structures.count()} papers)")
                self._process_entries(student, structures, target_session, target_semester, dry_run, stats, is_structure=True)
            
            stats['processed'] += 1

        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 100)
        self.stdout.write(f"Students Processed   : {stats['processed']}")
        self.stdout.write(f"Entries Created      : {stats['entries_created']}")
        self.stdout.write(f"Already Existed      : {stats['already_existed']}")
        self.stdout.write(f"Skipped (No Data)    : {stats['no_structure']}")
        self.stdout.write("=" * 100)

    def _process_entries(self, student, data_list, target_session, target_semester, dry_run, stats, is_structure=True):
        for item in data_list:
            if is_structure:
                paper_code = item.paper_code or item.code or ''
                if paper_code and not paper_code.upper().startswith('PG'):
                    paper_code = f"PG{paper_code}"
                
                label = item.label or 'CIA'
                course_name = item.course_name
                course_code = item.code
                course_type = item.course_type
                max_marks = int(item.max_marks) if item.max_marks else 0
                pass_marks = Decimal(str(item.min_marks)) if item.min_marks else Decimal(str(round(max_marks * 0.45, 2)))
            else:
                # item is a PGStudentCourseAssessment object (peer template)
                paper_code = item.paper_code
                label = item.label
                course_name = item.course_name
                course_code = item.course_code
                course_type = item.course_type
                max_marks = item.ind_max_marks
                pass_marks = item.ind_pass_marks

            # Normalize semester label to match TARGET_SEMESTER or typical "1ST", "2ND" etc.
            sem_label = str(target_semester)
            if sem_label == '1': sem_label = '1ST'
            elif sem_label == '2': sem_label = '2ND'
            elif sem_label == '3': sem_label = '3RD'
            elif sem_label == '4': sem_label = '4TH'

            exists = PGStudentCourseAssessment.objects.filter(
                student=student,
                semester=sem_label,
                session=target_session,
                paper_code=paper_code,
                label=label
            ).exists()

            if exists:
                self.stdout.write(f"    [Skip] {paper_code} | {label} - Already exists")
                stats['already_existed'] += 1
                continue

            if not dry_run:
                PGStudentCourseAssessment.objects.create(
                    student=student,
                    department=student.department,
                    batch=PGBatch.objects.filter(name=student.batch).first(),
                    college_code=student.college.college_code if student.college else None,
                    semester=sem_label,
                    session=target_session,
                    course_name=course_name,
                    course_code=course_code,
                    course_type=course_type,
                    paper_code=paper_code,
                    label=label,
                    exam_type='BACK',
                    ind_max_marks=max_marks,
                    ind_pass_marks=pass_marks,
                    ind_is_absent=False,
                    ind_marks_obtained=None,
                    ind_is_pass=None,
                    is_cia_fill=False,
                    is_ese_fill=False
                )
                self.stdout.write(self.style.SUCCESS(f"    [Created] {paper_code} | {label}"))
            else:
                self.stdout.write(f"    [Would Create] {paper_code} | {label} | Type: BACK")
            
            stats['entries_created'] += 1
