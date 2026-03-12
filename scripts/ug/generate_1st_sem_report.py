import os
import sys
import django
import csv
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import UGExamResult, UGStudentProfile, StudentCourseAssessment
from ug.services.result_calculator import UGResultCalculator

def main():
    print("Generating report for 1ST semester (FAIL, PROMOTED, PARTLY_QUALIFIED, DISQUALIFIED)...")
    
    # Fetch Exam Results for 1ST semester with the specified statuses
    results = UGExamResult.objects.filter(
        semester='1ST',
        semester_result__in=['FAIL', 'PROMOTED', 'PARTLY_QUALIFIED', 'DISQUALIFIED']
    ).select_related('student', 'student__college', 'student__batch', 'student__user')
    
    total_count = results.count()
    print(f"Found {total_count} students matching the criteria.")
    
    output_data = []
    
    for idx, res in enumerate(results, 1):
        if idx % 100 == 0:
            print(f"Processing student {idx}/{total_count}...")
            
        student = res.student
        
        # Determine which exam type to check based on the status
        exam_type_to_check = 'BACK' if res.semester_result in ['PARTLY_QUALIFIED', 'DISQUALIFIED'] else 'REGULAR'
        
        failed_assessments = StudentCourseAssessment.objects.filter(
            student=student,
            semester='1ST',
            exam_type=exam_type_to_check,
            ind_is_pass=False
        )
        
        failed_cia_papers = set()
        failed_cia_courses = set()
        failed_ese_papers = set()
        failed_ese_courses = set()
        
        for a in failed_assessments:
            label = (a.label or '').upper()
            if 'CIA' in label:
                failed_cia_papers.add(a.paper_code)
                if a.course_code: failed_cia_courses.add(a.course_code)
            elif 'ESE' in label:
                failed_ese_papers.add(a.paper_code)
                if a.course_code: failed_ese_courses.add(a.course_code)
                
        # Handle cases where user might not have standard django user first_name populated but rather profile fields
        first_name = student.user.first_name if student.user else ''
        if not first_name:
            # Fallback to splitting full name if first_name is empty
            first_name = student.full_name.split()[0] if student.full_name else ''
            
        row = {
            'First Name': first_name,
            'Roll No': student.roll_no or '',
            'Registration Number': student.registration_no or '',
            'College Name': student.college.name if student.college else '',
            'Session': student.batch.name if student.batch else '',
            'Overall Status': res.semester_result,
            'Failed in CIA (Papers)': ', '.join(sorted(list(failed_cia_papers))),
            'Failed in CIA (Course Codes)': ', '.join(sorted(list(failed_cia_courses))),
            'Failed in ESE (Papers)': ', '.join(sorted(list(failed_ese_papers))),
            'Failed in ESE (Course Codes)': ', '.join(sorted(list(failed_ese_courses)))
        }

        output_data.append(row)
        
    # Group data by college
    college_grouped_data = {}
    for row in output_data:
        college_name = row['College Name'] or 'Unknown_College'
        if college_name not in college_grouped_data:
            college_grouped_data[college_name] = []
        college_grouped_data[college_name].append(row)
        
    output_dir = BASE_DIR / '1st_semester_reports'
    output_dir.mkdir(exist_ok=True)
    
    if college_grouped_data:
        keys = output_data[0].keys()
        for college, rows in college_grouped_data.items():
            # Sanitize college name for filename
            safe_college_name = "".join([c for c in college if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            safe_college_name = safe_college_name.replace(' ', '_')
            if not safe_college_name:
                safe_college_name = "Unknown_College"
                
            college_file = output_dir / f"{safe_college_name}.csv"
            
            with open(college_file, 'w', newline='', encoding='utf-8') as f:
                dict_writer = csv.DictWriter(f, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(rows)
            
        print(f"\n✅ Generated {len(college_grouped_data)} college-wise reports in directory: {output_dir}")
    else:
        print("\nNo data to write.")

if __name__ == '__main__':
    main()
