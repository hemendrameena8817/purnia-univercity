"""
Import MCA Students Script

This script imports student profiles, and optionally assessments and results from an Excel file.
It creates Users, Students, and optionally Semester Results and Assessments.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.mca.import_mca_students import run_import
>>> run_import('old_data/MCA_DATA.xlsx')

OR run directly:
poetry run python scripts/mca/import_mca_students.py --file "old_data/MCA_DATA.xlsx"

Required Excel Columns:
- Roll Number
- Name of Candidate
- Reg No
- Batch (e.g., 2021 Admission)
- Session (e.g., 2021-23)
- College
- Course (e.g., MCA)
- Father Name (optional)
- Mother Name (optional)

Optional Columns (if importing results):
- MCA Exam (used to fetch session/semester)
- Result (Status e.g., PASS)
- Total (Marks Obtained)
- Subject Columns (Subject names as defined in MCASubject)
"""

import os
import sys
import pandas as pd
import argparse
from django.db import transaction
from django.contrib.auth import get_user_model

# Setup Django if running directly
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    import django
    django.setup()

from mca_sem.models import (
    MCAStudentProfile, MCAExam, MCASemesterResult, MCAStudentAssessment, 
    MCASubject, MCABatch, MCASession, MCACourse
)
from colleges.models import College

User = get_user_model()

# Columns that are NOT subjects
NON_SUBJECT_COLUMNS = [
    'Roll Number', 'Name of Candidate', 'Reg No', 'Total', 'Result', 
    'College', 'Batch', 'Session', 'Father Name', 'MCA Exam', 'Exam Center',
    'Mother Name', 'DOB', 'Mobile', 'Course', 'Grace'
]

def get_or_create_user(reg_no, full_name):
    """
    Get or create a User based on Registration Number.
    """
    user = User.objects.filter(username=reg_no).first()
    if user:
        return user
    
    first_name = full_name.strip()
    
    # Create new user
    user = User.objects.create_user(
        username=reg_no,
        first_name=first_name,
        last_name="",
        password=reg_no, # Default password is reg no
        current_profile="mca_sem"
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
    
    # Cache to avoid duplicate DB lookups
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
            cache['sessions'][session_name] = MCASession.objects.filter(name=session_name).first()
        if not cache['sessions'][session_name]:
            errors.append(f"Row {row_num}: Session '{session_name}' not found.")

        # 3. Batch
        batch_name = str(row['Batch']).strip()
        if batch_name not in cache['batches']:
            sess = cache['sessions'].get(session_name)
            if sess:
                cache['batches'][batch_name] = MCABatch.objects.filter(name=batch_name, session=sess).first()
            else:
                cache['batches'][batch_name] = None
        if not cache['batches'][batch_name]:
            errors.append(f"Row {row_num}: Batch '{batch_name}' not found for session '{session_name}'.")

        # 4. Course
        course_name = str(row.get('Course', 'MCA')).strip()
        if course_name not in cache['courses']:
            cache['courses'][course_name] = MCACourse.objects.filter(name__iexact=course_name).first()
        if not cache['courses'][course_name]:
            errors.append(f"Row {row_num}: Course '{course_name}' not found.")

        # 5. Exam (Optional)
        exam_name = row.get('MCA Exam')
        if not pd.isna(exam_name):
            exam_name = str(exam_name).strip()
            if exam_name not in cache['exams']:
                exam = MCAExam.objects.filter(name__iexact=exam_name).first()
                if not exam:
                    errors.append(f"Row {row_num}: Exam '{exam_name}' not found in database.")
                cache['exams'][exam_name] = exam

        # 6. Subjects (Only if exam is present)
        if not pd.isna(exam_name):
            for sub_col in subject_cols:
                subject_name = str(sub_col).strip()
                if subject_name not in cache['subjects']:
                    cache['subjects'][subject_name] = MCASubject.objects.filter(name__iexact=subject_name).first()
                if not cache['subjects'][subject_name]:
                    # Also try to find by paper_code
                    subj = MCASubject.objects.filter(paper_code__iexact=subject_name).first()
                    cache['subjects'][subject_name] = subj
                
                if not cache['subjects'][subject_name]:
                    errors.append(f"Row {row_num}: Subject/Paper '{subject_name}' not found.")

    if errors:
        print("\nVALIDATION FAILED! Please fix the following errors before re-running:")
        for err in errors[:50]:
            print(f"  - {err}")
        return

    print("Validation Successful! Starting Import...\n")

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
                course = cache['courses'][str(row.get('Course', 'MCA')).strip()]
                
                father_name = str(row.get('Father Name', '')).strip() if not pd.isna(row.get('Father Name')) else ""
                mother_name = str(row.get('Mother Name', '')).strip() if not pd.isna(row.get('Mother Name')) else ""
                
                # User
                user = get_or_create_user(reg_no, name)
                
                # Student Profile
                student, created = MCAStudentProfile.objects.update_or_create(
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

                # Optional Result
                exam_name = row.get('MCA Exam')
                if not pd.isna(exam_name):
                    exam_obj = cache['exams'][str(exam_name).strip()]
                    result_status = str(row.get('Result', '')).strip()
                    
                    # Estimate semester and session from exam
                    sem_str = str(exam_obj.name).upper()
                    semester = "1" # default
                    if "SEM-I" in sem_str or "1ST" in sem_str: semester = "1"
                    elif "SEM-II" in sem_str or "2ND" in sem_str: semester = "2"
                    elif "SEM-III" in sem_str or "3RD" in sem_str: semester = "3"
                    elif "SEM-IV" in sem_str or "4TH" in sem_str: semester = "4"

                    res_obj, created = MCASemesterResult.objects.update_or_create(
                        student=student,
                        semester=semester,
                        session=exam_obj.session,
                        defaults={
                            'semester_result': result_status,
                        }
                    )
                    if created: stats['results_created'] += 1
                    else: stats['results_updated'] += 1
                    
                    # Student Assessments (Granular marks)
                    for sub_col in subject_cols:
                        marks_val = row[sub_col]
                        if pd.isna(marks_val) or str(marks_val).strip() == '':
                            continue
                            
                        try: obtained = float(marks_val)
                        except: obtained = 0
                        
                        subject_obj = cache['subjects'][str(sub_col).strip()]
                        
                        MCAStudentAssessment.objects.update_or_create(
                            student=student,
                            subject=subject_obj,
                            semester=semester,
                            label='ESE-Theory', # Defaulting to ESE-Theory for legacy import
                            defaults={
                                'ind_marks_obtained': obtained,
                                'ind_max_marks': subject_obj.full_marks,
                                'ind_pass_marks': subject_obj.pass_marks,
                                'ind_is_absent': False if obtained > 0 else True,
                                'session': exam_obj.session,
                                'college': college,
                                'batch': batch_obj,
                                'exam_type': 'REGULAR'
                            }
                        )

        except Exception as e:
            print(f"Error processing row {index + 2} (Roll: {row.get('Roll Number')}): {e}")

    print("\nImport Completed!")
    print(f"Students Created: {stats['students_created']}, Updated: {stats['students_updated']}")
    print(f"Results Created: {stats['results_created']}, Updated: {stats['results_updated']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import MCA Students from Excel')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    run_import(file_path)
