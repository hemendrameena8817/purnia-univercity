import os
import django
import sys

# Set up Django environment
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import UGResultCurrent
from django.db.models import Count

def analyze():
    print("="*50)
    print("STAGING DATA ANALYSIS: UGResultCurrent")
    print("="*50)
    
    total = UGResultCurrent.objects.count()
    print(f"Total Records: {total:,}")
    
    print("\nSemester Distribution:")
    sem_counts = UGResultCurrent.objects.values('semester_code').annotate(count=Count('id')).order_by('semester_code')
    for sem in sem_counts:
        print(f"  - {sem['semester_code']}: {sem['count']:,} records")
        
    print("\nSample Student Analysis (2134B100023):")
    student_records = UGResultCurrent.objects.filter(college_reg_no='2134B100023').order_by('semester_code', 'paper_code')
    print(f"Total records for student: {student_records.count()}")
    header = f"{'Sem':<10} | {'Paper':<10} | {'Subject':<30} | {'Type':<10} | {'Th':<5} | {'Pr':<5}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for r in student_records:
        print(f"{str(r.semester_code):<10} | {str(r.paper_code):<10} | {str(r.subject_name)[:30]:<30} | {str(r.exam_type):<10} | {str(r.theory):<5} | {str(r.pra):<5}")

if __name__ == "__main__":
    analyze()
