"""
Import PLW Results Script

This script imports student profiles, exams, and results from an Excel file.
It creates Users, Students, Exams, and Results with Details.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.plw.import_plw_results import run_import
>>> run_import('old_data/PRE_LAW_PART_I_USER_PROFILE_MARKS_SHEET.xlsx')

OR run directly:
poetry run python scripts/plw/import_plw_results.py --file "old_data/Pre_Law_Sample.xlsx"

Required Excel Columns:
- Roll Number
- Name of Candidate
- Reg No
- Batch (e.g., 2021-2024)
- Session (e.g., 2021-24) or derive from Batch
- College
- Course (e.g., Pre-Law) - will be mapped to existing courses in database
- PLW Exam
- Result (Status e.g., PASS)
- Total (Total Marks)
- Exam Center (optional)
- Father Name (optional)
- Mother Name
- Subject Columns (English-I, etc.)
"""

import os
import sys
import pandas as pd
import argparse
from datetime import date
from django.db import transaction
from django.contrib.auth import get_user_model

# Setup Django if running directly
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    import django
    django.setup()

from plw.models import (
    PLWStudentProfile, PLWExam, PLWResult, PLWResultDetail, 
    PLWSubject, PLWBatch, PLWSession, PLWCourse
)
from colleges.models import College

User = get_user_model()

# Columns that are NOT subjects
NON_SUBJECT_COLUMNS = [
    'Roll Number', 'Name of Candidate', 'Reg No', 'Total', 'Result', 
    'College', 'Batch', 'Session', 'Father Name', 'PLW Exam', 'Exam Center',
    'Mother Name', 'DOB', 'Mobile', 'Course', 'Grace'
]

def get_or_create_user(reg_no, full_name):
    """
    Get or create a User based on Registration Number.
    """
    # Try to find by username (Reg No)
    user = User.objects.filter(username=reg_no).first()
    if user:
        return user
    
    first_name = full_name.strip()
    
    # Create new user
    user = User.objects.create_user(
        username=reg_no,
        first_name=first_name,
        last_name="",
        password=reg_no # Default password is reg no
    )
    print(f"Created User: {reg_no}")
    return user

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    
    print("Columns:", df.columns.tolist())
    
    # Identify Subject Columns dynamically
    subject_cols = [col for col in df.columns if col not in NON_SUBJECT_COLUMNS and "Unnamed" not in str(col)]
    print(f"Identified Subjects: {subject_cols}")
    
    stats = {
        'students_created': 0, 'students_updated': 0,
        'results_created': 0, 'results_updated': 0
    }

    # Iterate rows
    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                # 1. Extract Basic Data
                roll_no = str(row['Roll Number']).strip()
                reg_no = str(row['Reg No']).strip()
                name = str(row['Name of Candidate']).strip()
                college_name = str(row['College']).strip()
                batch_name = str(row['Batch']).strip()
                session_name = str(row['Session']).strip()
                exam_name = str(row['PLW Exam']).strip()
                
                father_name = row.get('Father Name')
                if pd.isna(father_name): father_name = ""
                else: father_name = str(father_name).strip()

                mother_name = row.get('Mother Name')
                if pd.isna(mother_name): mother_name = ""
                else: mother_name = str(mother_name).strip()

                exam_center = row.get('Exam Center')
                if pd.isna(exam_center): exam_center = ""
                else: exam_center = str(exam_center).strip()
                
                total_marks = row['Total']
                result_status = str(row['Result']).strip()
                
                grace_marks = row.get('Grace')
                if pd.isna(grace_marks) or str(grace_marks).strip() == '':
                    grace_marks = None
                else:
                    try:
                        grace_marks = int(grace_marks)
                    except:
                        grace_marks = None
                
                # 2. User
                user = get_or_create_user(reg_no, name)
                
                # 3. College
                # Try exact match or contains
                college = College.objects.filter(name__iexact=college_name).first()
                if not college:
                    college = College.objects.filter(name__icontains=college_name).first()
                
                if not college:
                    # Create generic college if missing to avoid breaking import, or error out?
                    # For now, create a placeholder if strictly needed, or skip
                    # Better to create one to proceed
                    college, _ = College.objects.get_or_create(name=college_name, defaults={'college_code': 'TEMP'})
                    print(f"Warning: Created provisional college '{college_name}'")

                # 4. Session & Batch
                # Handle session years (e.g. 2023 -> 2023-2024 or just 2023?) Assuming name is key
                session_obj, _ = PLWSession.objects.get_or_create(
                    name=session_name,
                    defaults={
                        'start_year': int(session_name.split('-')[0]) if '-' in session_name else int(session_name),
                        'end_year': int(session_name.split('-')[1]) if '-' in session_name else int(session_name) + 1
                    }
                )
                
                batch_obj, _ = PLWBatch.objects.get_or_create(
                    name=batch_name,
                    session=session_obj,
                    defaults={'admission_year': session_obj.start_year}
                )

                # 5. Course - Read from Excel and map to existing course
                course_name = row.get('Course')
                if pd.isna(course_name) or str(course_name).strip() == '':
                    # Default to Pre-Law if no course specified
                    course_name = "Pre-Law"
                else:
                    course_name = str(course_name).strip()
                
                # Try to find existing course (case-insensitive)
                course = PLWCourse.objects.filter(name__iexact=course_name).first()
                
                if not course:
                    # Create new course if not found
                    print(f"Warning: Course '{course_name}' not found in database. Creating new course...")
                    course = PLWCourse.objects.create(name=course_name, duration_years=5)

                # 6. Student Profile
                student, created = PLWStudentProfile.objects.update_or_create(
                    roll_no=roll_no,
                    defaults={
                        'user': user,
                        'registration_no': reg_no,
                        'father_name': father_name,
                        'mother_name': mother_name,
                        'college': college,
                        'course': course,
                        'batch': batch_obj
                    }
                )
                if created: stats['students_created'] += 1
                else: stats['students_updated'] += 1

                # 7. Exam
                # Assuming exam name is unique enough; publication date default today if new
                exam_obj, _ = PLWExam.objects.get_or_create(
                    name=exam_name,
                    session=session_name,
                    defaults={
                        'exam_month_year': 'Unknown', # Or parse from name/sheet if available
                        'publication_date': date.today()
                    }
                )
                
                # 8. Result
                # total_marks might be NaN or string
                try:
                    t_marks = int(total_marks)
                except:
                    t_marks = 0

                result_obj, created = PLWResult.objects.update_or_create(
                    student=student,
                    exam=exam_obj,
                    defaults={
                        'total_marks': t_marks,
                        'grace': grace_marks,
                        'result_status': result_status,
                        'exam_center': exam_center
                    }
                )
                if created: stats['results_created'] += 1
                else: stats['results_updated'] += 1
                
                # 9. Result Details (Subjects)
                for sub_col in subject_cols:
                    marks_val = row[sub_col]
                    
                    # Skip if marks is empty/NaN
                    if pd.isna(marks_val) or str(marks_val).strip() == '':
                        continue
                        
                    try:
                        obtained = int(marks_val)
                    except:
                        # Could be 'Absent' or other text
                        obtained = 0 # Or handle appropriately
                    
                    # Find Subject by Name
                    # We assume subject name in Excel matches DB name
                    # Or we create it dynamically? Better to try find.
                    # Since we have "English-I" in excel and DB, name match should work.
                    subject_obj = PLWSubject.objects.filter(name__iexact=sub_col).first()
                    
                    if not subject_obj:
                        # Try simple matching or create?
                        print(f"  Note: Subject '{sub_col}' not found in DB. Creating...")
                        subject_obj = PLWSubject.objects.create(name=sub_col, paper_code="?", full_marks=100, pass_marks=33)
                    
                    PLWResultDetail.objects.update_or_create(
                        result=result_obj,
                        subject=subject_obj,
                        defaults={'marks_obtained': obtained}
                    )

        except Exception as e:
            print(f"Error processing row {index + 2} (Roll: {row.get('Roll Number')}): {e}")
            import traceback
            traceback.print_exc()

    print("\nImport Completed!")
    print(f"Students Created: {stats['students_created']}, Updated: {stats['students_updated']}")
    print(f"Results Created: {stats['results_created']}, Updated: {stats['results_updated']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import PLW Results from Excel')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    run_import(file_path)
