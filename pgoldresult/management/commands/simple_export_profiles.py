from django.core.management.base import BaseCommand
from pgoldresult.models import PGOldStudentProfile
import csv
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Simple export PGOldStudentProfile data'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=f'pg_profiles_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')

    def handle(self, *args, **options):
        output_file = options['output']
        
        # Get all profiles
        profiles = PGOldStudentProfile.objects.all()
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'uid', 'registration_no', 'roll_no', 'student_name', 'student_name_hindi',
                'fathers_name', 'mothers_name', 'gender', 'dob', 'college_id', 'college_code', 'college_name',
                'course_code', 'discipline_code', 'batch_code', 'current_semester',
                'pg_faculty', 'pg_department', 'pg_degree', 'pg_program',
                'final_result', 'gpa', 'cgpa', 'total_percentage',
                'source_user_id', 'is_active', 'created_at', 'updated_at'
            ])
            
            # Data
            for profile in profiles:
                writer.writerow([
                    profile.uid,
                    profile.registration_no,
                    profile.roll_no,
                    profile.student_name,
                    profile.student_name_hindi,
                    profile.fathers_name,
                    profile.mothers_name,
                    profile.gender,
                    profile.dob,
                    profile.college.id if profile.college else '',
                    profile.college.college_code if profile.college else '',
                    profile.college.name if profile.college else '',
                    profile.course_code,
                    profile.discipline_code,
                    profile.batch_code,
                    profile.current_semester,
                    profile.pg_faculty,
                    profile.pg_department,
                    profile.pg_degree,
                    profile.pg_program,
                    profile.final_result,
                    profile.gpa,
                    profile.cgpa,
                    profile.total_percentage,
                    profile.source_user_id,
                    profile.is_active,
                    profile.created_at,
                    profile.updated_at
                ])
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully exported {profiles.count()} profiles to {output_file}')
        )
