"""
BTech Student Exam Registration Import Script
=============================================
This script imports student exam registrations (Back Papers) from an Excel file.
It follows a strict validation-first approach.

Command to run:
poetry run python -m scripts.betch.import_student_exam_registration old_data/btech/BTECH_STUDENT_EXAM_REGISTRATION.xlsx
"""

import os
import django
import pandas as pd
from django.db import transaction

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from btech.models import (
    BTechStudentProfile, BTechExam, BTechExamRegistration, BTechCommonCourseStructure
)

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    print(f"Total rows found in Excel: {len(df)}")

    # --- PHASE 1: STRICT VALIDATION ---
    print("\n[PHASE 1] Starting Validation...")
    validation_errors = []
    processed_data = []

    for index, row in df.iterrows():
        row_num = index + 2
        
        reg_no = str(row.get('Registration No', '')).strip()
        exam_name = str(row.get('Exam', '')).strip()
        fees = row.get('Fees')
        reg_status = str(row.get('Status', '')).strip()
        backlog_str = str(row.get('Backlog subjects', '')).strip()

        if not reg_no or reg_no == 'nan':
            validation_errors.append(f"Row {row_num}: Registration No is missing.")
            continue
        
        if not exam_name or exam_name == 'nan':
            validation_errors.append(f"Row {row_num}: Exam name is missing.")
            continue

        # 1. Validate Student
        student = BTechStudentProfile.objects.filter(registration_no=reg_no).first()
        if not student:
            validation_errors.append(f"Row {row_num}: Student with Registration No '{reg_no}' not found.")
        
        # 2. Validate Exam
        exam = BTechExam.objects.filter(name=exam_name).first()
        if not exam:
            validation_errors.append(f"Row {row_num}: Exam '{exam_name}' not found. Please import exam schedule first.")

        # 3. Validate Backlog Subjects
        subject_objs = []
        if backlog_str and backlog_str != 'nan':
            codes = [c.strip() for c in backlog_str.split(',') if c.strip()]
            for code in codes:
                subj = BTechCommonCourseStructure.objects.filter(code=code).first()
                if not subj:
                    validation_errors.append(f"Row {row_num}: Subject Code '{code}' not found in course structure.")
                else:
                    subject_objs.append(subj)
        else:
            validation_errors.append(f"Row {row_num}: No backlog subjects specified for Special Examination.")

        # If everything is okay so far, add to processed data
        if not any(err.startswith(f"Row {row_num}:") for err in validation_errors):
            processed_data.append({
                'student': student,
                'exam': exam,
                'fees': int(fees) if pd.notna(fees) else 0,
                'status': reg_status if reg_status != 'nan' else 'Verified',
                'subjects': subject_objs,
                'row_num': row_num
            })

    if validation_errors:
        print(f"\n!!! VALIDATION FAILED - Total Errors: {len(validation_errors)} !!!")
        for err in validation_errors[:20]: # Show first 20 errors
            print(f"  - {err}")
        if len(validation_errors) > 20:
            print(f"  ... and {len(validation_errors) - 20} more errors.")
        print("\nImport aborted. Please fix the Excel or Database data.")
        return

    print(f"Validation Successful! All {len(processed_data)} entries are ready to import.")

    # --- PHASE 2: IMPORT ---
    print("\n[PHASE 2] Starting Database Import...")
    stats = {'created': 0, 'updated': 0}

    try:
        with transaction.atomic():
            for data in processed_data:
                # Create or Update Exam Registration
                # We identify a registration by (student, exam)
                reg_obj, created = BTechExamRegistration.objects.update_or_create(
                    student=data['student'],
                    exam=data['exam'],
                    defaults={
                        'exam_type': 'BACK', # Since these are special exams
                        'fees': data['fees'],
                        'status': data['status'],
                    }
                )
                
                # Clear and Set many-to-many subjects
                reg_obj.backlog_subjects.set(data['subjects'])
                
                if created:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1
        
        print(f"\nImport Finished Successfully!")
        print(f"  - Registrations Created: {stats['created']}")
        print(f"  - Registrations Updated: {stats['updated']}")

    except Exception as e:
        print(f"FATAL ERROR during Import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Import BTech Student Exam Registrations')
    parser.add_argument('file', type=str, help='Path to Excel file')
    args = parser.parse_args()
    run_import(args.file)
