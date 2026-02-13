import os
import sys
import django

# Add the project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import UGResultCurrent

def inspect_data():
    print("Inspecting UGResultCurrent data...")
    try:
        records = UGResultCurrent.objects.all()[:10]
        if not records.exists():
            print("No records found in UGResultCurrent.")
            return

        for record in records:
            print(f"--- Record: {record.student_name} ---")
            print(f"UID: {record.uid}")
            print(f"Reg: {record.college_reg_no} | Roll: {record.college_roll_no}")
            print(f"Course: {record.course_code} | Discipline: {record.discipline_code}")
            print(f"Part: {record.semester_code} | Session: {record.session_code}")
            print(f"Subject: {record.subject_name} ({record.subject_code}) | Paper: {record.paper_code}")
            print(f"Marks: T={record.theory} | P={record.pra} | S={record.sessional} | Total={record.subject_total_mark}")
            print(f"Secured: {record.mark_secured} | Max: {record.maximum_mark}")
            print("-" * 20)

        # Unique values analysis
        print("\nDistinct Semester Codes:")
        print(list(UGResultCurrent.objects.values_list('semester_code', flat=True).distinct()))
        
        print("\nDistinct Course Codes:")
        print(list(UGResultCurrent.objects.values_list('course_code', flat=True).distinct()))

        print("\nDistinct Exam Types:")
        print(list(UGResultCurrent.objects.values_list('exam_type', flat=True).distinct()))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_data()
