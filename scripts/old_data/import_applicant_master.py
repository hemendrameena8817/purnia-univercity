"""
Import script for applicant_master.csv
Run from Django shell:
    exec(open('scripts/import_applicant_master.py').read()); import_data()
"""
import csv
import os
from staging.models import StagingApplicantMaster

CSV_PATH = 'old_data/applicant_master.csv'

def clean_value(value):
    if value in ('\\N', '', 'NULL', 'null', None):
        return None
    return str(value).strip() if value else None

def import_data():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return
    
    existing = StagingApplicantMaster.objects.count()
    print(f"Existing records: {existing}")
    
    imported = 0
    errors = []
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            try:
                StagingApplicantMaster.objects.create(
                    csv_id=clean_value(row.get('id')),
                    reg_user_id=clean_value(row.get('reg_user_id')),
                    center=clean_value(row.get('center')),
                    applied_program=clean_value(row.get('applied_program')),
                    first_name=clean_value(row.get('first_name')),
                    mid_name=clean_value(row.get('mid_name')),
                    last_name=clean_value(row.get('last_name')),
                    full_name=clean_value(row.get('full_name')),
                    applied_class=clean_value(row.get('applied_class')),
                    exam_center_code=clean_value(row.get('exam_center_code')),
                    gender=clean_value(row.get('gender')),
                    nationality=clean_value(row.get('nationality')),
                    dob=clean_value(row.get('dob')),
                    dob_in_word=clean_value(row.get('dob_in_word')),
                    blood_group=clean_value(row.get('blood_group')),
                    caste=clean_value(row.get('caste')),
                    second_language=clean_value(row.get('second_language')),
                    univ_regn_no=clean_value(row.get('univ_regn_no')),
                    category=clean_value(row.get('category')),
                    is_general=clean_value(row.get('is_general')),
                    is_physically_challanged=clean_value(row.get('is_physically_challanged')),
                    instruction_mode=clean_value(row.get('instruction_mode')),
                    last_grade=clean_value(row.get('last_grade')),
                    last_board=clean_value(row.get('last_board')),
                    present_status=clean_value(row.get('present_status')),
                    employer_address=clean_value(row.get('employer_address')),
                    comm_address_ref_id=clean_value(row.get('comm_address_ref_id')),
                    perm_address_ref_id=clean_value(row.get('perm_address_ref_id')),
                    institute_code=clean_value(row.get('institute_code')),
                    created_on=clean_value(row.get('created_on')),
                    updated_by=clean_value(row.get('updated_by')),
                    updated_on=clean_value(row.get('updated_on')),
                    religion=clean_value(row.get('religion')),
                    applicant_email=clean_value(row.get('applicant_email')),
                    applicant_landline=clean_value(row.get('applicant_landline')),
                    applicant_mobile=clean_value(row.get('applicant_mobile')),
                    highest_qualification=clean_value(row.get('highest_qualification')),
                    secured_mark=clean_value(row.get('secured_mark')),
                    guardian_name=clean_value(row.get('guardian_name')),
                    marital_status=clean_value(row.get('marital_status')),
                    created_by=clean_value(row.get('created_by')),
                    record_status=clean_value(row.get('record_status')),
                    last_updated=clean_value(row.get('last_updated')),
                    discipline_code=clean_value(row.get('discipline_code')),
                    aadhar_no=clean_value(row.get('aadhar_no')),
                    medium=clean_value(row.get('medium')),
                    applied=clean_value(row.get('applied')),
                    applied_details=clean_value(row.get('applied_details')),
                    application_status=clean_value(row.get('application_status')),
                    differently_abled=clean_value(row.get('differently_abled')),
                )
                imported += 1
                if imported % 5000 == 0:
                    print(f"Imported {imported} records...")
            except Exception as e:
                errors.append(f"Row {imported + 1}: {str(e)}")
                if len(errors) > 10:
                    break
    
    print(f"\n✅ Import completed!")
    print(f"   Imported: {imported} records")
    print(f"   Errors: {len(errors)}")
    if errors[:5]:
        print("   First errors:", errors[:5])
    print(f"   Total in table: {StagingApplicantMaster.objects.count()}")

if __name__ == '__main__':
    import_data()
