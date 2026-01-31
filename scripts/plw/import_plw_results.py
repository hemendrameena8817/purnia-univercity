"""
Import PLW Results Script

This script imports student profiles, exams, and results from an Excel file.
It creates Users, Students, Exams, and Results with Details.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.plw.import_plw_results import run_import
>>> run_import('old_data/FINAL_LLB_PART_1.xlsx')

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
    
    # --- PHASE 1: VALIDATION ---
    print("\nStarting Validation Pass...")
    errors = []
    
    # Cache to avoid duplicate DB lookups for the same values
    cache = {
        'colleges': {}, 'sessions': {}, 'batches': {}, 
        'courses': {}, 'exams': {}, 'subjects': {}
    }

    for index, row in df.iterrows():
        row_num = index + 2
        
        # 1. College
        college_name = str(row['College']).strip()
        if college_name not in cache['colleges']:
            college = College.objects.filter(name__iexact=college_name).first()
            if not college:
                college = College.objects.filter(name__icontains=college_name).first()
            cache['colleges'][college_name] = college
        if not cache['colleges'][college_name]:
            errors.append(f"Row {row_num}: College '{college_name}' not found.")

        # 2. Session
        session_name = str(row['Session']).strip()
        if session_name not in cache['sessions']:
            cache['sessions'][session_name] = PLWSession.objects.filter(name=session_name).first()
        if not cache['sessions'][session_name]:
            errors.append(f"Row {row_num}: Session '{session_name}' not found.")

        # 3. Batch
        batch_name = str(row['Batch']).strip()
        if batch_name not in cache['batches']:
            # Also check session link for batch
            sess = cache['sessions'].get(session_name)
            if sess:
                cache['batches'][batch_name] = PLWBatch.objects.filter(name=batch_name, session=sess).first()
            else:
                cache['batches'][batch_name] = None
        if not cache['batches'][batch_name]:
            errors.append(f"Row {row_num}: Batch '{batch_name}' not found for session '{session_name}'.")

        # 4. Course
        course_name = str(row.get('Course', 'Pre-Law')).strip()
        if course_name not in cache['courses']:
            cache['courses'][course_name] = PLWCourse.objects.filter(name__iexact=course_name).first()
        if not cache['courses'][course_name]:
            errors.append(f"Row {row_num}: Course '{course_name}' not found.")

        # 5. Exam
        exam_name = str(row['PLW Exam']).strip()
        if exam_name not in cache['exams']:
            # Match ONLY by name now, as requested
            exam = PLWExam.objects.filter(name__iexact=exam_name).first()
            
            if not exam:
                errors.append(f"Row {row_num}: Exam '{exam_name}' not found in database.")
            
            cache['exams'][exam_name] = exam

        # 6. Subjects
        for sub_col in subject_cols:
            subject_name = str(sub_col).strip()
            if subject_name not in cache['subjects']:
                cache['subjects'][subject_name] = PLWSubject.objects.filter(name__iexact=subject_name).first()
            if not cache['subjects'][subject_name]:
                errors.append(f"Row {row_num}: Subject '{subject_name}' not found. Please create it or check spelling.")

    if errors:
        print("\nVALIDATION FAILED! Please fix the following errors before re-running:")
        for err in errors[:50]: # Show first 50 errors
            print(f"  - {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors)-50} more errors.")
        return

    print("Validation Successful! All dependencies found. Starting Import...\n")

    # --- PHASE 2: IMPORT ---
    stats = {
        'students_created': 0, 'students_updated': 0,
        'results_created': 0, 'results_updated': 0
    }

    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                roll_no = str(row['Roll Number']).strip()
                reg_no = str(row['Reg No']).strip()
                name = str(row['Name of Candidate']).strip()
                
                college = cache['colleges'][str(row['College']).strip()]
                session_obj = cache['sessions'][str(row['Session']).strip()]
                batch_obj = cache['batches'][str(row['Batch']).strip()]
                course = cache['courses'][str(row.get('Course', 'Pre-Law')).strip()]
                exam_obj = cache['exams'][str(row['PLW Exam']).strip()]
                
                father_name = str(row.get('Father Name', '')).strip() if not pd.isna(row.get('Father Name')) else ""
                mother_name = str(row.get('Mother Name', '')).strip() if not pd.isna(row.get('Mother Name')) else ""
                exam_center = str(row.get('Exam Center', '')).strip() if not pd.isna(row.get('Exam Center')) else ""
                
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
                
                # 6. Student Profile
                student, created = PLWStudentProfile.objects.update_or_create(
                    registration_no=reg_no,
                    defaults={
                        'user': user,
                        'roll_no': roll_no,
                        'father_name': father_name,
                        'mother_name': mother_name,
                        'college': college,
                        'course': course,
                        'batch': batch_obj
                    }
                )
                if created: stats['students_created'] += 1
                else: stats['students_updated'] += 1

                # 8. Result
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
                    if pd.isna(marks_val) or str(marks_val).strip() == '':
                        continue
                        
                    try:
                        obtained = int(marks_val)
                    except:
                        obtained = 0
                    
                    subject_obj = cache['subjects'][sub_col]
                    
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
