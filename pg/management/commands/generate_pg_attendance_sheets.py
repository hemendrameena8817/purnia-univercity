import os
import re
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pg.models import PGExam, PGExamRegistration, PGDepartment
from colleges.models import College
from pg.utils.pdf_generator import generate_pg_attendance_sheet_pdf
# python manage.py generate_pg_attendance_sheets \
#   --exam-uid ba082de1-32fb-4c6a-b5b6-4facdc678f48 \
#   --college-uid \
#     a82e1271-05ba-4199-9f92-02cd0d33ce5c \
#     fb1589be-fffc-4f25-a064-b46472646f74 \
#     a5fa9c5a-4cbe-4376-ba2e-e9688e0384f2 \
#     a584b9fb-ab99-4b88-804e-3f789dd0732a \
#     8764ba4e-6968-4882-8020-06dd7ec4d0dd \
#     1dbeddef-ae4a-47d5-ac1d-973652466479 \
#   --department-uid \
#     d22e6316-113b-4dca-b6ec-743514497acd \
#     2b7c5882-d86c-4579-8add-3db1b0bf4b05 \
#     343aca47-80a2-48ab-b4e5-35cc686db4bd \
#     5db309ef-e9ea-492b-89fa-d27a51f101de \
#     229fbdab-5b07-4652-b836-0d68d00d0b5c \
#     678465e3-da4c-4a1f-9139-d4c653f85b14 \
#     1b294fa2-2973-491d-b24f-8a4fa0143428 \
#     5a11c83b-f460-4c29-9874-1ab31816acd1 \
#     a06640a0-ac39-49a1-8a6d-440da8836885 \
#     316c518f-972e-43f6-8be5-06fbb1ad27a4 \
#     b2f20a5f-5a0c-4382-b052-b31e8a895820 \
#     ce908839-d63a-4ac2-8ced-9bd1aba35640 \
#     2c05e7bb-e7d8-472b-af55-4dc5ca2c64c0 \
#     bd6f3ea0-908f-4d30-a896-d16f6b8eaeb1 \
#     ec77dc97-1d3e-443a-9ba5-d1db2508c776 \
#     e510c4d9-0b7d-4bda-957b-4acfa7f13895 \
#     24f38e5a-9593-4ac3-99f0-b4c81df96af9 \
#     7ee3795e-7d3d-4e6a-9e64-03727153f36b \
#     d3ed3a5b-778f-4df1-b279-ae5d2287c2e6 \
#     a522e2a4-bf93-4074-b553-b2fe04258de6 \
#     b4507b0a-5359-494a-bdc5-86a1944af693

#olocakl 
#  python manage.py generate_pg_attendance_sheets --exam-uid 10f3ea2b-675b-4c5d-baf6-017ef4b6b0de --college-uid 3788a4ef-76b6-4acc-9b33-e3f4b00868b4 314384cc-ad4b-43ad-aabe-ca58c7a97e48 --department-uid de58d650-0b33-4262-8991-050b94ff283c 76b6dde4-c363-4913-bcbb-453928c3e71b

class Command(BaseCommand):
    help = 'Generate PG Attendance Sheets in batch for all colleges and departments associated with an exam.'

    def add_arguments(self, parser):
        parser.add_argument('--exam-uid', type=str, required=True, help='UID of the PG Exam')
        parser.add_argument('--college-uid', nargs='+', help='Optional: One or more UIDs of specific Colleges')
        parser.add_argument('--department-uid', nargs='+', help='Optional: One or more UIDs of specific Departments')
        parser.add_argument('--output-dir', type=str, default='attendance_sheets', help='Directory to save generated PDFs')

    def handle(self, *args, **options):
        exam_uid = options['exam_uid']
        college_uids = options.get('college_uid') or []
        dept_uids = options.get('department_uid') or []
        output_dir = options['output_dir']

        # Ensure output directory exists
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(settings.BASE_DIR, output_dir)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.stdout.write(self.style.SUCCESS(f"Created directory: {output_dir}"))

        try:
            exam = PGExam.objects.get(uid=exam_uid)
        except PGExam.DoesNotExist:
            raise CommandError(f"PGExam with UID {exam_uid} does not exist.")

        self.stdout.write(f"Generating attendance sheets for Exam: {exam.name} ({exam.session})")

        # ── Semester variants extraction (aligned with pdf_generator.py) ────────
        _roman_str_to_int = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
        }
        ey = str(exam.year) if exam.year else ""
        sem_variants_int = set()
        if ey.isdigit():
            sem_variants_int.add(int(ey))
        if exam.name:
            roman_m = re.search(r'\b(?:SEM|SEMESTER)[-\s]*(I{1,3}|IV|VI{0,3}|IX|X)\b', exam.name, re.IGNORECASE)
            if roman_m:
                rn = roman_m.group(1).upper()
                if rn in _roman_str_to_int:
                    sem_variants_int.add(_roman_str_to_int[rn])
            digit_m = re.search(r'(?<!\d)([1-8])(?!\d)', exam.name)
            if digit_m:
                sem_variants_int.add(int(digit_m.group(1)))
        
        sem_variants_int = list(sem_variants_int)
        is_year_range = bool(re.match(r'^\d{4}-\d{2,4}$', exam.session or ''))

        # ── Build Registration Filters ──────────────────────────────────────────
        filters = {
            'status': 'REGISTERED',
        }
        
        if sem_variants_int:
            # Filter primarily by semester. 
            # We don't strictly match session because registrations for the same exam
            # might have different sessions (e.g. 2024-25 vs 2025-26).
            filters['sem__in'] = sem_variants_int
        elif is_year_range:
            filters['session'] = exam.session
        
        if college_uids:
            colleges_found = College.objects.filter(uid__in=college_uids)
            if colleges_found.count() != len(college_uids):
                found_uids = set(map(str, colleges_found.values_list('uid', flat=True)))
                missing = set(college_uids) - found_uids
                self.stdout.write(self.style.WARNING(f"Warning: Some college UIDs not found: {missing}"))
            
            if not colleges_found.exists():
                raise CommandError("None of the specified college UIDs were found.")
            
            filters['student__college__in'] = colleges_found

        self.stdout.write(f"DEBUG: Search filters: {filters}")

        # Find colleges with matching registrations
        college_ids = PGExamRegistration.objects.filter(**filters).values_list('student__college_id', flat=True).distinct()
        colleges = College.objects.filter(id__in=college_ids)
        total_colleges = colleges.count()

        if total_colleges == 0:
            self.stdout.write(self.style.WARNING("No registered students found matching the exam's semester and session."))
            return

        self.stdout.write(f"Found {total_colleges} colleges with registrations.")

        for college in colleges:
            self.stdout.write(f"\nProcessing College: {college.name} ({college.college_code})")
            
            # Find departments for this college/exam
            dept_filters = filters.copy()
            dept_filters['student__college'] = college
            
            if dept_uids:
                depts_found = PGDepartment.objects.filter(uid__in=dept_uids)
                if not depts_found.exists():
                    self.stdout.write(self.style.WARNING(f"  - No matching departments found for this college among specified UIDs."))
                    continue
                dept_filters['student__department__in'] = depts_found

            dept_ids = PGExamRegistration.objects.filter(**dept_filters).values_list('student__department_id', flat=True).distinct()
            departments = PGDepartment.objects.filter(id__in=dept_ids)
            
            if not departments.exists():
                # Check for registrations without a department
                # Or just try one generation for the college as "General" if no depts found
                self.process_generation(exam, college, None, output_dir)
            else:
                for dept in departments:
                    self.process_generation(exam, college, dept, output_dir)

        self.stdout.write(self.style.SUCCESS(f"\nBatch generation complete! Files saved in: {output_dir}"))

    def process_generation(self, exam, college, department, output_dir):
        dept_name = department.name if department else "General"
        self.stdout.write(f"  - Generating for Department: {dept_name}...")
        
        try:
            pdf_content = generate_pg_attendance_sheet_pdf(exam, college, department=department)
            
            if pdf_content:
                safe_college = "".join(c if c.isalnum() else "_" for c in college.name)
                safe_dept = "".join(c if c.isalnum() else "_" for c in dept_name)
                filename = f"Attendance_Sheet_{safe_college}_{safe_dept}.pdf"
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(pdf_content)
                
                self.stdout.write(self.style.SUCCESS(f"    Saved: {filename}"))
            else:
                self.stdout.write(self.style.WARNING(f"    No students returned by generator for {dept_name}."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error generating PDF for {dept_name}: {str(e)}"))
