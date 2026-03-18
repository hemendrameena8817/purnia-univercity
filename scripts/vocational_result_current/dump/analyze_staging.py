import os
import django
import sys

# Set up Django environment
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import VocationalResultCurrent
from django.db.models import Count

def analyze():
    print("="*50)
    print("STAGING DATA ANALYSIS: VocationalResultCurrent")
    print("="*50)
    
    total = VocationalResultCurrent.objects.count()
    print(f"Total Records: {total:,}")
    
    print("\nSemester Distribution:")
    sem_counts = VocationalResultCurrent.objects.values('semester_code').annotate(count=Count('id')).order_by('semester_code')
    for sem in sem_counts:
        print(f"  - {sem['semester_code']}: {sem['count']:,} records")
        
    print("\nCourse Distribution (Top 10):")
    course_counts = VocationalResultCurrent.objects.values('course_code').annotate(count=Count('id')).order_by('-count')[:10]
    for c in course_counts:
        print(f"  - {c['course_code']}: {c['count']:,}")

    print("\nSample Student Analysis:")
    # Get a random student with multiple records
    sample_student = VocationalResultCurrent.objects.values('college_reg_no').annotate(count=Count('id')).filter(count__gt=1).order_by('-count').first()
    if sample_student:
        reg_no = sample_student['college_reg_no']
        student_records = VocationalResultCurrent.objects.filter(college_reg_no=reg_no).order_by('semester_code', 'paper_code')
        print(f"Total records for student ({reg_no}): {student_records.count()}")
        header = f"{'Sem':<10} | {'Paper':<10} | {'Subject':<30} | {'Marks':<10} | {'Result':<10}"
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        for r in student_records:
            print(f"{str(r.semester_code):<10} | {str(r.paper_code):<10} | {str(r.subject_name)[:30]:<30} | {str(r.mark_secured):<10} | {str(r.subject_result):<10}")
    else:
        print("No sample student with multiple records found.")

if __name__ == "__main__":
    analyze()
