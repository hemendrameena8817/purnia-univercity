import os
import sys
import django
# python scripts/pg/resultuploading.py
# Setup path to project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from decimal import Decimal
import re
from django.db import transaction
from django.forms.models import model_to_dict
from pg.models import (
    PGStudentCourseAssessment,
    PGStudentProfile,
    PGDepartment,
    PGBatch,
    PGDegree,
    PGProgram
)
from staging.models import PGResultCurrent

def run():
    print("Starting PG Result Upload...")
    
    # Fetch all records from staging
    staging_records = PGResultCurrent.objects.all()
    print(f"Found {staging_records.count()} records in Staging.")
    
    count = 0
    updated_count = 0
    skipped_count = 0
    
    for record in staging_records:
        count += 1
        if count % 100 == 0:
            print(f"Processed {count} records...")
            
        # --- 1. Resolve Foreign Keys ---
        
        # Student
        student = PGStudentProfile.objects.filter(registration_no=record.college_reg_no).first()
        if not student:
            print(f"  Skipping: Student not found for Reg No: {record.college_reg_no}")
            skipped_count += 1
            continue
            
        # Department
        department = PGDepartment.objects.filter(code=record.discipline_code).first()
        if not department:
            # Try finding by name or other means if needed, but sticking to code for now as per plan
             print(f"  Skipping: Department not found for Code: {record.discipline_code}")
             skipped_count += 1
             continue

        # Batch
        batch = PGBatch.objects.filter(name=record.batch_code).first()
        # If batch not found, we might want to proceed or skip. Keeping strictly to plan: resolve or skip/warn.
        # Let's try to find, if not found, we might set it to None or skip. 
        # Plan said "Resolved foreign keys". If critical, skip. 
        # Often batch is needed for filtering. I will skip if not found to be safe.
        if not batch:
             print(f"  Skipping: Batch not found for: {record.batch_code}")
             skipped_count += 1
             continue
             
        # --- 2. Data Cleaning & Mapping ---
        
        # Subject Code Cleaning (remove prefix before first underscore)
        # e.g. "m19_subcode" -> "subcode"
        raw_subject_code = record.course_code # staging.course_code -> target.subject_code (wait, plan said staging.course_code = subject_code... let's re-read prompt)
        # User: "course_code = subject_code inside remove m19_,etc only store after _ this value"
        # Staging: subject_code field exists? Yes `subject_code` field in PGResultCurrent.
        # Wait, the prompt said: "course_code = subject_code".
        # Staging `subject_code` (e.g. m19_PHY101) -> Target `course_code` (PHY101)
        # Staging `course_code` -> Target `degree` (User: "degree=course_code")
        
        # Let's verify Staging fields again.
        # PGResultCurrent has `subject_code` and `course_code`.
        # Plan: "Target course_code = cleaned staging.subject_code"
        # Plan: "Target degree = staging.course_code"
        
        raw_subject_val = record.subject_code 
        cleaned_course_code = raw_subject_val
        if raw_subject_val and '_' in raw_subject_val:
            cleaned_course_code = raw_subject_val.split('_', 1)[1]
            
        # Marks & Absent Status
        mark_secured_val = record.mark_secured
        is_absent = False
        marks_obtained = Decimal(0)
        
        if mark_secured_val == 'AB':
            is_absent = True
            marks_obtained = Decimal(0)
        else:
            try:
                marks_obtained = Decimal(mark_secured_val)
            except (ValueError, TypeError, Exception):
                marks_obtained = Decimal(0)
                
        # Boolean Match for Result
        is_pass = False
        if record.subject_result == 'P':
            is_pass = True
        elif record.subject_result == 'F':
            is_pass = False
        
        # Numeric conversions (handle potential empty strings)
        def to_int(val):
            try:
                return int(float(val))
            except:
                return None
                
        def to_decimal(val):
            try:
                return Decimal(str(val))
            except:
                return None

        # Mapping other fields
        
        # Defaults for finding the record
        # We need a unique way to identify the assessment record.
        # User didn't specify unique keys, but `student` + `semester` + `paper_code` + `label` seems reasonable to avoid duplicates.
        # Or just `student` + `semester` + `paper_code`?
        # Target has `paper_code` field. 
        # Staging `paper_code` = `paper_code`.
        
        
        assessment_data = {
            'course_name': record.subject_name,      # course_namre=subject_name
            'course_code': cleaned_course_code,      # course_code = subject_code (cleaned)
            'paper_code': record.paper_code,         # paper_code = paper_code
            'degree': record.course_code,            # degree=course_code
            'session': record.session_code,          # sission=session_code
            'college_code': record.institute_code,   # college_code=institute_code
            'exam_type': record.exam_type,           # exam_type=exam_type
            
            # Individual Marks
            'ind_max_marks': to_int(record.maximum_mark),            # 'max_mark': 'ind_max_marks' (staging field maximum_mark?) -> Prompt: 'max_mark': 'ind_max_marks'. Staging has `maximum_mark`.
            'ind_pass_marks': to_decimal(record.pass_mark),       # 'pass_mark': 'ind_pass_marks'
            'ind_marks_obtained': marks_obtained,                    # 'mark_secured': 'ind_marks_obtained' (handled)
            'ind_is_absent': is_absent,                              # Derived
            'ind_grace_obtained': Decimal(0), # 'grace_given' not in Staging model. Defaulting to 0.
            'ind_final_marks_obtained': Decimal(0), # 'final_mark' not in Staging. Defaulting to 0.
            'ind_is_pass': is_pass,                                   # 'subject_result': 'ind_is_pass'
            
            # Combined/Subject Marks
            'comb_max_credits': to_int(record.subject_ca),        # 'subject_ca': 'comb_max_credits'
            'comb_marks_obtained': to_decimal(record.subject_total_mark), # 'subject_total_mark': 'comb_marks_obtained'
            'comb_numeric_grade': to_decimal(record.subject_ng),  # 'subject_ng': 'comb_numeric_grade'
            'comb_letter_grade': record.let_grad_sub,             # 'let_grad_sub': 'comb_letter_grade'
            'comb_credit_obtained': to_decimal(record.subject_ce), # 'subject_ce': 'comb_credit_obtained'
            'comb_grade_point': to_decimal(record.subject_gp),    # 'subject_gp': 'comb_grade_point'
            
            # Semester Totals
            'course_grade_point': Decimal(0),    # 'total_gp' not in Staging. Defaulting to 0.
            'sem_max_credit': to_int(record.total_ca),            # 'total_ca': 'sem_max_credit'
            'sem_credit_obtained': to_decimal(record.total_ce),   # 'total_ce': 'sem_credit_obtained'
            'sgpa': to_decimal(record.gpa),                       # 'gpa': 'sgpa'
            'sem_result': record.final_result[:10] if record.final_result else None,                       # 'final_result': 'sem_result'
            
            # Linking fields
            'batch': batch,
            'department': department,
            # 'label': record.status # labl = status
        }
        
        # Serialize staging record to JSON
        record_json = model_to_dict(record)
        if 'uid' in record_json:
            record_json['uid'] = str(record_json['uid']) # Convert UUID to string
        
        assessment_data['json_data'] = record_json
        
        # Using update_or_create. 
        # Key fields to identifying uniqueness: student, semester, paper_code, label?
        # If I use `label` in defaults, it might create duplicates if label changes?
        # Use `label` in lookup.
        
        label_val = record.status 
        
        obj, created = PGStudentCourseAssessment.objects.update_or_create(
            student=student,
            semester=record.semester_code, # semester = semester_code
            paper_code=record.paper_code,
            label=label_val, # labl = status
            defaults=assessment_data
        )
        
        updated_count += 1

    print(f"Done. Processed: {count}, Updated/Created: {updated_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    run()
        
