"""
MBA Student Assessment Import Script
====================================
Imports student assessments from CSV into StudentCourseAssessment model.
Maps columns from 'old_data/mba/mba_1st_sem_export.csv'.

Usage:
    python manage.py shell
    >>> from scripts.mba.import_mba_student_assessments import run_import
    >>> run_import("old_data/mba/mba_1st_sem_export.csv")
"""

import os
import sys
import pandas as pd
import argparse
import math
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model

# Setup Django environment if run directly
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    import django
    django.setup()

from mba_sem.models import (
    StudentCourseAssessment,
    MBAStudentProfile,
    MBABatch,
    MBACourse,
    MBASemesterRegistration
)
from colleges.models import College

User = get_user_model()

def normalize_semester(sem):
    """Normalize semester values (e.g., '1ST' -> '1', 'I' -> '1')."""
    s = str(sem).strip().upper()
    if 'SEM' in s:
        s = s.replace('SEMESTER', '').replace('SEM', '').replace('-', '').strip()
    
    roman_map = {
        'I': '1', 'II': '2', 'III': '3', 'IV': '4', 
        'V': '5', 'VI': '6', '1ST': '1', '2ND': '2', 
        '3RD': '3', '4TH': '4'
    }
    return roman_map.get(s, s)

def get_or_create_user(reg_no, full_name):
    """Get or create a User based on Registration Number."""
    user = User.objects.filter(username=reg_no).first()
    if user:
        return user
    
    # Create new user
    user = User.objects.create_user(
        username=reg_no,
        first_name=full_name.strip(),
        last_name="",
        password=reg_no, 
        current_profile="mba_sem",
        user_type="student"
    )
    # print(f"Created User: {reg_no}")
    return user

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading CSV file: {file_path}")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print(f"Importing Student Assessments into StudentCourseAssessment...")

    stats = {
        'rows_processed': 0,
        'records_created': 0,
        'records_updated': 0,
        'students_created': 0,
        'errors': 0
    }

    # Label Mappings based on 'status' column
    # END_TERM -> ESE (External Semester Exam)
    # MID_TERM -> CIA (Continuous Internal Assessment)
    LABEL_MAP = {
        'END_TERM': 'ESE', 
        'MID_TERM': 'CIA',
        'LAB': 'CIA' # Assumption if LAB exists
    }

    for index, row in df.iterrows():
        stats['rows_processed'] += 1
        if index % 50 == 0:
            print(f"Processing row {index}/{len(df)}...")

        try:
            # 1. Extract Basic Info
            reg_no = str(row.get('college_reg_no', '')).strip()
            if not reg_no or reg_no.lower() == 'nan':
                continue

            student_name = str(row.get('student_name', '')).strip()
            father_name = str(row.get('fathers_name', '')).strip()
            mother_name = str(row.get('mothers_name', '')).strip()
            roll_no = str(row.get('college_roll_no', '')).strip()
            
            # Semester & Session
            sem_raw = str(row.get('semester_code', '')).strip()
            semester_val = normalize_semester(sem_raw)
            session_val = str(row.get('session_code', '')).strip() # e.g. 2019-20
            
            # Batch
            batch_name = str(row.get('batch_code', '')).strip() # e.g. 2019-21
            
            # Course / Subject
            subject_code = str(row.get('subject_code', '')).strip() # e.g. PUMBA501
            subject_name = str(row.get('subject_name', '')).strip()
            paper_code = str(row.get('paper_code', '')).strip()     # e.g. MBA101
            course_col = str(row.get('course_code', 'MBA')).strip() # e.g. MBA
            
            # Marks & Status
            status_val = str(row.get('status', '')).strip() # END_TERM, MID_TERM
            label = LABEL_MAP.get(status_val)
            if not label:
                # Fallback or skip?
                label = status_val # Use raw if not in map
            
            exam_type_raw = str(row.get('exam_type', 'REGULAR')).strip().upper()
            
            # Marks Parsing
            max_mark_raw = row.get('maximum_mark', 0)
            pass_mark_raw = row.get('pass_mark', 0)
            secured_mark_raw = str(row.get('mark_secured', 0)).strip().upper() # Could be 'AB'
            
            is_absent = False
            marks_obtained = 0.0
            
            if secured_mark_raw in ['AB', 'ABSENT', 'A', 'nan']:
                is_absent = True
                marks_obtained = 0.0
            else:
                try:
                    marks_obtained = float(secured_mark_raw)
                except ValueError:
                    marks_obtained = 0.0

            try:
                max_marks = int(float(max_mark_raw)) if not pd.isna(max_mark_raw) else 0
            except:
                max_marks = 0
                
            try:
                pass_marks = float(pass_mark_raw) if not pd.isna(pass_mark_raw) else 0.0
            except:
                pass_marks = 0.0

            # Result/Pass status
            subject_result = str(row.get('subject_result', '')).strip().upper() # 'P', 'F'?
            is_pass = (subject_result == 'P' or subject_result == 'PASS')

            final_result = str(row.get('final_result', '')).strip() # 'PASS', 'PROMOTED'

            with transaction.atomic():
                # 2. Get/Create Student
                student = MBAStudentProfile.objects.filter(registration_no=reg_no).first()
                if not student:
                    user = get_or_create_user(reg_no, student_name)
                    
                    # Try to find or create batch
                    batch_obj, _ = MBABatch.objects.get_or_create(name=batch_name)
                    
                    # Try to find course (program)
                    mba_course = MBACourse.objects.filter(name__icontains=course_col).first()
                    
                    # Create Profile
                    student = MBAStudentProfile.objects.create(
                        user=user,
                        registration_no=reg_no,
                        roll_no=roll_no if roll_no != 'nan' else None,
                        first_name=student_name,
                        father_name=father_name if father_name != 'nan' else None,
                        mother_name=mother_name if mother_name != 'nan' else None,
                        batch=batch_obj,
                        session_str=session_val,
                        course=mba_course,
                        current_semester=int(semester_val) if semester_val.isdigit() else None
                    )
                    stats['students_created'] += 1

                # 3. Create/Update StudentCourseAssessment
                # Use update_or_create to handle re-runs
                assessment, created = StudentCourseAssessment.objects.update_or_create(
                    student=student,
                    course_code=subject_code, # e.g. PUMBA501 - assume this is unique per course
                    semester=semester_val,
                    label=label,
                    defaults={
                        'paper_code': paper_code,
                        'course_name': subject_name,
                        'course_type': course_col, 
                        'session': session_val,
                        'batch': student.batch, # Use student's batch or lookup again?
                        'exam_type': exam_type_raw,
                        
                        # Individual Marks
                        'ind_max_marks': max_marks,
                        'ind_pass_marks': pass_marks,
                        'ind_marks_obtained': marks_obtained,
                        'ind_is_absent': is_absent,
                        'ind_is_pass': is_pass,
                        
                        # Combined/Other Fields (Optional mapping)
                        # 'comb_max_marks': ... if available in CSV
                        # 'sem_result': final_result # Not a direct field in StudentCourseAssessment, strictly
                    }
                )

                if created:
                    stats['records_created'] += 1
                else:
                    stats['records_updated'] += 1

                # 4. Optional: Update Semester Registration
                if semester_val.isdigit():
                    MBASemesterRegistration.objects.get_or_create(
                        student=student,
                        sem=int(semester_val),
                        session=session_val,
                        defaults={
                            'status': 'APPROVED', 
                            'exam_eligible': True,
                            'result_status': final_result
                        }
                    )

        except Exception as e:
            print(f"Error on row {index} (Reg: {row.get('college_reg_no')}): {e}")
            stats['errors'] += 1

    print("\nImport completed!")
    print(f"Statistics: {stats}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import MBA Student Assessments from CSV')
    parser.add_argument('--file', type=str, required=True, help='Path to CSV file')
    args = parser.parse_args()
    run_import(args.file)
