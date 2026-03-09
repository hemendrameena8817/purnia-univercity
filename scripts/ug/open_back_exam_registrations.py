import os
import sys

# Setup Django path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')

import django
django.setup()

from django.utils import timezone
from datetime import datetime, time
from ug.models import UGExamResult, ExamRegistration


def run():
    print("Finding students who are Promoted, Partly Qualified, or Disqualified...")
    
    # Identify students who need their BACK exams opened
    results = UGExamResult.objects.filter(
        semester_result__in=['PROMOTED', 'PARTLY_QUALIFIED', 'DISQUALIFIED']
    ).values_list('student_id', flat=True).distinct()
    
    student_count = results.count()
    print(f"Found {student_count} students with matching exam results.")
    
    # Fetch their pending exam registrations (usually exam_type='BACK')
    regs_to_update = ExamRegistration.objects.filter(
        student_id__in=results,
        session='2025-26',
        sem=1,
        status__in=['PENDING', 'OPEN']
    )
    
    reg_count = regs_to_update.count()
    print(f"Opening {reg_count} pending exam registrations...")
    
    # Define the precise time bounds
    now = timezone.now()
    # "midnight of 12-3-2026" means March 12, 2026, 23:59:59 (since end date is typically end of the day)
    # or 00:00:00 if interpreted strictly as the start. I will use the end of the day:
    start_date = timezone.make_aware(datetime(2026, 3, 9, 00, 00, 00))
    end_date = timezone.make_aware(datetime(2026, 3, 12, 23, 59, 59))
    
    # Bulk update the found registrations
    updated_count = regs_to_update.update(
        status='OPEN', 
        is_open=True,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"Successfully updated {updated_count} registrations to OPEN status!")

if __name__ == "__main__":
    run()
