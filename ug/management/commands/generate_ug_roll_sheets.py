import os
import logging
import traceback
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ug.models import UGExam, ExamRegistration, UGDepartment, UGExamCenterMapping
from colleges.models import College
from ug.utils.roll_sheet_pdf import generate_ug_roll_sheet_pdf, generate_ug_roll_sheet_excel

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate UG Roll Sheets (PDF & Excel) organized by Exam Centers.'

    def add_arguments(self, parser):
        parser.add_argument('--exam-uid', type=str, required=True, help='UID of the UG Exam')
        parser.add_argument('--output-dir', type=str, default='ug_roll_sheets_automated', help='Base directory to save files')

    def handle(self, *args, **options):
        exam_uid = options['exam_uid']
        output_dir = options['output_dir']

        if not os.path.isabs(output_dir):
            output_dir = os.path.join(settings.BASE_DIR, output_dir)
        
        try:
            exam = UGExam.objects.get(uid=exam_uid)
        except UGExam.DoesNotExist:
            raise CommandError(f"UGExam with UID {exam_uid} does not exist.")

        self.stdout.write(f"Starting Roll Sheet generation for: {exam.name} ({exam.session})")

        # 1. Get all unique colleges that have active registrations for this exam
        from ug.utils.roll_sheet_pdf import get_sem_integer
        sem_int = get_sem_integer(exam.semester)
        session_str = str(exam.session or "").strip()

        active_college_ids = ExamRegistration.objects.filter(
            sem=sem_int,
            session__iexact=session_str,
            status='REGISTERED'
        ).values_list('student__college_id', flat=True).distinct()

        colleges = College.objects.filter(id__in=active_college_ids).order_by('name')
        
        if not colleges.exists():
            self.stdout.write(self.style.WARNING("No active registrations found for this exam."))
            return

        for college in colleges:
            college_name = "".join(c if c.isalnum() else "_" for c in college.name)
            college_path = os.path.join(output_dir, college_name)
            
            if not os.path.exists(college_path):
                os.makedirs(college_path)

            self.stdout.write(self.style.SUCCESS(f"\nProcessing College: {college.name}"))
            self.generate_files(exam, college, college_path)

        self.stdout.write(self.style.SUCCESS(f"\nAll Roll Sheets generated in: {output_dir}"))

    def generate_files(self, exam, college, base_path):
        safe_college = "".join(c if c.isalnum() else "_" for c in college.name)
        
        # 1. Generate PDF
        try:
            pdf_content = generate_ug_roll_sheet_pdf(exam, college, department_uid=None)
            if pdf_content:
                pdf_filename = f"Roll_Sheet_{safe_college}.pdf"
                with open(os.path.join(base_path, pdf_filename), 'wb') as f:
                    f.write(pdf_content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      PDF Error: {str(e)}"))

        # 2. Generate Excel
        try:
            excel_content = generate_ug_roll_sheet_excel(exam, college, department_uid=None)
            if excel_content:
                excel_filename = f"Roll_Sheet_{safe_college}.xlsx"
                with open(os.path.join(base_path, excel_filename), 'wb') as f:
                    f.write(excel_content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Excel Error: {str(e)}"))
