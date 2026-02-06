"""
BTech Student Assessment Import Script
====================================
This script imports student marks (assessments) from the BTech Student Details Excel file.
It maps END_TERM to 'ESE' and LAB/MID_TERM to 'CIA'.

Usage:
1. Run: poetry run python scripts/betch/import_betch_student_assessments.py --file "path/to/excel.xlsx"
"""

import os
import sys
import django
import pandas as pd
import argparse
from django.db import transaction
from django.contrib.auth import get_user_model

# Setup Django environment
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    django.setup()

from btech.models import (
    BTechStudentProfile, 
    BTechCourseStructure, 
    BTechStudentAssessment, 
    BTechExam,
    BTechExamSchedule,
    BTechSemesterRegistration,
    BTechBatch,
    BTechCourse,
    BTechSession
)
from colleges.models import College

User = get_user_model()

def normalize_semester(sem):
    """Normalize semester values to simple digits (1, 2, 3...)"""
    if pd.isna(sem): return None
    s = str(sem).strip().upper()
    if 'SEM' in s:
        s = s.replace('SEMESTER', '').replace('SEM', '').replace('-', '').strip()
    roman_map = {'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5', 'VI': '6', '1ST': '1', '2ND': '2', '3RD': '3', '4TH': '4'}
    for k, v in roman_map.items():
        if s == k: return v
    # Handle cases like "1ST SEMESTER" -> "1"
    import re
    match = re.search(r'\d+', s)
    if match: return match.group()
    return s

def get_or_create_user(reg_no, full_name):
    """
    Get or create a User based on Registration Number. Match import_mca_students.py logic.
    """
    user = User.objects.filter(username=reg_no).first()
    if user:
        user.first_name = full_name.strip()
        user.save()
        return user, False
    
    # Create new user
    user = User.objects.create_user(
        username=reg_no,
        first_name=full_name.strip(),
        last_name="",
        password=reg_no, 
        current_profile="btech"
    )
    print(f"Created User: {reg_no}")
    return user, True

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

    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    # --- PHASE 1: VALIDATION & CACHING ---
    print("\nStarting Validation & Caching Pass...")
    errors = []
    cache = {
        'colleges': {}, 'sessions': {}, 'batches': {}, 'courses': {}
    }

    for index, row in df.iterrows():
        row_num = index + 2
        
        # 1. College
        inst_code = str(row.get('Institute code', '')).strip()
        if inst_code and inst_code != 'nan' and inst_code not in cache['colleges']:
            college = College.objects.filter(college_code=inst_code).first()
            cache['colleges'][inst_code] = college
            if not college:
                errors.append(f"Row {row_num}: College '{inst_code}' not found.")

        # 2. Session
        sess_name = str(row.get('Session', '')).strip()
        if sess_name and sess_name != 'nan' and sess_name not in cache['sessions']:
            session = BTechSession.objects.filter(name=sess_name).first()
            cache['sessions'][sess_name] = session
            if not session:
                errors.append(f"Row {row_num}: Session '{sess_name}' not found.")

        # 3. Batch
        batch_name = str(row.get('Batch', '')).strip()
        if batch_name and batch_name != 'nan' and batch_name not in cache['batches']:
            batch = BTechBatch.objects.filter(name=batch_name).first()
            cache['batches'][batch_name] = batch
            if not batch:
                errors.append(f"Row {row_num}: Batch '{batch_name}' not found.")

        # 4. Course
        course_name = str(row.get('Course', 'BTech')).strip()
        if course_name and course_name != 'nan' and course_name not in cache['courses']:
            course = BTechCourse.objects.filter(name__icontains=course_name).first()
            cache['courses'][course_name] = course
            if not course:
                errors.append(f"Row {row_num}: Course '{course_name}' not found.")

    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} errors)!")
        for err in errors[:20]:
            print(f"  - {err}")
        return

    print("Validation Successful! Starting Import...")

    stats = {
        'rows_processed': 0,
        'records_created': 0,
        'records_updated': 0,
        'students_created': 0,
        'sem_registrations_created': 0,
        'subjects_not_found': 0,
        'errors': 0
    }

    # Helper mapping for labels
    LABEL_MAP = {
        'END_TERM': 'ESE',
        'LAB': 'CIA',
        'MID_TERM': 'CIA'
    }

    for index, row in df.iterrows():
        stats['rows_processed'] += 1
        if index % 50 == 0:
            print(f"Processing row {index}/{len(df)}...")

        # Core Identity
        reg_no = str(row.get('Registration No', '')).strip()
        if not reg_no or reg_no == 'nan': continue

        roll_no = str(row.get('Roll No', '')).strip()
        full_name = str(row.get('Student Name', '')).strip()
        father_name = str(row.get('Father Name', '')).strip()
        mother_name = str(row.get('Mother Name', '')).strip()
        
        # Paper Details
        subject_code = str(row.get('Subject Code', '')).strip()
        subject_name = str(row.get('Subject Name', '')).strip()
        status_val = str(row.get('Status', '')).strip()
        semester_val = normalize_semester(row.get('Semester', ''))
        
        # Context
        exam_name = str(row.get('Exam', '')).strip()
        batch_col = str(row.get('Batch', '')).strip()
        session_col = str(row.get('Session', '')).strip()
        course_col = str(row.get('Course', 'BTech')).strip()
        final_result = str(row.get('Final Results', '')).strip().upper()
        
        # Marks
        marks_obt = row.get('Mark Obtained')
        max_marks = row.get('Maximum Marks')

        # Exam Type mapping
        exam_type_raw = str(row.get('Exam Type', 'REGULAR')).strip().upper()
        if 'BACK' in exam_type_raw: exam_type_val = 'BACK'
        elif 'IMPROVEMENT' in exam_type_raw: exam_type_val = 'IMPROVEMENT'
        else: exam_type_val = 'REGULAR'

        # Label Mapping
        label = LABEL_MAP.get(status_val)
        if not label: continue

        try:
            with transaction.atomic():
                # 1. Get/Create Student Profile (Match profiles script logic)
                student = BTechStudentProfile.objects.filter(registration_no=reg_no).first()
                if not student:
                    user, _ = get_or_create_user(reg_no, full_name)
                    
                    college = cache['colleges'].get(str(row.get('Institute code', '')).strip())
                    batch_obj = cache['batches'].get(batch_col)
                    btech_course = cache['courses'].get(course_col)

                    student = BTechStudentProfile.objects.create(
                        user=user,
                        registration_no=reg_no,
                        roll_no=roll_no if roll_no != 'nan' else None,
                        first_name=full_name,
                        father_name=father_name if father_name != 'nan' else None,
                        mother_name=mother_name if mother_name != 'nan' else None,
                        college=college,
                        batch=batch_obj,
                        session_str=session_col,
                        course=btech_course,
                        current_semester=int(semester_val) if semester_val and semester_val.isdigit() else None
                    )
                    stats['students_created'] += 1

                # 2. Get Course Structure (Syllabus) for Pass Marks
                course_struct = BTechCourseStructure.objects.filter(
                    course_code=subject_code,
                    semester=semester_val,
                    label=label
                ).first()
                
                pass_marks = course_struct.min_marks if course_struct else 0
                if not course_struct:
                    stats['subjects_not_found'] += 1

                # 3. Handle Attendance
                attendance = "Present"
                if str(marks_obt).upper() in ['ABSENT', 'A', 'ABS']:
                    attendance = "Absent"
                    marks_obt = 0
                
                try:
                    marks_obt_val = float(marks_obt) if not pd.isna(marks_obt) else 0
                    max_marks_val = float(max_marks) if not pd.isna(max_marks) else (course_struct.max_marks if course_struct else 0)
                except:
                    marks_obt_val = 0
                    attendance = "Absent"

                # 4. Create/Update Assessment
                assessment, created = BTechStudentAssessment.objects.update_or_create(
                    student=student,
                    course_code=subject_code,
                    semester=semester_val,
                    label=label,
                    exam_type=exam_type_val,
                    defaults={
                        'course_name': subject_name,
                        'course_type': course_col,
                        'session': session_col,
                        'batch': student.batch,
                        'college_code': student.college.college_code if student.college else str(row.get('Institute code', '')).strip(),
                        'attendance': attendance,
                        'ind_max_marks': int(max_marks_val),
                        'ind_pass_marks': pass_marks,
                        'ind_marks_obtained': marks_obt_val,
                        'ind_is_absent': attendance == "Absent",
                        'sem_result': final_result,
                        'json_data': {
                            'exam_name_from_excel': exam_name,
                            'original_status': status_val
                        }
                    }
                )

                if created: stats['records_created'] += 1
                else: stats['records_updated'] += 1

                # 5. Update Registration
                if semester_val and semester_val.isdigit():
                    _, r_created = BTechSemesterRegistration.objects.get_or_create(
                        student=student,
                        sem=int(semester_val),
                        session=session_col,
                        defaults={'status': 'APPROVED', 'exam_eligible': True}
                    )
                    if r_created: stats['sem_registrations_created'] += 1

        except Exception as e:
            print(f"Error on row {index} (Reg No: {reg_no}): {e}")
            stats['errors'] += 1

    print("\nImport completed!")
    print(f"Final Statistics: {stats}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import BTech Student Assessments')
    parser.add_argument('--file', type=str, required=True, help='Path to Excel file')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    run_import(file_path)
