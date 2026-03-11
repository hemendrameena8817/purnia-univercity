"""
Import PLW Results Only Script

This script imports ONLY results for existing PLW student profiles.
It does NOT create users or student profiles - they must already exist.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.plw.import_plw_results_only import run_import
>>> run_import('old_data/FINAL_LLB_PART_1.xlsx')

OR run directly:
poetry run python scripts/plw/import_plw_results_only.py --file "old_data/Results.xlsx"

Required Excel Columns:
- Reg No (must match existing PLWStudentProfile.registration_no)
- PLW Exam (must match existing PLWExam.name)
- Result (Status e.g., PASS)
- Total (Total Marks)
- Exam Center (optional)
- Grace (optional)
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
    PLWSubject
)

User = get_user_model()

# Columns that are NOT subjects
NON_SUBJECT_COLUMNS = [
    'Reg No', 'Total', 'Result', 'PLW Exam', 'Exam Center', 'Grace'
]

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    
    print("Columns:", df.columns.tolist())
    
    # --- COLUMN VALIDATION ---
    print("\nValidating required columns...")
    required_columns = ['Reg No', 'PLW Exam', 'Result', 'Total']
    
    # Convert DataFrame columns to exact case-sensitive match
    df_columns = df.columns.tolist()
    missing_columns = []
    
    for required_col in required_columns:
        if required_col not in df_columns:
            missing_columns.append(required_col)
    
    if missing_columns:
        print("\nVALIDATION FAILED! Missing required columns:")
        for col in missing_columns:
            print(f"  - '{col}'")
        print("\nAvailable columns:", df_columns)
        return
    
    print("All required columns found!")
    
    # Identify Subject Columns dynamically
    subject_cols = [col for col in df.columns if col not in NON_SUBJECT_COLUMNS and "Unnamed" not in str(col)]
    print(f"Identified Subjects: {subject_cols}")
    
    # --- PHASE 1: VALIDATION ---
    print("\nStarting Validation Pass...")
    errors = []
    
    # Cache to avoid duplicate DB lookups
    cache = {
        'students': {}, 'exams': {}, 'subjects': {}
    }

    for index, row in df.iterrows():
        row_num = index + 2
        
        # Skip empty rows
        if pd.isna(row.get('Reg No')) and pd.isna(row.get('PLW Exam')):
            continue
            
        # 1. Student Profile (must exist)
        reg_no = str(row['Reg No']).strip()
        if reg_no not in cache['students']:
            student = PLWStudentProfile.objects.filter(registration_no=reg_no).first()
            cache['students'][reg_no] = student
        if not cache['students'][reg_no]:
            errors.append(f"Row {row_num}: Student profile with Reg No '{reg_no}' not found. Please create profile first.")

        # 2. Exam (must exist)
        exam_name = str(row['PLW Exam']).strip()
        if exam_name not in cache['exams']:
            exam = PLWExam.objects.filter(name__iexact=exam_name).first()
            cache['exams'][exam_name] = exam
        if not cache['exams'][exam_name]:
            errors.append(f"Row {row_num}: Exam '{exam_name}' not found in database.")
            
        # 3. Validate required data
        if pd.isna(row.get('Reg No')) or str(row['Reg No']).strip() == '':
            errors.append(f"Row {row_num}: Reg No is required.")
            
        if pd.isna(row.get('PLW Exam')) or str(row['PLW Exam']).strip() == '':
            errors.append(f"Row {row_num}: PLW Exam is required.")
            
        if pd.isna(row.get('Result')) or str(row['Result']).strip() == '':
            errors.append(f"Row {row_num}: Result is required.")
            
        if pd.isna(row.get('Total')):
            errors.append(f"Row {row_num}: Total marks is required.")

        # 4. Subjects (must exist)
        for sub_col in subject_cols:
            subject_name = str(sub_col).strip()
            if subject_name not in cache['subjects']:
                subject = PLWSubject.objects.filter(name__iexact=subject_name).first()
                cache['subjects'][subject_name] = subject
            if not cache['subjects'][subject_name]:
                errors.append(f"Row {row_num}: Subject '{subject_name}' not found. Please create it first.")

    if errors:
        print("\nVALIDATION FAILED! Please fix the following errors before re-running:")
        for err in errors[:50]:
            print(f"  - {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors)-50} more errors.")
        return

    print("Validation Successful! All dependencies found. Starting Import...\n")

    # --- PHASE 2: IMPORT ---
    stats = {
        'results_created': 0, 'results_updated': 0,
        'result_details_created': 0, 'result_details_updated': 0
    }

    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                reg_no = str(row['Reg No']).strip()
                exam_name = str(row['PLW Exam']).strip()
                
                student = cache['students'][reg_no]
                exam_obj = cache['exams'][exam_name]
                
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
                
                # Convert total marks to int
                try:
                    t_marks = int(total_marks)
                except:
                    t_marks = 0

                # Create/Update Result
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
                if created:
                    stats['results_created'] += 1
                    print(f"Created Result for {reg_no} - {exam_name}")
                else:
                    stats['results_updated'] += 1
                    print(f"Updated Result for {reg_no} - {exam_name}")
                
                # Create/Update Result Details (Subjects)
                for sub_col in subject_cols:
                    marks_val = row[sub_col]
                    if pd.isna(marks_val) or str(marks_val).strip() == '':
                        continue
                        
                    try:
                        obtained = int(marks_val)
                    except:
                        obtained = 0
                    
                    subject_obj = cache['subjects'][sub_col]
                    
                    detail_obj, detail_created = PLWResultDetail.objects.update_or_create(
                        result=result_obj,
                        subject=subject_obj,
                        defaults={'marks_obtained': obtained}
                    )
                    if detail_created:
                        stats['result_details_created'] += 1
                    else:
                        stats['result_details_updated'] += 1

        except Exception as e:
            print(f"Error processing row {index + 2} (Reg No: {row.get('Reg No')}): {e}")
            import traceback
            traceback.print_exc()

    print("\nImport Completed!")
    print(f"Results Created: {stats['results_created']}, Updated: {stats['results_updated']}")
    print(f"Result Details Created: {stats['result_details_created']}, Updated: {stats['result_details_updated']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import PLW Results Only (for existing profiles)')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    run_import(file_path)
