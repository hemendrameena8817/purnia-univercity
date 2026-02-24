# Run command: python scripts/mca/import_mca_student_assessments.py
import os
import django
import pandas as pd
import sys
from django.db import transaction

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from mca_sem.models import (
    MCAStudentProfile, MCACourse, MCAExam, MCABatch,
    MCACourseStructure, MCAStudentAssessment
)
from mca_sem.choices import ASSESSMENT_LABEL_CHOICES

def map_status_to_label(status):
    """
    Map Excel status to ASSESSMENT_LABEL_CHOICES.
    END_TERM, ESE -> ESE
    MID_TERM, LAB, CIA -> CIA
    """
    if not status:
        return None
    
    status = str(status).upper().strip()
    if status in ['END_TERM', 'ESE']:
        return 'ESE'
    if status in ['MID_TERM', 'LAB', 'CIA']:
        return 'CIA'
    return None

def get_course_structure(row):
    """
    Lookup course structure by Code (primary) or Subject Name (fallback).
    """
    sub_code = str(row.get('Subject Code', '')).strip()
    sub_name = str(row.get('Subject', '')).strip()
    
    # 1. Try exact Code
    structure = MCACourseStructure.objects.filter(course_code=sub_code).first()
    
    # 2. Try cleaned Code (remove spaces)
    if not structure:
        sub_code_cleaned = sub_code.replace(" ", "")
        structure = MCACourseStructure.objects.filter(course_code__iexact=sub_code_cleaned).first()

    # 3. Fallback to Exact Subject Name (if Code failed)
    if not structure and sub_name and sub_name != 'nan':
        structure = MCACourseStructure.objects.filter(course_name__iexact=sub_name).first()
        
    return structure

def import_assessments(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    df = pd.read_excel(file_path)
    print(f"Loaded {len(df)} rows from Excel.")

    # Phase 1: Validation
    print("\nPhase 1: Validating all rows...")
    validation_errors = []
    
    # Cache for validation
    course_cache = {}
    exam_cache = {}
    structure_cache = {}

    for index, row in df.iterrows():
        line = index + 2
        reg_no = str(row.get('Registration No', '')).strip()
        exam_name = str(row.get('Exam', '')).strip()
        course_name = str(row.get('Course', '')).strip()
        sub_code = str(row.get('Subject Code', '')).strip()
        sub_name = str(row.get('Subject', '')).strip()
        status = str(row.get('Status', '')).strip()

        if not reg_no or reg_no == 'nan':
            validation_errors.append(f"Row {line}: Missing Registration No.")
            continue

        # 1. Check Student
        student = MCAStudentProfile.objects.filter(registration_no=reg_no).first()
        if not student:
            validation_errors.append(f"Row {line}: Student not found (Reg: {reg_no}).")

        # 2. Check Course
        if course_name not in course_cache:
            course = MCACourse.objects.filter(name__icontains=course_name).first()
            course_cache[course_name] = course
        
        # 3. Check Exam
        if exam_name not in exam_cache:
            exam = MCAExam.objects.filter(name__icontains=exam_name).first()
            exam_cache[exam_name] = exam
        if not exam_cache[exam_name]:
            validation_errors.append(f"Row {line}: Exam not found (Name: {exam_name}).")

        # 4. Check Course Structure
        structure = get_course_structure(row)
        if not structure:
            validation_errors.append(f"Row {line}: Course Structure not found (Code: '{sub_code}', Name: '{sub_name}').")

        # 5. Check Label
        label = map_status_to_label(status)
        if not label:
            validation_errors.append(f"Row {line}: Invalid Status '{status}'.")

    if validation_errors:
        print(f"\nValidation FAILED with {len(validation_errors)} errors:")
        for err in validation_errors[:20]: # Show first 20
            print(f" - {err}")
        if len(validation_errors) > 20:
            print(f" ... and {len(validation_errors) - 20} more errors.")
        print("\nImport aborted. Please fix the above errors in Excel or DB before retrying.")
        return

    print("Phase 1: Validation PASSED. Proceeding to Import...")

    # Phase 2: Import
    success_count = 0
    error_count = 0

    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                reg_no = str(row.get('Registration No', '')).strip()
                exam_name = str(row.get('Exam', '')).strip()
                course_name = str(row.get('Course', '')).strip()
                status = str(row.get('Status', '')).strip()
                marks_obtained = row.get('Mark Obtained')
                max_marks = row.get('Maximum Marks')
                semester_val = row.get('Semester')

                student = MCAStudentProfile.objects.filter(registration_no=reg_no).first()
                exam = MCAExam.objects.filter(name__icontains=exam_name).first()
                structure = get_course_structure(row)
                
                course = MCACourse.objects.filter(name__icontains=course_name).first() or student.course
                label = map_status_to_label(status)

                assessment, created = MCAStudentAssessment.objects.update_or_create(
                    student=student,
                    exam=exam,
                    course_structure=structure,
                    label=label,
                    defaults={
                        'course': course,
                        'batch': student.batch,
                        'session': student.batch.session.name if student.batch and student.batch.session else None,
                        'semester': str(semester_val) if pd.notnull(semester_val) else None,
                        'ind_marks_obtained': marks_obtained if pd.notnull(marks_obtained) else None,
                        'ind_max_marks': int(max_marks) if pd.notnull(max_marks) else None,
                        'ind_is_absent': pd.isnull(marks_obtained) or str(marks_obtained).upper() == 'ABS',
                        'exam_type': str(row.get('Exam Type', 'REGULAR')).upper(),
                    }
                )
                success_count += 1

            except Exception as e:
                print(f"Row {index+2}: Error during import - {str(e)}")
                error_count += 1
                raise # Rollback transaction on any error during final phase

    print(f"\nImport Summary:")
    print(f"Total Rows: {len(df)}")
    print(f"Successfully Imported/Updated: {success_count}")
    print(f"Errors: {error_count}")

if __name__ == "__main__":
    file_path = r"d:\code\Purnea\pup-umis-backend\courses_data\mca_sem\MCA_SEM_STUDENT_DETAILS_WITH_ASSESMENT.xlsx"
    import_assessments(file_path)
