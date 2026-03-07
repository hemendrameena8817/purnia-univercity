import os
import re
import logging
import traceback
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pg.models import PGExam, PGExamRegistration, PGDepartment
from colleges.models import College
from pg.utils.excel_generator import generate_pg_tsi_excel
# python manage.py generate_pg_roll_sheets_excel --exam-uid ba082de1-32fb-4c6a-b5b6-4facdc678f48 --output-dir my_roll_sheets
# # Generate TSI in Excel
# python manage.py generate_pg_tsi --exam-uid <EXAM_UID> --output-dir my_tsi

# Comment
# Ctrl+Alt+M
# 
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate PG TSI (Tabulation Sheet I) in Excel format for all colleges and departments associated with an exam.'

    def add_arguments(self, parser):
        parser.add_argument('--exam-uid', type=str, required=True, help='UID of the PG Exam')
        parser.add_argument('--college-uid', nargs='+', help='Optional: One or more UIDs of specific Colleges')
        parser.add_argument('--department-uid', nargs='+', help='Optional: One or more UIDs of specific Departments')
        parser.add_argument('--registration-no', type=str, help='Optional: Registration Number for single student generation')
        parser.add_argument('--output-dir', type=str, default='tsi_excel', help='Directory to save generated Excel files')

    def handle(self, *args, **options):
        exam_uid = options['exam_uid']
        college_uids = options.get('college_uid') or []
        dept_uids = options.get('department_uid') or []
        registration_no = options.get('registration_no')
        output_dir = options['output_dir']

        if not os.path.isabs(output_dir):
            output_dir = os.path.join(settings.BASE_DIR, output_dir)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.stdout.write(self.style.SUCCESS(f"Created directory: {output_dir}"))

        try:
            exam = PGExam.objects.get(uid=exam_uid)
        except PGExam.DoesNotExist:
            raise CommandError(f"PGExam with UID {exam_uid} does not exist.")

        self.stdout.write(f"Generating TSI Excel for Exam: {exam.name} ({exam.session})")

        # ── Semester variants extraction ────────
        _roman_str_to_int = { 'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10 }
        ey = str(exam.year) if exam.year else ""
        sem_variants_int = set()
        if ey.isdigit(): sem_variants_int.add(int(ey))
        if exam.name:
            roman_m = re.search(r'\b(?:SEM|SEMESTER)[-\s]*(I{1,3}|IV|VI{0,3}|IX|X)\b', exam.name, re.IGNORECASE)
            if roman_m:
                rn = roman_m.group(1).upper()
                if rn in _roman_str_to_int: sem_variants_int.add(_roman_str_to_int[rn])
            digit_m = re.search(r'(?<!\d)([1-8])(?!\d)', exam.name)
            if digit_m: sem_variants_int.add(int(digit_m.group(1)))
        
        sem_variants_int = list(sem_variants_int)
        is_year_range = bool(re.match(r'^\d{4}-\d{2,4}$', exam.session or ''))

        filters = {'status': 'REGISTERED'}
        if sem_variants_int: filters['sem__in'] = sem_variants_int
        elif is_year_range: filters['session'] = exam.session
        
        if registration_no:
            filters['student__registration_no'] = registration_no
        
        if college_uids:
            colleges_found = College.objects.filter(uid__in=college_uids)
            filters['student__college__in'] = colleges_found

        college_ids = PGExamRegistration.objects.filter(**filters).values_list('student__college_id', flat=True).distinct()
        colleges = College.objects.filter(id__in=college_ids)

        for college in colleges:
            self.stdout.write(f"\nProcessing College: {college.name} ({college.college_code})")
            
            dept_filters = filters.copy()
            dept_filters['student__college'] = college
            
            if dept_uids:
                depts_found = PGDepartment.objects.filter(uid__in=dept_uids)
                dept_filters['student__department__in'] = depts_found

            dept_ids = PGExamRegistration.objects.filter(**dept_filters).values_list('student__department_id', flat=True).distinct()
            departments = list(PGDepartment.objects.filter(id__in=dept_ids))
            
            if not departments:
                self.process_generation(exam, college, None, output_dir)
            else:
                for dept in departments:
                    self.process_generation(exam, college, dept, output_dir, registration_no)

        self.stdout.write(self.style.SUCCESS(f"\nTSI generation complete! Files saved in: {output_dir}"))

    def process_generation(self, exam, college, department, output_dir, registration_no=None):
        dept_name = department.name if department else "General"
        self.stdout.write(f"  - Generating for Department: {dept_name}...")
        
        try:
            xlsx_content = generate_pg_tsi_excel(exam, college, department=department, registration_no=registration_no)
            if xlsx_content:
                safe_college = "".join(c if c.isalnum() else "_" for c in college.name)
                safe_dept = "".join(c if c.isalnum() else "_" for c in dept_name)
                
                if registration_no:
                    safe_reg = registration_no.replace("/", "_")
                    filename = f"TSI_{safe_reg}.xlsx"
                else:
                    filename = f"TSI_{safe_college}_{safe_dept}.xlsx"
                
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(xlsx_content)
                self.stdout.write(self.style.SUCCESS(f"    Saved: {filename}"))
            else:
                self.stdout.write(self.style.WARNING(f"    No students found for {dept_name}."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error generating TSI for {dept_name}: {str(e)}"))
            logger.error(traceback.format_exc())
