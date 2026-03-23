import os
import sys
import django
from django.db.models import Count, Sum

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import VocationalResultCurrent

print("=== BCA_HONS Year 1 Subjects Stats ===")
stats = VocationalResultCurrent.objects.filter(
    course_code='BCA_HONS', 
    semester_code='1ST'
).values('subject_name', 'paper_code', 'status', 'maximum_mark').distinct().order_by('subject_name')

for s in stats:
    print(s)

print("\n=== Count of unique subjects (stripped/upper) ===")
subjects = VocationalResultCurrent.objects.filter(
    course_code='BCA_HONS', 
    semester_code='1ST'
).values_list('subject_name', flat=True).distinct()
unique_subs = set(s.strip().upper() for s in subjects if s)
print(f"Total Unique Subjects found: {len(unique_subs)}")
for s in sorted(unique_subs):
    print(f"- {s}")
