import os
import re
import logging
import traceback
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pg.models import PGExam, PGExamRegistration, PGDepartment
from colleges.models import College
from pg.utils.pg305_306_pdf_generator import generate_pg305_306_attendance_pdf

logger = logging.getLogger(__name__)


"""
Generate Attendance Sheets for PG106 paper code only

Usage:
python manage.py generate_pg106_attendance_sheets --exam-uid ba082de1-32fb-4c6a-b5b6-4facdc678f48
python manage.py generate_pg106_attendance_sheets --exam-uid 10f3ea2b-675b-4c5d-baf6-017ef4b6b0de
python manage.py generate_pg106_attendance_sheets --exam-uid <exam-uid> --registration-no <reg-no>
python manage.py generate_pg106_attendance_sheets --exam-uid <exam-uid> --college-uid <college-uid1> <college-uid2>
"""

class Command(BaseCommand):
    help = 'Generate PG Attendance Sheets for PG106 paper code only'

    def add_arguments(self, parser):
        parser.add_argument('--exam-uid', type=str, required=True, help='UID of the PG Exam')
        parser.add_argument('--college-uid', nargs='+', help='Optional: One or more UIDs of specific Colleges')
        parser.add_argument('--department-uid', nargs='+', help='Optional: One or more UIDs of specific Departments')
        parser.add_argument('--registration-no', type=str, help='Optional: Registration Number for single student generation')
        parser.add_argument('--output-dir', type=str, default='pg106_attendance_sheets', help='Directory to save generated PDFs')

    def handle(self, *args, **options):
        exam_uid = options['exam_uid']
        college_uids = options.get('college_uid') or []
        dept_uids = options.get('department_uid') or []
        registration_no = options.get('registration_no')
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

        self.stdout.write(f"Generating PG306 attendance sheets for Exam: {exam.name} ({exam.session})")

        # ── Build Registration Filters (PG305/PG306 filtering via course enrollment) ──
        filters = {
            'exam': exam,
            'status': 'REGISTERED',
        }
        
        if registration_no:
            filters['student__registration_no'] = registration_no
        
        if college_uids:
            colleges_found = College.objects.filter(uid__in=college_uids)
            if colleges_found.count() != len(college_uids):
                found_uids = set(map(str, colleges_found.values_list('uid', flat=True)))
                missing = set(college_uids) - found_uids
                self.stdout.write(self.style.WARNING(f"Warning: Some college UIDs not found: {missing}"))
            
            if not colleges_found.exists():
                raise CommandError("None of the specified college UIDs were found.")
            
            filters['student__college__in'] = colleges_found

        # Get all registrations first
        all_regs = PGExamRegistration.objects.filter(**filters)
        
        # Filter students by paper code (PG305 for Music, PG306 for others)
        from pg.models import PGStudentCourseAssessment
        
        # Get Music department
        music_dept = PGDepartment.objects.filter(name__icontains='Music').first()
        
        # Get PG305 students (Music department)
        pg305_filter = {'paper_code': 'PG305'}
        if music_dept:
            pg305_filter['department'] = music_dept
        
        pg305_student_ids = set(PGStudentCourseAssessment.objects.filter(
            **pg305_filter
        ).values_list('student_id', flat=True).distinct())
        
        # Get PG306 students (Non-Music departments)
        pg306_filter = {'paper_code': 'PG306'}
        if music_dept:
            # Exclude Music department from PG306
            pg306_student_ids = set(PGStudentCourseAssessment.objects.filter(
                **pg306_filter
            ).exclude(department=music_dept).values_list('student_id', flat=True).distinct())
        else:
            pg306_student_ids = set(PGStudentCourseAssessment.objects.filter(
                **pg306_filter
            ).values_list('student_id', flat=True).distinct())
        
        # Combine both sets
        target_student_ids = pg305_student_ids | pg306_student_ids
        
        # Filter registrations to only target students
        target_regs = all_regs.filter(student_id__in=target_student_ids)
        
        self.stdout.write(f"DEBUG: Found {len(pg305_student_ids)} PG305 students (Music)")
        self.stdout.write(f"DEBUG: Found {len(pg306_student_ids)} PG306 students (Non-Music)")
        self.stdout.write(f"DEBUG: Total {target_regs.count()} registrations")

        # Find colleges with matching PG305/PG306 registrations
        college_ids = target_regs.values_list('student__college_id', flat=True).distinct()
        colleges = College.objects.filter(id__in=college_ids)
        total_colleges = colleges.count()

        if total_colleges == 0:
            self.stdout.write(self.style.WARNING("No PG305/PG306 registered students found matching the criteria."))
            return

        self.stdout.write(f"Found {total_colleges} colleges with PG305/PG306 registrations.")

        try:
            for college in colleges:
                self.stdout.write(f"\nProcessing College: {college.name} ({college.college_code})")
                
                # Find departments for this college/exam with PG106
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
                    self.process_generation(exam, college, None, output_dir, registration_no, pg305_student_ids, pg306_student_ids)
                else:
                    for dept in departments:
                        self.process_generation(exam, college, dept, output_dir, registration_no, pg305_student_ids, pg306_student_ids)
        except Exception as e:
            logger.error(f"Critical error in PG106 batch generation: {str(e)}")
            logger.error(traceback.format_exc())
            self.stdout.write(self.style.ERROR(f"\nCritical error occurred: {str(e)}"))
            self.stdout.write("Check server logs for full traceback.")

        self.stdout.write(self.style.SUCCESS(f"\nPG106 batch generation complete! Files saved in: {output_dir}"))

    def process_generation(self, exam, college, department, output_dir, registration_no=None, pg305_student_ids=None, pg306_student_ids=None):
        dept_name = department.name if department else "General"
        
        # Determine paper code based on department
        is_music = department and 'MUSIC' in department.name.upper()
        paper_code = 'PG305' if is_music else 'PG306'
        student_ids_filter = pg305_student_ids if is_music else pg306_student_ids
        
        self.stdout.write(f"  - Generating {paper_code} for Department: {dept_name}...")
        
        try:
            # Use new PG305/306 PDF generator with 4 students per page
            pdf_content = generate_pg305_306_attendance_pdf(
                exam=exam,
                college=college,
                department=department,
                paper_code=paper_code,
                student_ids_filter=student_ids_filter
            )
            
            if pdf_content:
                safe_college = "".join(c if c.isalnum() else "_" for c in college.name)
                safe_dept = "".join(c if c.isalnum() else "_" for c in dept_name)
                
                if registration_no:
                    safe_reg = registration_no.replace("/", "_")
                    filename = f"{paper_code}_Attendance_Sheet_{safe_reg}.pdf"
                else:
                    filename = f"{paper_code}_Attendance_Sheet_{safe_college}_{safe_dept}.pdf"
                
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(pdf_content)
                
                self.stdout.write(self.style.SUCCESS(f"    Saved: {filename}"))
            else:
                self.stdout.write(self.style.WARNING(f"    No {paper_code} students returned by generator for {dept_name}."))
        except Exception as e:
            logger.error(f"Error generating {paper_code} PDF for College: {college.name}, Dept: {dept_name}. Error: {str(e)}")
            logger.error(traceback.format_exc())
            self.stdout.write(self.style.ERROR(f"    Error generating {paper_code} PDF for {dept_name}: {str(e)}"))
