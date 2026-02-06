import os
import sys
import django
from pathlib import Path
from decimal import Decimal

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import StudentCourseAssessment, UGStudentProfile
from django.db import transaction

print("=" * 100)
print("🔄 UPDATE StudentCourseAssessment Fields from json_data")
print("=" * 100)

# EXACT FIELD MAPPING as specified
FIELD_MAPPING = {
    'max_mark': 'ind_max_marks',
    'pass_mark': 'ind_pass_marks',
    'mark_secured': 'ind_marks_obtained',
    'subject_ca': 'comb_max_credits',
    'subject_total_mark': 'comb_marks_obtained',
    'grace_given': 'ind_grace_obtained',
    'final_mark': 'ind_final_marks_obtained',
    'subject_ng': 'comb_numeric_grade',
    'subject_ce': 'comb_credit_obtained',
    'subject_gp': 'comb_grade_point',
    'total_gp': 'course_grade_point',
    'total_ca': 'sem_max_credit',
    'total_ce': 'sem_credit_obtained',
    'subject_result': 'ind_is_pass',  # P -> True, F -> False
    'final_result': 'sem_result',
}

def safe_decimal(value):
    """Convert to Decimal safely"""
    if value is None or value == '':
        return None
    try:
        val_str = str(value).strip().upper()
        if val_str in ['AB', 'ABS', 'ABSENT', 'NULL', 'NONE']:
            return None
        return Decimal(str(value))
    except:
        return None

def safe_int(value):
    """Convert to int safely"""
    if value is None or value == '':
        return None
    try:
        val_str = str(value).strip().upper()
        if val_str in ['AB', 'ABS', 'ABSENT', 'NULL', 'NONE']:
            return None
        return int(float(value))
    except:
        return None

def convert_subject_result_to_bool(value):
    """Convert P/F to True/False"""
    if value is None or value == '':
        return None
    val_str = str(value).strip().upper()
    return val_str == 'P'

# Configuration
TARGET_BATCH = '2024-28'
TARGET_SEMESTER = '1ST'
BATCH_SIZE = 1000

print(f"\n📊 Configuration:")
print(f"   Target Batch: {TARGET_BATCH}")
print(f"   Target Semester: {TARGET_SEMESTER}")
print(f"   Batch Size: {BATCH_SIZE}")

# Get students from target batch
print(f"\n🔍 Finding students in batch {TARGET_BATCH}...")
students = UGStudentProfile.objects.filter(batch=TARGET_BATCH)
student_count = students.count()
print(f"✅ Found {student_count:,} students in batch {TARGET_BATCH}")

# Get assessments for these students in target semester
print(f"\n🔍 Finding assessment records...")
assessments = StudentCourseAssessment.objects.filter(
    student__batch=TARGET_BATCH,
    semester=TARGET_SEMESTER
).select_related('student')

total_count = assessments.count()
print(f"✅ Found {total_count:,} assessment records for {TARGET_BATCH} / {TARGET_SEMESTER}")

if total_count == 0:
    print("\n⚠️  No records found to update!")
    print("=" * 100)
    sys.exit(0)

# Process and update
print(f"\n🔄 Processing updates in batches of {BATCH_SIZE}...")

updated_count = 0
skipped_no_json = 0
skipped_no_changes = 0
batch_updates = []

# Fields that need updating
update_fields = list(set(FIELD_MAPPING.values()))

for idx, assessment in enumerate(assessments.iterator(chunk_size=BATCH_SIZE), 1):
    # Skip if no json_data
    if not assessment.json_data or not isinstance(assessment.json_data, dict):
        skipped_no_json += 1
        continue
    
    json_data = assessment.json_data
    needs_update = False
    
    # Update each field based on mapping
    for json_key, model_field in FIELD_MAPPING.items():
        if json_key not in json_data:
            continue
        
        json_value = json_data[json_key]
        
        # Skip null/empty values
        if json_value is None or json_value == '':
            continue
        
        # Convert based on target field type
        if model_field == 'ind_is_pass':
            # subject_result: P -> True, F -> False
            new_value = convert_subject_result_to_bool(json_value)
        elif model_field == 'sem_result':
            # final_result: keep as string (PASS/FAIL/PROMOTED)
            new_value = str(json_value).strip().upper()
        elif 'marks' in model_field or 'credit' in model_field or 'grade' in model_field or 'grace' in model_field:
            # Numeric fields -> Decimal
            new_value = safe_decimal(json_value)
        else:
            # Default: keep as is
            new_value = json_value
        
        # Skip if conversion failed
        if new_value is None:
            continue
        
        # Get current value
        current_value = getattr(assessment, model_field, None)
        
        # Only update if different
        if current_value != new_value:
            setattr(assessment, model_field, new_value)
            needs_update = True
    
    if needs_update:
        batch_updates.append(assessment)
        updated_count += 1
    else:
        skipped_no_changes += 1
    
    # Bulk update when batch is full
    if len(batch_updates) >= BATCH_SIZE:
        with transaction.atomic():
            StudentCourseAssessment.objects.bulk_update(
                batch_updates,
                update_fields,
                batch_size=BATCH_SIZE
            )
        print(f"  ✅ Updated batch: {updated_count:,} records updated so far...")
        batch_updates = []
    
    # Progress indicator
    if idx % 5000 == 0:
        print(f"  📊 Processed {idx:,}/{total_count:,} records...")

# Update remaining batch
if batch_updates:
    with transaction.atomic():
        StudentCourseAssessment.objects.bulk_update(
            batch_updates,
            update_fields,
            batch_size=BATCH_SIZE
        )
    print(f"  ✅ Updated final batch")

print("\n" + "=" * 100)
print("📊 UPDATE SUMMARY")
print("=" * 100)
print(f"Batch: {TARGET_BATCH}")
print(f"Semester: {TARGET_SEMESTER}")
print(f"Total records processed: {total_count:,}")
print(f"Records updated: {updated_count:,}")
print(f"Records skipped (no json_data): {skipped_no_json:,}")
print(f"Records skipped (no changes): {skipped_no_changes:,}")

print("\n✅ Update complete!")
print("=" * 100)

# Show sample of updated records
print("\n🔍 VERIFICATION - Sample of 3 updated records:")
print("=" * 100)

sample_records = StudentCourseAssessment.objects.filter(
    student__batch=TARGET_BATCH,
    semester=TARGET_SEMESTER
).select_related('student')[:3]

for record in sample_records:
    print(f"\n📄 {record.student.registration_no} | {record.paper_code} | {record.label}")
    print(f"   ind_marks: {record.ind_marks_obtained}/{record.ind_max_marks} (pass: {record.ind_pass_marks})")
    print(f"   comb_marks: {record.comb_marks_obtained}")
    print(f"   credits: {record.comb_credit_obtained}/{record.comb_max_credits}")
    print(f"   grade: {record.comb_grade_point}")
    print(f"   is_pass: {record.ind_is_pass}")

print("\n" + "=" * 100)
