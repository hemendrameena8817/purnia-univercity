"""
Script to import institute_master.csv into StagingInstituteMaster table.

Usage:
    poetry run python manage.py shell < scripts/import_institute_master.py
    
Or run from Django shell:
    exec(open('scripts/import_institute_master.py').read())
"""
import csv
import os
import django

# Setup Django if running standalone
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    django.setup()

from staging.models import StagingInstituteMaster

CSV_PATH = 'old_data/institute_master.csv'

def clean_value(value):
    """Clean CSV value - convert \\N to None"""
    if value in ('\\N', '', 'NULL', 'null'):
        return None
    return value.strip() if value else None

def import_institute_master():
    """Import institute_master.csv into staging table"""
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return
    
    # Count existing records
    existing_count = StagingInstituteMaster.objects.count()
    print(f"Existing records in staging: {existing_count}")
    
    imported = 0
    errors = []
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        # CSV is tab-separated based on the file
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            try:
                StagingInstituteMaster.objects.create(
                    institute_id=clean_value(row.get('institute_id')),
                    institute_code=clean_value(row.get('institute_code')),
                    institute_name=clean_value(row.get('institute_name')),
                    institute_type=clean_value(row.get('institute_type')),
                    website_address=clean_value(row.get('website_address')),
                    contact_number=clean_value(row.get('contact_number')),
                    institute_address=clean_value(row.get('institute_address')),
                    location=clean_value(row.get('location')),
                    logo_url=clean_value(row.get('logo_url')),
                    image_url=clean_value(row.get('image_url')),
                    enrollment_process=clean_value(row.get('enrollment_process')),
                    admin_name=clean_value(row.get('admin_name')),
                    admin_user_name=clean_value(row.get('admin_user_name')),
                    affiliated_year=clean_value(row.get('affiliated_year')),
                    created_by=clean_value(row.get('created_by')),
                    created_on=clean_value(row.get('created_on')),
                    updated_by=clean_value(row.get('updated_by')),
                    updated_on=clean_value(row.get('updated_on')),
                    record_status=clean_value(row.get('record_status')),
                    last_update=clean_value(row.get('last_update')),
                )
                imported += 1
            except Exception as e:
                errors.append(f"Row {imported + 1}: {str(e)}")
    
    print(f"\n✅ Import completed!")
    print(f"   Imported: {imported} records")
    print(f"   Errors: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for err in errors[:10]:  # Show first 10 errors
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    # Show total count
    total = StagingInstituteMaster.objects.count()
    print(f"\nTotal records in staging table: {total}")

if __name__ == '__main__':
    import_institute_master()
