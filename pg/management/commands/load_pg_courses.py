import pandas as pd
from django.core.management.base import BaseCommand
from pg.models import PGCommonCourseStructure, PGDepartment
# /home/gaurav/.pyenv/versions/pup-umis/bin/python manage.py load_pg_courses
class Command(BaseCommand):
    help = 'Load PG Course Structure from ODS file'

    def handle(self, *args, **kwargs):
        file_path = 'courses_data/pg/structureofcourse.ods'
        try:
            df = pd.read_excel(file_path, engine='odf')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(f"Found {len(df)} rows. Starting import...")

        # Columns expected: 
        # Faculty, Semester, Course Code, Department, Course Name, Total Credits, 
        # Credits2, Theory Max Marks, Theory Min Marks, C.I.A Max Marks, C.I.Amin Marks.1, Paper Code

        for index, row in df.iterrows():
            course_name = row.get('Course Name')
            course_code = row.get('Course Code')
            semester_val = row.get('Semester')
            dept_name = row.get('Department')
            
            # Sanitization
            if pd.isna(course_name) or pd.isna(course_code):
                continue
            
            # Semester mapping
            semester_map = {
                1: '1ST', '1': '1ST', 
                2: '2ND', '2': '2ND',
                3: '3RD', '3': '3RD',
                4: '4TH', '4': '4TH'
            }
            semester = semester_map.get(semester_val, str(semester_val))

            # Helper to safely convert to int
            def safe_int(val):
                try:
                    if pd.isna(val): return 0
                    return int(float(val))
                except (ValueError, TypeError):
                    return 0

            credits = safe_int(row.get('Total Credits'))
            cia_marks = safe_int(row.get('C.I.A Max Marks'))
            ese_marks = safe_int(row.get('Theory Max Marks'))

            # Total marks
            total_marks = cia_marks + ese_marks

            # Create or Update Course, updating ONLY requested fields
            # User requested: departments, semester, course_code, cia_marks, ese_marks, marks
            course, created = PGCommonCourseStructure.objects.update_or_create(
                course_code=course_code,
                semester=semester,
                defaults={
                    'cia_marks': int(cia_marks),
                    'ese_marks': int(ese_marks),
                    'marks': total_marks,
                }
            )

            # Handle Department
            if dept_name and not pd.isna(dept_name):
                dept_name = str(dept_name).strip()
                department = PGDepartment.objects.filter(name__iexact=dept_name).first()
                if department:
                    course.departments.add(department)
                else:
                    self.stdout.write(self.style.WARNING(f"Department not found: {dept_name} for course {course_code}"))
            
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action}: {course_code} - {course_name}")

        self.stdout.write(self.style.SUCCESS('Successfully imported PG courses.'))
