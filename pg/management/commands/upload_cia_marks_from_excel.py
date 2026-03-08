import pandas as pd
from django.core.management.base import BaseCommand
from pg.models import PGStudentCourseAssessment
from decimal import Decimal
import os


"""
Usage examples:

# Dry run (no changes):
python manage.py upload_cia_marks_from_excel \
    --file courses_data/cia_pg_1_mark.xlsx \
    --session 2025-26 --semester 1ST \
    --exam-type BACK --no-header --dry-run

# Execute (save to DB):
python manage.py upload_cia_marks_from_excel \
    --file courses_data/cia_pg_1_mark.xlsx \
    --session 2025-26 --semester 1ST \
    --exam-type BACK --no-header --execute
"""

class Command(BaseCommand):
    help = 'Upload CIA marks from an Excel/ODS file into blank entries'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Path to the Excel/ODS file')
        parser.add_argument('--session', required=True, help='Target session (e.g. 2025-26)')
        parser.add_argument('--semester', required=True, help='Target semester label (e.g. 1ST, 2ND)')
        parser.add_argument('--exam-type', default=None, help='Filter by exam type (e.g. BACK, REGULAR)')
        parser.add_argument('--no-header', action='store_true', default=False,
                            help='If set, file has no header row. Assumes: col1=reg_no, col4=course_code, col6=marks')
        parser.add_argument('--dry-run', action='store_true', default=False, help='Dry run mode (no DB changes)')
        parser.add_argument('--execute', action='store_true', help='Actually update the DB')

    def handle(self, *args, **options):
        file_path = options['file']
        session = options['session']
        semester = options['semester'].upper()
        exam_type = options.get('exam_type', None)
        no_header = options['no_header']
        execute = options['execute']
        dry_run = options['dry_run'] or not execute

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write("=" * 100)
        self.stdout.write("UPLOADING CIA MARKS FROM FILE")
        self.stdout.write("=" * 100)
        self.stdout.write(f"File      : {file_path}")
        self.stdout.write(f"Session   : {session}")
        self.stdout.write(f"Semester  : {semester}")
        self.stdout.write(f"Exam Type : {exam_type or 'All'}")
        self.stdout.write(f"Mode      : {'DRY RUN' if dry_run else 'EXECUTE'}")
        self.stdout.write("=" * 100)

        # 1. Read file
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.ods':
                engine = 'odf'
            else:
                engine = None  # pandas auto-detects xlsx/xls

            if no_header:
                df = pd.read_excel(file_path, engine=engine, header=None)
                # Assign column names based on known ODS structure:
                # col0=college_code, col1=registration_no, col2=name, col3=roll_no,
                # col4=course_code, col5=department, col6=marks_obtained
                df.columns = ['college_code', 'registration_no', 'name', 'roll_no',
                              'course_code', 'department', 'marks_obtained'] + [f'extra_{i}' for i in range(max(0, len(df.columns) - 7))]
            else:
                df = pd.read_excel(file_path, engine=engine)
                df.columns = [str(c).lower().strip() for c in df.columns]

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading file: {str(e)}"))
            return

        # Validate required columns
        required_cols = ['registration_no', 'course_code', 'marks_obtained']
        for col in required_cols:
            if col not in df.columns:
                self.stdout.write(self.style.ERROR(f"Missing required column: {col}"))
                self.stdout.write(f"Available columns: {list(df.columns)}")
                return

        stats = {'total_rows': len(df), 'updated': 0, 'not_found': 0, 'errors': 0}
        missing_entries = []

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
            assessment_qs = PGStudentCourseAssessment.objects.filter(
                course_code=course_code,
                semester=semester,
                session=session,
                label='CIA',
                student__registration_no=reg_no,
            )
            if exam_type:
                assessment_qs = assessment_qs.filter(exam_type=exam_type.upper())

            assessment = assessment_qs.first()

            if not assessment:
                self.stdout.write(self.style.WARNING(f"    ⚠️  CIA entry not found in DB"))
                missing_entries.append({
                    'reg_no': reg_no,
                    'roll_no': roll_no,
                    'name': name,
                    'course_code': course_code
                })
                stats['not_found'] += 1
                continue

            # 3. Parse Marks (absent = 0 marks + is_absent flag)
            is_absent = False
            marks_obtained = None

            if marks_raw in ['A', 'ABSENT', 'NAN', '']:
                marks_obtained = Decimal('0')   # Absent → 0 marks
                is_absent = True                # Also flag as absent
            else:
                try:
                    marks_obtained = Decimal(marks_raw)
                except Exception:
                    self.stdout.write(self.style.ERROR(f"    ❌ Invalid marks value: {marks_raw}"))
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
                    f"    ✅ Updated: {marks_obtained if not is_absent else 'ABSENT'} | Pass: {is_pass}"
                ))
            else:
                self.stdout.write(
                    f"    [Dry Run] Would set: {marks_obtained if not is_absent else 'ABSENT'} | Pass: {is_pass}"
                )

            stats['updated'] += 1

        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 100)
        self.stdout.write(f"Total Rows in File  : {stats['total_rows']}")
        self.stdout.write(f"Successfully Updated: {stats['updated']}")
        self.stdout.write(f"Entries Not Found   : {stats['not_found']}")
        self.stdout.write(f"Errors in Format    : {stats['errors']}")
        
        if missing_entries:
            self.stdout.write("\n" + "-" * 50)
            self.stdout.write("DETAILED LIST OF ENTRIES NOT FOUND IN DB")
            self.stdout.write("-" * 50)
            self.stdout.write(f"{'Reg No':<15} | {'Roll No':<10} | {'Course':<10} | {'Name'}")
            self.stdout.write("-" * 50)
            for m in missing_entries:
                self.stdout.write(f"{m['reg_no']:<15} | {m['roll_no']:<10} | {m['course_code']:<10} | {m['name']}")
            self.stdout.write("-" * 50)

        self.stdout.write("=" * 100)
