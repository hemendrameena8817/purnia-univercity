import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from pg.models import (
    PGStudentProfile, 
    PGStudentCourseAssessment,
    PGExamResult
)

class Command(BaseCommand):
    help = 'Upload PG CIA marks from Excel/ODS file'

    """
    Usage Examples:
    # Dry Run:
    python manage.py upload_cia_marks_from_excel \
        --file courses_data/cia_pg_1_mark.xlsx \
        --session 2025-26 --semester 1ST \
        --exam-type BACK --no-header

    # Execute (save to DB):
    python manage.py upload_cia_marks_from_excel \
        --file courses_data/cia_pg_1_mark.xlsx \
        --session 2025-26 --semester 1ST \
        --exam-type BACK --no-header --execute
    """

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to Excel/ODS file')
        parser.add_argument('--session', type=str, required=True, help='Academic session (e.g., 2024-25)')
        parser.add_argument('--semester', type=str, required=True, help='Semester (e.g., 1ST, 2ND)')
        parser.add_argument('--exam-type', type=str, default='REGULAR', help='Exam type (REGULAR/BACK)')
        parser.add_argument('--no-header', action='store_true', help='File has no header row')
        parser.add_argument('--execute', action='store_true', help='Execute database updates')

    def handle(self, *args, **options):
        file_path = options['file']
        session = options['session']
        semester = options['semester'].upper()
        exam_type = options['exam_type'].upper()
        dry_run = not options['execute']

        try:
            if file_path.endswith('.ods'):
                df = pd.read_excel(file_path, engine='odf', header=None if options['no_header'] else 0)
            else:
                df = pd.read_excel(file_path, header=None if options['no_header'] else 0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading file: {e}"))
            return

        # Map common column positions if no header
        if options['no_header']:
            # Expected format: College | Reg No | Name | Roll No | Course | Dept | Marks
            cols = list(df.columns)
            mapping = {
                'registration_no': cols[1],
                'course_code': cols[4],
                'marks_obtained': cols[6],
                'roll_no': cols[3],
                'name': cols[2]
            }
            df = df.rename(columns={v: k for k, v in mapping.items()})

        # Paper Code Mappings for Semester 1 (Excel: CC-I -> DB: PG101)
        PAPER_MAP = {
            '1ST': {
                'CC-I': 'PG101',
                'CC-II': 'PG102',
                'CC-III': 'PG103',
                'CC-IV': 'PG104',
                'AECC-I': 'PG105',
                'AECC-1': 'PG105',
            }
        }

        required_cols = ['registration_no', 'course_code', 'marks_obtained']
        for col in required_cols:
            if col not in df.columns:
                self.stdout.write(self.style.ERROR(f"Missing required column: {col}"))
                self.stdout.write(f"Available columns: {list(df.columns)}")
                return

        stats = {'total_rows': len(df), 'updated': 0, 'not_found': 0, 'errors': 0}
        missing_entries = []
        updated_with_marks = set()  # Track (reg_no, course_code) updated with actual marks

        for index, row in df.iterrows():
            reg_no = str(row['registration_no']).strip() if pd.notna(row['registration_no']) else None
            roll_no = str(row['roll_no']).strip() if 'roll_no' in df.columns and pd.notna(row['roll_no']) else "N/A"
            name = str(row['name']).strip() if 'name' in df.columns and pd.notna(row['name']) else "N/A"
            course_code = str(row['course_code']).strip() if pd.notna(row['course_code']) else None
            marks_raw = str(row['marks_obtained']).strip().upper() if pd.notna(row['marks_obtained']) else 'ABSENT'

            if not reg_no or reg_no == 'NAN':
                stats['errors'] += 1
                continue
            if not course_code or course_code == 'NAN':
                stats['errors'] += 1
                continue

            self.stdout.write(f"\n[{index+1}] {reg_no} | {course_code} | Marks: {marks_raw}")

            # 2. Find CIA entry in DB (search by course_code field)
            # Support both Original (Excel) and Translated (Database) codes
            search_codes = [course_code]
            translation = PAPER_MAP.get(semester, {}).get(course_code)
            if translation:
                search_codes.append(translation)

            assessment = PGStudentCourseAssessment.objects.filter(
                student__registration_no=reg_no,
                semester=semester,
                session=session,
                label__icontains='CIA',
                paper_code__in=search_codes
            ).first()

            if not assessment:
                # Try fallback matching by course_name if paper_code doesn't match
                assessment = PGStudentCourseAssessment.objects.filter(
                    student__registration_no=reg_no,
                    semester=semester,
                    session=session,
                    label__icontains='CIA',
                    course_name__icontains=course_code
                ).first()

            if not assessment:
                self.stdout.write(self.style.WARNING(f"    \u26a0\ufe0f  CIA entry not found in DB"))
                missing_entries.append({
                    'reg_no': reg_no,
                    'roll_no': roll_no,
                    'name': name,
                    'course_code': course_code
                })
                stats['not_found'] += 1
                continue

            # 3. Check for ABSENT
            is_absent = False
            marks_obtained = None
            
            # Key for duplicate tracking
            cache_key = (reg_no, course_code)

            if marks_raw in ['A', 'ABSENT', 'NAN', '', ' ', '\xa0']:
                # If we already encountered valid marks for this student/course in this run,
                # skip this duplicate empty entry to avoid overwriting valid data.
                if cache_key in updated_with_marks:
                    self.stdout.write(self.style.WARNING(f"    \u26a0\ufe0f  Duplicate empty row skipped for {reg_no} | {course_code}"))
                    continue
                marks_obtained = Decimal('0')   # Absent \u2794 0 marks
                is_absent = True                # Also flag as absent
            else:
                try:
                    marks_obtained = Decimal(marks_raw)
                    updated_with_marks.add(cache_key) # Track as updated with data
                except Exception:
                    self.stdout.write(self.style.ERROR(f"    \u274c Invalid marks value: {marks_raw}"))
                    stats['errors'] += 1
                    continue

            # 4. Calculate Pass/Fail
            is_pass = False
            if not is_absent and marks_obtained is not None:
                if assessment.ind_pass_marks:
                    is_pass = marks_obtained >= assessment.ind_pass_marks
                elif assessment.ind_max_marks:
                    is_pass = marks_obtained >= (assessment.ind_max_marks * Decimal('0.45'))

            # 5. Update DB
            if not dry_run:
                assessment.ind_marks_obtained = marks_obtained
                assessment.ind_is_absent = is_absent
                assessment.ind_is_pass = is_pass
                assessment.is_cia_fill = True
                assessment.save()
                self.stdout.write(self.style.SUCCESS(
                    f"    \u2705 Updated: {marks_obtained if not is_absent else 'ABSENT'} | Pass: {is_pass}"
                ))
            else:
                self.stdout.write(
                    f"    [Dry Run] Would set: {marks_obtained if not is_absent else 'ABSENT'} | Pass: {is_pass}"
                )

            stats['updated'] += 1

        # Summary
        self.stdout.write("\n" + "="*100)
        self.stdout.write("SUMMARY")
        self.stdout.write("="*100)
        self.stdout.write(f"Total Rows in File  : {stats['total_rows']}")
        self.stdout.write(f"Successfully Updated: {stats['updated']}")
        self.stdout.write(f"Entries Not Found   : {stats['not_found']}")
        self.stdout.write(f"Errors in Format    : {stats['errors']}")
        self.stdout.write("="*100)

        # Show detailed list of missing entries
        if missing_entries:
            self.stdout.write("\n" + "!"*100)
            self.stdout.write("DETAILED LIST OF ENTRIES NOT FOUND IN DB")
            self.stdout.write("!"*100)
            self.stdout.write(f"{'Reg No':20} | {'Roll No':15} | {'Name':30} | {'Course':20}")
            self.stdout.write("-" * 100)
            for entry in missing_entries:
                self.stdout.write(f"{entry['reg_no']:20} | {entry['roll_no']:15} | {entry['name']:30} | {entry['course_code']:20}")
            self.stdout.write("!"*100 + "\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n\ud83d\udca1 This was a DRY RUN. No database changes were made."))
