from django.core.management.base import BaseCommand
from pgoldresult.models import PGOldStudentProfile, College
from django.contrib.auth import get_user_model
import csv
import json

class Command(BaseCommand):
    help = 'Simple import PGOldStudentProfile data'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='CSV file path')
        parser.add_argument('--dry-run', action='store_true', help='Test without importing')
        parser.add_argument('--create-users', action='store_true', help='Create user accounts')

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        create_users = options['create_users']
        
        User = get_user_model()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                imported = 0
                updated = 0
                errors = 0
                
                for row in reader:
                    try:
                        # Handle college
                        college = None
                        college_id = row.get('college_id', '')
                        college_code = row.get('college_code', '')
                        college_name = row.get('college_name', '')
                        
                        if college_id:
                            college = College.objects.filter(id=college_id).first()
                        elif college_code:
                            college = College.objects.filter(college_code=college_code).first()
                        elif college_name:
                            college = College.objects.filter(name=college_name).first()
                        
                        # Check if profile exists
                        profile = None
                        if row.get('registration_no'):
                            profile = PGOldStudentProfile.objects.filter(registration_no=row['registration_no']).first()
                        elif row.get('roll_no'):
                            profile = PGOldStudentProfile.objects.filter(roll_no=row['roll_no']).first()
                        
                        if profile:
                            # Update existing
                            profile.student_name = row.get('student_name', profile.student_name)
                            profile.student_name_hindi = row.get('student_name_hindi', profile.student_name_hindi)
                            profile.fathers_name = row.get('fathers_name', profile.fathers_name)
                            profile.mothers_name = row.get('mothers_name', profile.mothers_name)
                            profile.gender = row.get('gender', profile.gender)
                            profile.dob = row.get('dob', profile.dob)
                            profile.college = college
                            profile.course_code = row.get('course_code', profile.course_code)
                            profile.discipline_code = row.get('discipline_code', profile.discipline_code)
                            profile.batch_code = row.get('batch_code', profile.batch_code)
                            profile.current_semester = row.get('current_semester', profile.current_semester)
                            profile.pg_faculty = row.get('pg_faculty', profile.pg_faculty)
                            profile.pg_department = row.get('pg_department', profile.pg_department)
                            profile.pg_degree = row.get('pg_degree', profile.pg_degree)
                            profile.pg_program = row.get('pg_program', profile.pg_program)
                            profile.source_user_id = row.get('source_user_id', profile.source_user_id)
                            profile.is_active = row.get('is_active', profile.is_active)
                            
                            if not dry_run:
                                profile.save()
                            updated += 1
                            
                        else:
                            # Create new
                            if not dry_run:
                                profile = PGOldStudentProfile.objects.create(
                                    uid=row.get('uid', ''),
                                    registration_no=row.get('registration_no', ''),
                                    roll_no=row.get('roll_no', ''),
                                    student_name=row.get('student_name', ''),
                                    student_name_hindi=row.get('student_name_hindi', ''),
                                    fathers_name=row.get('fathers_name', ''),
                                    mothers_name=row.get('mothers_name', ''),
                                    gender=row.get('gender', ''),
                                    dob=row.get('dob', ''),
                                    college=college,
                                    course_code=row.get('course_code', ''),
                                    discipline_code=row.get('discipline_code', ''),
                                    batch_code=row.get('batch_code', ''),
                                    current_semester=row.get('current_semester', ''),
                                    pg_faculty=row.get('pg_faculty', ''),
                                    pg_department=row.get('pg_department', ''),
                                    pg_degree=row.get('pg_degree', ''),
                                    pg_program=row.get('pg_program', ''),
                                    final_result=row.get('final_result', ''),
                                    gpa=row.get('gpa', ''),
                                    cgpa=row.get('cgpa', ''),
                                    total_percentage=row.get('total_percentage', ''),
                                    source_user_id=row.get('source_user_id', ''),
                                    is_active=row.get('is_active', 'True') == 'True'
                                )
                                
                                # Create user if requested
                                if create_users and profile.registration_no:
                                    if not User.objects.filter(username=profile.registration_no).exists():
                                        user = User.objects.create_user(
                                            username=profile.registration_no,
                                            email=f"{profile.registration_no}@student.edu",
                                            first_name=profile.student_name.split()[0] if profile.student_name else '',
                                            last_name=' '.join(profile.student_name.split()[1:]) if profile.student_name and len(profile.student_name.split()) > 1 else '',
                                        )
                                        profile.user = user
                                        profile.save()
                            
                            imported += 1
                    
                    except Exception as e:
                        errors += 1
                        self.stdout.write(
                            self.style.ERROR(f'Error processing row: {str(e)}')
                        )
                
                action = "DRY RUN: " if dry_run else ""
                self.stdout.write(
                    self.style.SUCCESS(f'{action}Imported: {imported} new, {updated} updated, {errors} errors')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Import failed: {str(e)}')
            )
