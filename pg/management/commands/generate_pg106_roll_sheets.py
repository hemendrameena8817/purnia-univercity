import os
import re
import logging
import traceback
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pg.models import PGExam, PGExamRegistration, PGDepartment
from colleges.models import College
from pg.utils.pdf_generator import generate_pg_roll_sheet_pdf

logger = logging.getLogger(__name__)


"""
Generate Roll Sheets for PG106 paper code only

Usage:
python manage.py generate_pg106_roll_sheets --exam-uid <exam-uid>
python manage.py generate_pg106_roll_sheets --exam-uid <exam-uid> --registration-no <reg-no>
python manage.py generate_pg106_roll_sheets --exam-uid <exam-uid> --college-uid <college-uid1> <college-uid2>
"""

class Command(BaseCommand):
    help = 'Generate PG Roll Sheets for PG106 paper code only'

    def add_arguments(self, parser):
        parser.add_argument('--exam-uid', type=str, required=True, help='UID of the PG Exam')
        parser.add_argument('--college-uid', nargs='+', help='Optional: One or more UIDs of specific Colleges')
        parser.add_argument('--department-uid', nargs='+', help='Optional: One or more UIDs of specific Departments')
        parser.add_argument('--registration-no', type=str, help='Optional: Registration Number for single student generation')
        parser.add_argument('--output-dir', type=str, default='pg106_roll_sheets', help='Directory to save generated PDFs')

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

        self.stdout.write(f"Generating PG306 roll sheets for Exam: {exam.name} ({exam.session})")

        # Base filters (PG306 filtering will be done via course enrollment)
        filters = {
            'exam': exam,
            'status': 'REGISTERED',
        }
        
        if registration_no:
            filters['student__registration_no'] = registration_no
        
        if college_uids:
            colleges_found = College.objects.filter(uid__in=college_uids)
            filters['student__college__in'] = colleges_found

        # Get all registrations first
        all_regs = PGExamRegistration.objects.filter(**filters)
        
        # Filter students by paper code (PG305 for Music, PG306 for others)
        from pg.models import PGStudentCourseAssessment
        
        # Get both PG305 and PG306 students
        pg305_student_ids = set(PGStudentCourseAssessment.objects.filter(
            paper_code='PG305'
        ).values_list('student_id', flat=True).distinct())
        
        pg306_student_ids = set(PGStudentCourseAssessment.objects.filter(
            paper_code='PG306'
        ).values_list('student_id', flat=True).distinct())
        
        # Combine both sets
        target_student_ids = pg305_student_ids | pg306_student_ids
        
        # Filter registrations to only target students
        target_regs = all_regs.filter(student_id__in=target_student_ids)
        
        self.stdout.write(f"DEBUG: Found {len(pg305_student_ids)} PG305 students (Music)")
        self.stdout.write(f"DEBUG: Found {len(pg306_student_ids)} PG306 students (Non-Music)")
        self.stdout.write(f"DEBUG: Total {target_regs.count()} registrations")

        college_ids = target_regs.values_list('student__college_id', flat=True).distinct()
        colleges = College.objects.filter(id__in=college_ids)

        if not colleges.exists():
            self.stdout.write(self.style.WARNING("No PG305/PG306 registered students found matching the criteria."))
            return

        self.stdout.write(f"Found {colleges.count()} colleges with PG305/PG306 registrations.")

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
                self.process_generation(exam, college, None, output_dir, registration_no)
            else:
                for dept in departments:
                    self.process_generation(exam, college, dept, output_dir, registration_no)

        self.stdout.write(self.style.SUCCESS(f"\nPG106 Roll Sheet generation complete! Files saved in: {output_dir}"))

    def process_generation(self, exam, college, department, output_dir, registration_no=None):
        dept_name = department.name if department else "General"
        self.stdout.write(f"  - Generating PG106 for Department: {dept_name}...")
        
        try:
            # Pass paper_code filter to the PDF generator
            pdf_content = generate_pg_roll_sheet_pdf(
                exam, 
                college, 
                department=department, 
                registration_no=registration_no,
                paper_code='PG106'  # Filter for PG106
            )
            
            if pdf_content:
                safe_college = "".join(c if c.isalnum() else "_" for c in college.name)
                safe_dept = "".join(c if c.isalnum() else "_" for c in dept_name)
                
                if registration_no:
                    safe_reg = registration_no.replace("/", "_")
                    filename = f"PG106_Roll_Sheet_{safe_reg}.pdf"
                else:
                    filename = f"PG106_Roll_Sheet_{safe_college}_{safe_dept}.pdf"
                
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(pdf_content)
                self.stdout.write(self.style.SUCCESS(f"    Saved: {filename}"))
            else:
                self.stdout.write(self.style.WARNING(f"    No PG106 students found for {dept_name}."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error generating PG106 PDF for {dept_name}: {str(e)}"))
            logger.error(traceback.format_exc())
