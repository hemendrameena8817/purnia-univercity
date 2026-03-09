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

from ug.models import UGExamResult, StudentCourseAssessment

def main():
    target_sem = sys.argv[1] if len(sys.argv) > 1 else '1ST'
    
    print(f"Generating BACK marks upload templates for {target_sem} semester...")
    
    # We want to find all students who failed (FAIL) in the specified semester.
    results = UGExamResult.objects.filter(
        semester=target_sem,
        semester_result='FAIL'
    ).select_related('student', 'student__college')
    
    upload_data = []
    
    # Pre-fetch assessments to speed things up? Or just query in loop.
    count = 0
    total = results.count()
    
    for res in results:
        count += 1
        if count % 100 == 0:
            print(f"Processing student {count}/{total}...")
            
        student = res.student
        
        # Check exam type
        exam_type_to_check = 'BACK' if res.semester_result in ['PARTLY_QUALIFIED', 'DISQUALIFIED'] else 'REGULAR'
        
        # If the student is FAIL, they need to re-appear for ALL CIA exams in that semester.
        cia_assessments = StudentCourseAssessment.objects.filter(
            student=student,
            semester=target_sem,
            exam_type=exam_type_to_check,
            label__icontains='CIA'
        )
        
        for a in cia_assessments:
            label = (a.label or '').upper()
            
            # Usually 'label' has 'THEORY' or 'PRACTICAL'
            component = 'THEORY' if 'THEORY' in label else ('PRACTICAL' if 'PRACTICAL' in label or 'LAB' in label else 'UNKNOWN')
            
            row = {
                'Registration No': student.registration_no or '',
                'Roll No': student.roll_no or '',
                'Semester': target_sem,
                'Exam Type': exam_type_to_check,
                'Theory': 'Yes' if component == 'THEORY' else '',
                'Practical': 'Yes' if component == 'PRACTICAL' else '',
                'Paper Code': a.paper_code or '',
                'Paper Name': a.course_name or '',
                'Course Code': a.course_type or '',  # Using course_type to output formats like MJC-1 instead of 1001
                'College Name': student.college.name if student.college else 'Unknown_College',
                'Marks Obtained (Leave empty if absent)': ''
            }
            upload_data.append(row)
            
    # Write to college-wise files
    college_grouped = {}
    for row in upload_data:
        c_name = row['College Name']
        if c_name not in college_grouped:
            college_grouped[c_name] = []
        college_grouped[c_name].append(row)
        
    output_dir = BASE_DIR / f'{target_sem.lower()}_sem_upload_templates'
    output_dir.mkdir(exist_ok=True)
    
    if college_grouped:
        keys = ['Registration No', 'Roll No', 'Semester', 'Exam Type', 'Theory', 'Practical', 'Paper Code', 'Paper Name', 'Course Code', 'Marks Obtained (Leave empty if absent)']
        for college, rows in college_grouped.items():
            # Sanitize filename
            safe_cname = "".join([c for c in college if c.isalnum() or c==' ']).rstrip().replace(' ', '_')
            if not safe_cname: safe_cname = "Unknown_College"
            
            filepath = output_dir / f"{safe_cname}_Upload_Template.csv"
            
            # Remove College Name from output rows to keep it clean for college
            clean_rows = []
            for r in rows:
                cr = {k: v for k, v in r.items() if k in keys}
                clean_rows.append(cr)
                
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(clean_rows)
                
        print(f"\n✅ Generated {len(college_grouped)} college-wise upload templates in directory: {output_dir}")
    else:
        print("\nNo failed assessments found to generate upload templates.")

if __name__ == '__main__':
    main()
