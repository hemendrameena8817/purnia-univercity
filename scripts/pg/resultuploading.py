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
    print("Starting PG Result Bulk Upload...")
    
    # --- 1. Pre-fetch Foreign Keys (Optimize N+1 Queries) ---
    print("Loading mapping data into memory...")
    
    # Students: RegNo -> ID
    student_map = dict(PGStudentProfile.objects.values_list('registration_no', 'id'))
    print(f"  Loaded {len(student_map)} students.")
    
    # Departments: Code -> ID
    dept_map = dict(PGDepartment.objects.values_list('code', 'id'))
    print(f"  Loaded {len(dept_map)} departments.")
    
    # Batches: Name -> ID
    batch_map = dict(PGBatch.objects.values_list('name', 'id'))
    print(f"  Loaded {len(batch_map)} batches.")
    
    # --- 2. Process Records in Batches ---
    BATCH_SIZE = 5000
    total_count = PGResultCurrent.objects.count()
    print(f"Found {total_count} records in Staging to process.")
    
    processed_count = 0
    created_count = 0
    updated_count = 0
    skipped_count = 0
    
    # Iterate using queryset iterator with chunk_size
    queryset = PGResultCurrent.objects.all().order_by('id')
    
    current_batch_records = []
    
    for record in queryset.iterator(chunk_size=BATCH_SIZE):
        current_batch_records.append(record)
        
        if len(current_batch_records) >= BATCH_SIZE:
            c, u, s = process_batch(current_batch_records, student_map, dept_map, batch_map)
            created_count += c
            updated_count += u
            skipped_count += s
            processed_count += len(current_batch_records)
            print(f"Processed {processed_count}/{total_count} (Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count})")
            current_batch_records = []
            
    # Process remaining records
    if current_batch_records:
        c, u, s = process_batch(current_batch_records, student_map, dept_map, batch_map)
        created_count += c
        updated_count += u
        skipped_count += s
        processed_count += len(current_batch_records)
        
    print(f"\nUpload Complete!")
    print(f"Total Processed: {processed_count}")
    print(f"Created: {created_count}")
    print(f"Updated: {updated_count}")
    print(f"Skipped: {skipped_count}")

def process_batch(records, student_map, dept_map, batch_map):
    """
    Process a list of PGResultCurrent records and bulk upsert PGStudentCourseAssessment.
    """
    to_create = []
    to_update = []
    skipped = 0
    
    # Prepare lookup keys for checking existing records in this batch
    # Key: (student_id, semester, paper_code, label) -> Existing Object ID
    keys_to_check = [] 
    
    # Step 1: Filter valid records and prepare data objects
    valid_data_list = []
    
    for record in records:
        # FK Resolution
        student_id = student_map.get(record.college_reg_no)
        if not student_id:
            # print(f"  Skipping: Student not found for Reg No: {record.college_reg_no}")
            skipped += 1
            continue
            
        dept_id = dept_map.get(record.discipline_code)
        if not dept_id:
             # print(f"  Skipping: Department not found for Code: {record.discipline_code}")
             skipped += 1
             continue

        batch_id = batch_map.get(record.batch_code)
        if not batch_id:
             # print(f"  Skipping: Batch not found for: {record.batch_code}")
             skipped += 1
             continue
             
        # Data Cleaning
        raw_subject_val = record.subject_code 
        cleaned_course_code = raw_subject_val
        if raw_subject_val and '_' in raw_subject_val:
            cleaned_course_code = raw_subject_val.split('_', 1)[1]
            
        # Marks Logic
        mark_secured_val = record.mark_secured
        is_absent = (mark_secured_val == 'AB')
        try:
            marks_obtained = Decimal(0) if is_absent else Decimal(mark_secured_val)
        except:
            marks_obtained = Decimal(0)
            
        is_pass = (record.subject_result == 'P')
        
        # Helpers
        def to_int(val):
            try: return int(float(val))
            except: return None
        def to_decimal(val):
            try: return Decimal(str(val))
            except: return None

        # Prepare Dictionary for Object Creation
        data_dict = {
            'student_id': student_id,
            'department_id': dept_id,
            'batch_id': batch_id,
            
            'course_name': record.subject_name,
            'course_code': cleaned_course_code,
            'paper_code': record.paper_code,
            'degree': record.course_code,
            'session': record.session_code,
            'college_code': record.institute_code,
            'exam_type': record.exam_type,
            'semester': record.semester_code,
            'label': record.status,
            
            # Individual Marks
            'ind_max_marks': to_int(record.maximum_mark),
            'ind_pass_marks': to_decimal(record.pass_mark),
            'ind_marks_obtained': marks_obtained,
            'ind_is_absent': is_absent,
            'ind_grace_obtained': Decimal(0),
            'ind_final_marks_obtained': Decimal(0),
            'ind_is_pass': is_pass,
            
            # Combined Marks
            'comb_max_credits': to_int(record.subject_ca),
            'comb_marks_obtained': to_decimal(record.subject_total_mark),
            'comb_numeric_grade': to_decimal(record.subject_ng),
            'comb_letter_grade': record.let_grad_sub,
            'comb_credit_obtained': to_decimal(record.subject_ce),
            'comb_grade_point': to_decimal(record.subject_gp),
            
            # Semester Totals
            'course_grade_point': Decimal(0),
            'sem_max_credit': to_int(record.total_ca),
            'sem_credit_obtained': to_decimal(record.total_ce),
            'sgpa': to_decimal(record.gpa),
            'sem_result': record.final_result[:10] if record.final_result else None,
            
            # Meta
            'json_data': model_to_dict(record) # This might be slow if large
        }
        
        # Add to list
        valid_data_list.append(data_dict)
        
        # Prepare Q objects for bulk fetching existing
        # We need to find if (student, semester, paper_code, label) exists
        # To do this efficiently for 5000 items:
        # We can fetch ALL existing items matching these criteria in one query.
        
    # Step 2: Identification of Existing Records
    if not valid_data_list:
        return 0, 0, skipped

    # Optimization: Filter existing records by student IDs in this batch
    student_ids_in_batch = set(d['student_id'] for d in valid_data_list)
    
    # potential bottleneck if student has many records, but filtered by semester/paper/label helps.
    # To be safe and correct, we construct a key map from DB
    
    # Query: Filter by students in batch (this is standard practice)
    existing_qs = PGStudentCourseAssessment.objects.filter(
        student_id__in=student_ids_in_batch
    ).values('id', 'student_id', 'semester', 'paper_code', 'label', 'exam_type')
    
    # Build Map: Key -> ID
    existing_map = {}
    for ex in existing_qs:
        key = (ex['student_id'], ex['semester'], ex['paper_code'], ex['label'], ex['exam_type'])
        existing_map[key] = ex['id']
        
    # Step 3: Split into Create and Update
    for data in valid_data_list:
        key = (data['student_id'], data['semester'], data['paper_code'], data['label'], data['exam_type'])
        existing_id = existing_map.get(key)
        
        obj = PGStudentCourseAssessment(**data)
        
        if existing_id:
            obj.id = existing_id
            to_update.append(obj)
        else:
            to_create.append(obj)
            
    # Step 4: Validate and Execute
    
    # Bulk Create
    if to_create:
        PGStudentCourseAssessment.objects.bulk_create(to_create, ignore_conflicts=True)
        
    # Bulk Update
    if to_update:
        fields_to_update = [
            'department_id', 'batch_id', 'course_name', 'course_code', 'degree', 
            'session', 'college_code', 'exam_type', 
            'ind_max_marks', 'ind_pass_marks', 'ind_marks_obtained', 'ind_is_absent', 'ind_is_pass',
            'comb_max_credits', 'comb_marks_obtained', 'comb_numeric_grade', 'comb_letter_grade', 'comb_credit_obtained', 'comb_grade_point',
            'sem_max_credit', 'sem_credit_obtained', 'sgpa', 'sem_result', 'json_data'
        ]
        PGStudentCourseAssessment.objects.bulk_update(to_update, fields_to_update, batch_size=1000)
        
    return len(to_create), len(to_update), skipped

if __name__ == "__main__":
    run()
        
