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
python manage.py generate_pg106_roll_sheets --exam-uid ba082de1-32fb-4c6a-b5b6-4facdc678f48
python manage.py generate_pg106_roll_sheets --exam-uid 10f3ea2b-675b-4c5d-baf6-017ef4b6b0de

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

        self.stdout.write(f"Generating null-date subject roll sheets for Exam: {exam.name} ({exam.session})")

        filters = {
            'exam': exam,
            'status': 'REGISTERED',
        }

        if registration_no:
            filters['student__registration_no'] = registration_no

        if college_uids:
            colleges_found = College.objects.filter(uid__in=college_uids)
            if not colleges_found.exists():
                raise CommandError("None of the specified college UIDs were found.")
            filters['student__college__in'] = colleges_found

        from pg.models import PGStudentCourseAssessment, PGExamSchedule

        # Get all registrations for this exam
        all_regs = PGExamRegistration.objects.filter(**filters)
        exam_student_ids = list(all_regs.values_list('student_id', flat=True).distinct())

        # Find course codes whose exam_date is NULL in PGExamSchedule for this exam
        null_date_course_codes = set(
            PGExamSchedule.objects.filter(exam=exam, exam_date__isnull=True)
            .exclude(common_course_structure=None)
            .values_list('common_course_structure__course_code', flat=True)
            .distinct()
        )
        self.stdout.write(f"Null-date course codes: {sorted(null_date_course_codes)}")

        if not null_date_course_codes:
            self.stdout.write(self.style.WARNING("No null exam_date schedules found for this exam."))
            return

        # Find registered students enrolled in those null-date course codes
        target_student_ids = set(
            PGStudentCourseAssessment.objects.filter(
                student_id__in=exam_student_ids,
                course_code__in=null_date_course_codes
            ).values_list('student_id', flat=True).distinct()
        )
        self.stdout.write(f"Target students with null-date subjects: {len(target_student_ids)}")

        if not target_student_ids:
            self.stdout.write(self.style.WARNING("No registered students found with null-date subjects."))
            return

        # Find colleges with matching registrations
        college_ids = all_regs.filter(student_id__in=target_student_ids).values_list('student__college_id', flat=True).distinct()
        colleges = list(College.objects.filter(id__in=college_ids))

        if not colleges:
            self.stdout.write(self.style.WARNING("No colleges found with matching students."))
            return

        self.stdout.write(f"Found {len(colleges)} colleges.")

        for college in colleges:
            self.stdout.write(f"\nProcessing College: {college.name} ({college.college_code})")

            dept_filters = filters.copy()
            dept_filters['student__college'] = college

            if dept_uids:
                depts_found = PGDepartment.objects.filter(uid__in=dept_uids)
                dept_filters['student__department__in'] = depts_found

            dept_filters['student_id__in'] = list(target_student_ids)
            dept_ids = PGExamRegistration.objects.filter(**dept_filters).values_list('student__department_id', flat=True).distinct()
            departments = list(PGDepartment.objects.filter(id__in=dept_ids))

            if not departments:
                self.process_generation(exam, college, None, output_dir, registration_no, target_student_ids)
            else:
                for dept in departments:
                    self.process_generation(exam, college, dept, output_dir, registration_no, target_student_ids)

        self.stdout.write(self.style.SUCCESS(f"\nPG106 Roll Sheet generation complete! Files saved in: {output_dir}"))

    def process_generation(self, exam, college, department, output_dir, registration_no=None, target_student_ids=None):
        dept_name = department.name if department else "General"
        is_music = department and 'MUSIC' in department.name.upper()
        paper_code = 'PG305' if is_music else 'PG306'

        self.stdout.write(f"  - Generating {paper_code} Roll Sheet for Department: {dept_name}...")

        try:
            pdf_content = generate_pg_roll_sheet_pdf(
                exam=exam,
                college=college,
                department=department,
                registration_no=registration_no,
                allowed_student_ids=target_student_ids
            )

            if pdf_content:
                safe_college = "".join(c if c.isalnum() else "_" for c in college.name)
                safe_dept = "".join(c if c.isalnum() else "_" for c in dept_name)
                if registration_no:
                    safe_reg = registration_no.replace("/", "_")
                    filename = f"{paper_code}_Roll_Sheet_{safe_reg}.pdf"
                else:
                    filename = f"{paper_code}_Roll_Sheet_{safe_college}_{safe_dept}.pdf"
                file_path = os.path.join(output_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(pdf_content)
                self.stdout.write(self.style.SUCCESS(f"    Saved: {filename}"))
            else:
                self.stdout.write(self.style.WARNING(f"    No students found for {dept_name}."))
        except Exception as e:
            logger.error(f"Error generating {paper_code} PDF for College: {college.name}, Dept: {dept_name}. Error: {str(e)}")
            logger.error(traceback.format_exc())
            self.stdout.write(self.style.ERROR(f"    Error generating {paper_code} PDF for {dept_name}: {str(e)}"))
