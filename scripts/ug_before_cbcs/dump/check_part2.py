import os
import sys
import django

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug_before_cbcs.models import UGBeforeCBCSExamRegistration

count = UGBeforeCBCSExamRegistration.objects.filter(exam__part='PART2').count()
print(f"Part 2 Registrations: {count}")

if count > 0:
    reg = UGBeforeCBCSExamRegistration.objects.filter(exam__part='PART2').first()
    print(f"Sample Student: {reg.student.student_name} ({reg.student.registration_no})")
