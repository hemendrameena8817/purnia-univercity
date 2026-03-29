import os
import logging
import traceback
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ug.models import UGExam, ExamRegistration, UGDepartment
from colleges.models import College
from ug.utils.attendance_sheet_pdf import generate_ug_attendance_sheet_pdf
from ug.utils.roll_sheet_pdf import get_sem_integer

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate UG Attendance Sheets in batch for all colleges and departments associated with an exam.'

    def add_arguments(self, parser):
        parser.add_argument('--exam-uid', type=str, required=True, help='UID of the UG Exam')
        parser.add_argument('--college-uid', nargs='+', help='Optional: One or more UIDs of specific Colleges')
        parser.add_argument('--department-uid', nargs='+', help='Optional: One or more UIDs of specific Departments (MJC)')
        parser.add_argument('--registration-no', type=str, help='Optional: Registration Number for single student generation')
        parser.add_argument('--output-dir', type=str, default='ug_attendance_sheets', help='Directory to save generated PDFs')

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

        try:
            exam = UGExam.objects.get(uid=exam_uid)
        except UGExam.DoesNotExist:
            raise CommandError(f"UGExam with UID {exam_uid} does not exist.")

        self.stdout.write(f"Generating UG attendance sheets for Exam: {exam.name} ({exam.session})")

        sem_int = get_sem_integer(exam.semester)
        session_str = str(exam.session or "").strip()

        filters = {
            'exam': exam,
            'status': 'REGISTERED',
        }
        if sem_int: filters['sem'] = sem_int
        if session_str: filters['session__iexact'] = session_str
        
        if registration_no:
            filters['student__registration_no'] = registration_no
        
        if college_uids:
            colleges_found = College.objects.filter(uid__in=college_uids)
            filters['student__college__in'] = colleges_found

        # Find colleges with matching registrations
        college_ids = ExamRegistration.objects.filter(**filters).values_list('student__college_id', flat=True).distinct()
        colleges = College.objects.filter(id__in=college_ids).order_by('name')

        if not colleges.exists():
            self.stdout.write(self.style.WARNING("No registered students found matching the criteria."))
            return

        for college in colleges:
            self.stdout.write(f"\nProcessing College: {college.name}")
            self.process_generation(exam, college, output_dir, registration_no)

        self.stdout.write(self.style.SUCCESS(f"\nBatch generation complete! Files saved in: {output_dir}"))

    def process_generation(self, exam, college, output_dir, registration_no=None):
        self.stdout.write(f"  - Generating for College: {college.name}...")
        
        try:
            pdf_content = generate_ug_attendance_sheet_pdf(
                exam, college, registration_no=registration_no
            )
            
            if pdf_content:
                safe_college = "".join(c if c.isalnum() else "_" for c in college.name)
                
                if registration_no:
                    safe_reg = registration_no.replace("/", "_")
                    filename = f"Attendance_Sheet_{safe_reg}.pdf"
                else:
                    filename = f"Attendance_Sheet_{safe_college}.pdf"
                
                file_path = os.path.join(output_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(pdf_content)
                self.stdout.write(self.style.SUCCESS(f"    Saved: {filename}"))
            else:
                self.stdout.write(self.style.WARNING(f"    No students returned for {college.name}."))
        except Exception as e:
            logger.error(f"Error generating PDF for {college.name}: {str(e)}")
            self.stdout.write(self.style.ERROR(f"    Error: {str(e)}"))
