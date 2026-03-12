"""
Import LLB Results Only Script

This script imports ONLY results for existing LLB student profiles.
It does NOT create users or student profiles - they must already exist.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.llb.import_llb_results_only import run_import
>>> run_import('old_data/llb_results.xlsx')

OR run directly:
poetry run python scripts/llb/import_llb_results_only.py --file "old_data/llb_results.xlsx"

Required Excel Columns:
- Reg No
- LLB Exam
- Result (Status e.g., PASS)
- Total (Total Marks)
- Subject Columns (English-I, etc.)
"""

import os
import sys
import pandas as pd
import argparse
from django.db import transaction

# Setup Django if running directly
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    import django
    django.setup()

from llb.models import (
    LLBStudentProfile, LLBExam, LLBStudentExamResult, LLBStudentAssessment, LLBCourseStructure
)

# Columns that are NOT subjects
NON_SUBJECT_COLUMNS = [
    'Roll Number', 'Name of Candidate', 'Reg No', 'Total', 'Result', 
    'College', 'Batch', 'Session', 'Father Name', 'LLB Exam', 'Exam Center',
    'Mother Name', 'DOB', 'Mobile', 'Course', 'Grace'
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
    required_columns = ['Reg No', 'LLB Exam', 'Result', 'Total']
    
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
        if pd.isna(row.get('Reg No')) and pd.isna(row.get('LLB Exam')):
            continue
            
        # 1. Student Profile (must exist)
        reg_no = str(row['Reg No']).strip()
        if reg_no not in cache['students']:
            student = LLBStudentProfile.objects.filter(registration_no=reg_no).first()
            cache['students'][reg_no] = student
        if not cache['students'][reg_no]:
            errors.append(f"Row {row_num}: Student profile with Reg No '{reg_no}' not found. Please create profile first.")

        # 2. Exam (must exist)
        exam_name = str(row['LLB Exam']).strip()
        if exam_name not in cache['exams']:
            exam = LLBExam.objects.filter(name__iexact=exam_name).first()
            cache['exams'][exam_name] = exam
        if not cache['exams'][exam_name]:
            errors.append(f"Row {row_num}: Exam '{exam_name}' not found in database.")
            
        # 3. Validate required data
        if pd.isna(row.get('Reg No')) or str(row['Reg No']).strip() == '':
            errors.append(f"Row {row_num}: Reg No is required.")
            
        if pd.isna(row.get('LLB Exam')) or str(row['LLB Exam']).strip() == '':
            errors.append(f"Row {row_num}: LLB Exam is required.")
            
        if pd.isna(row.get('Result')) or str(row['Result']).strip() == '':
            errors.append(f"Row {row_num}: Result is required.")
            
        if pd.isna(row.get('Total')):
            errors.append(f"Row {row_num}: Total marks is required.")

        # 4. Subjects (must exist)
        for sub_col in subject_cols:
            subject_name = str(sub_col).strip()
            if subject_name not in cache['subjects']:
                subject = LLBCourseStructure.objects.filter(name__iexact=subject_name).first()
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
        'details_created': 0, 'details_updated': 0
    }

    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                reg_no = str(row['Reg No']).strip()
                exam_name = str(row['LLB Exam']).strip()
                
                student = cache['students'][reg_no]
                exam = cache['exams'][exam_name]
                
                total_marks = int(row['Total'])
                result_status = str(row['Result']).strip()
                exam_center = str(row.get('Exam Center', '')).strip() if not pd.isna(row.get('Exam Center')) else ""
                
                grace_marks = row.get('Grace')
                if pd.isna(grace_marks) or str(grace_marks).strip() == '':
                    grace_marks = None
                else:
                    try:
                        grace_marks = int(grace_marks)
                    except:
                        grace_marks = None
                
                # 1. Result
                result, created = LLBStudentExamResult.objects.update_or_create(
                    student=student,
                    exam=exam,
                    defaults={
                        'total_marks': total_marks,
                        'result_status': result_status,
                        'exam_center': exam_center,
                        'grace': grace_marks
                    }
                )
                
                if created:
                    stats['results_created'] += 1
                    print(f"Created Result: {reg_no} - {exam_name}")
                else:
                    stats['results_updated'] += 1
                    print(f"Updated Result: {reg_no} - {exam_name}")
                
                # 2. Result Details (Subject Marks)
                for subject_col in subject_cols:
                    subject_name = str(subject_col).strip()
                    marks_obtained = row.get(subject_col)
                    
                    if pd.isna(marks_obtained) or marks_obtained == '' or marks_obtained == 0:
                        continue
                    
                    subject = cache['subjects'][subject_name]
                    
                    try:
                        marks_obtained = int(marks_obtained)
                    except:
                        continue
                    
                    detail, created = LLBStudentAssessment.objects.update_or_create(
                        exam_result=result,
                        subject=subject,
                        defaults={'marks_obtained': marks_obtained}
                    )
                    
                    if created:
                        stats['details_created'] += 1
                    else:
                        stats['details_updated'] += 1

        except Exception as e:
            print(f"Error processing row {index + 2} (Reg No: {row.get('Reg No')}): {e}")
            import traceback
            traceback.print_exc()

    print("\nImport Completed!")
    print(f"Results Created: {stats['results_created']}, Updated: {stats['results_updated']}")
    print(f"Details Created: {stats['details_created']}, Updated: {stats['details_updated']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import LLB Results Only')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    run_import(file_path)
