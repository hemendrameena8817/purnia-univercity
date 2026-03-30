import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from ug.models import UGExamCenterMapping, UGExam

class Command(BaseCommand):
    help = 'Generate an Excel-ready CSV for UG Exam Centers (Center Name and Code)'

    def handle(self, *args, **options):
        # 1. Identify active or latest UG Exams to fetch center mappings
        # We look for session 2025-26 or any active exam
        active_exams = UGExam.objects.filter(is_active=True).order_by('-created_at')
        if not active_exams.exists():
            active_exams = [UGExam.objects.all().last()]
        
        exam_ids = [e.id for e in active_exams if e]
        
        if not exam_ids:
            self.stdout.write(self.style.ERROR("No UG exams found in database."))
            return

        # 2. Extract unique centers from the mapping
        # Each mapping links 1 Exam + 1 Center College to multiple Attached Colleges
        mappings = UGExamCenterMapping.objects.filter(
            exam_id__in=exam_ids
        ).select_related('center', 'exam').prefetch_related('attached_colleges').distinct()

        if not mappings.exists():
            self.stdout.write(self.style.WARNING(f"No center mappings found for exams: {active_exams}"))
            return

        # Prepare unique center list to avoid duplicates
        # We'll map: Center Name, Center Code, and the Colleges attached to them
        center_data = []
        processed_centers = set()

        for m in mappings:
            if not m.center:
                continue
            
            center_key = (m.center.college_code, m.exam.id)
            if center_key in processed_centers:
                continue
                
            processed_centers.add(center_key)
            
            # Formulate attached college codes list for reference
            attached = ", ".join([f"{c.college_code or 'N/A'}" for c in m.attached_colleges.all()])
            
            # Fetch primary college username (traversing CollegeUserProfile -> UserAccount)
            primary_profile = m.center.users.first()
            college_username = primary_profile.user.username if primary_profile and primary_profile.user else "N/A"
            
            center_data.append({
                'Exam Name': m.exam.name,
                'Exam Session': m.exam.session,
                'Centre Name': m.center.name,
                'Centre Code': m.center.college_code,      # Reverted to college_code
                'Username': college_username,
                'Attached College Codes': attached
            })

        # Add sorting by Centre Code
        center_data.sort(key=lambda x: str(x['Centre Code'] or "").zfill(5))

        # 3. Write to CSV in the root directory
        import datetime
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        filename = f'UGExamCenterMapping-{today_str}.csv'
        filepath = os.path.join(settings.BASE_DIR, filename)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Sl. No.', 'centre_code', 'name of the centre', 'username']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for idx, row in enumerate(center_data, 1):
                writer.writerow({
                    'Sl. No.': idx,
                    'centre_code': row['Centre Code'],
                    'name of the centre': row['Centre Name'],
                    'username': row['Username']
                })

        self.stdout.write(self.style.SUCCESS(f"Successfully generated UG Centers file: {filepath} ({len(center_data)} centers)"))
