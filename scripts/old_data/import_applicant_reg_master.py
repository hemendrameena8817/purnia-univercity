"""
Import script for applicant_reg_master.csv
Run from Django shell:
    exec(open('scripts/import_applicant_reg_master.py').read()); import_data()
"""
import csv
import os
from staging.models import ApplicantRegMaster

CSV_PATH = 'old_data/applicant_reg_master.csv'

def clean_value(value):
    if value in ('\\N', '', 'NULL', 'null', None):
        return None
    return str(value).strip() if value else None

def import_data():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return
    
    existing = ApplicantRegMaster.objects.count()
    print(f"Existing records: {existing}")
    
    imported = 0
    errors = []
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            try:
                ApplicantRegMaster.objects.create(
                    csv_id=clean_value(row.get('id')),
                    reg_user_id=clean_value(row.get('reg_user_id')),
                    first_name=clean_value(row.get('first_name')),
                    mid_name=clean_value(row.get('mid_name')),
                    last_name=clean_value(row.get('last_name')),
                    dob=clean_value(row.get('dob')),
                    communication_flag=clean_value(row.get('communication_flag')),
                    email_id=clean_value(row.get('email_id')),
                    mobile=clean_value(row.get('mobile')),
                    pin=clean_value(row.get('pin')),
                    applied_program=clean_value(row.get('applied_program')),
                    applied_date=clean_value(row.get('applied_date')),
                    reg_mode=clean_value(row.get('reg_mode')),
                    scrutiny_status=clean_value(row.get('scrutiny_status')),
                    scrutiny_remark=clean_value(row.get('scrutiny_remark')),
                    reg_status=clean_value(row.get('reg_status')),
                    institute_code=clean_value(row.get('institute_code')),
                    created_by=clean_value(row.get('created_by')),
                    created_on=clean_value(row.get('created_on')),
                    updated_by=clean_value(row.get('updated_by')),
                    updated_on=clean_value(row.get('updated_on')),
                    status=clean_value(row.get('status')),
                    last_updated=clean_value(row.get('last_updated')),
                    dob1=clean_value(row.get('dob1')),
                    mode=clean_value(row.get('mode')),
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
    print(f"   Total in table: {ApplicantRegMaster.objects.count()}")

if __name__ == '__main__':
    import_data()
