import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.models import PGStudentCourseAssessment

def check_values():
    print("Checking PGStudentCourseAssessment (Local DB)...")
    
    print("\nDistinct SESSIONS:")
    sessions = PGStudentCourseAssessment.objects.values_list('session', flat=True).distinct().order_by('session')
    for s in sessions:
        print(f"  '{s}'")
        
    print("\nDistinct SEMESTERS:")
    semesters = PGStudentCourseAssessment.objects.values_list('semester', flat=True).distinct().order_by('semester')
    for s in semesters:
        print(f"  '{s}'")

    print("\nDistinct BATCHES (via batch__name):")
    batches = PGStudentCourseAssessment.objects.values_list('batch__name', flat=True).distinct().order_by('batch__name')
    for b in batches:
        print(f"  '{b}'")

if __name__ == '__main__':
    check_values()
