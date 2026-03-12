import os
import sys
import django

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import VocationalResultCurrent

def inspect_data():
    print("Inspecting VocationalResultCurrent data...")
    try:
        records = VocationalResultCurrent.objects.all()[:10]
        if not records.exists():
            print("No records found in VocationalResultCurrent.")
            return

        for record in records:
            print(f"--- Record: {record.student_name} ---")
            print(f"UID: {record.uid}")
            print(f"Reg: {record.college_reg_no} | Roll: {record.college_roll_no}")
            print(f"Course: {record.course_code} | Discipline: {record.discipline_code}")
            print(f"Sem: {record.semester_code} | Session: {record.session_code}")
            print(f"Subject: {record.subject_name} ({record.subject_code}) | Paper: {record.paper_code}")
            print(f"Marks: Secured={record.mark_secured} | Max={record.maximum_mark} | Pass={record.pass_mark}")
            print(f"Result: {record.subject_result} | Final: {record.final_result}")
            print("-" * 20)

        # Unique values analysis
        print("\nDistinct Semester Codes:")
        print(list(VocationalResultCurrent.objects.values_list('semester_code', flat=True).distinct()))
        
        print("\nDistinct Course Codes:")
        print(list(VocationalResultCurrent.objects.values_list('course_code', flat=True).distinct()))

        print("\nDistinct Exam Types:")
        print(list(VocationalResultCurrent.objects.values_list('exam_type', flat=True).distinct()))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_data()
