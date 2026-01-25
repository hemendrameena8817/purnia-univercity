"""
Import Colleges Script
======================
Imports college data directly from Excel file into the College table.

HOW TO RUN:
-----------
poetry run python manage.py shell
>>> from scripts.colleges.import_colleges import run_import
>>> run_import()

OR run directly:
poetry run python scripts/import_colleges.py
"""

import pandas as pd
import os
import sys
import django

# Setup Django if running standalone
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
    django.setup()

from colleges.models import College
from university.models import University
from django.db.models import Q

EXCEL_PATH = 'old_data/colleges_master.xlsx'

def clean_value(value):
    """Clean Excel value - convert NaN, \\N, NULL to None"""
    if pd.isna(value):
        return None
    if str(value).strip() in ('\\N', '', 'NULL', 'null', 'nan'):
        return None
    return str(value).strip()

def run_import(excel_path=None, sheet=0):
    """Import colleges from Excel directly to College model"""
    file_path = excel_path or EXCEL_PATH
    
    if not os.path.exists(file_path):
        # Fallback to alternative path if default doesn't exist
        if os.path.exists('old_data/institute_master.xlsx'):
            file_path = 'old_data/institute_master.xlsx'
        else:
            print(f"❌ Error: Excel file not found at {file_path}")
            return {'status': 'failed', 'error': 'File not found'}
    
    print(f"\n📂 Reading Excel file: {file_path}")
    
    try:
        df = pd.read_excel(file_path, sheet_name=sheet)
        print(f"✅ Found {len(df)} rows\n")
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return {'status': 'failed', 'error': str(e)}

    # Ensure valid University exists
    univ, created = University.objects.get_or_create(
        name="Purnea University",
        defaults={'short_name': 'PU'}
    )
    if created:
        print("✅ Created default University: Purnea University")

    imported = 0
    skipped = 0
    errors = []

    for index, row in df.iterrows():
        try:
            # Case-insensitive column lookup
            row_data = {str(k).upper().strip(): v for k, v in row.items()}
            
            # Extract fields
            code = clean_value(row_data.get('INSTITUTE_CODE'))
            name = clean_value(row_data.get('INSTITUTE_NAME'))
            short_name = clean_value(row_data.get('SHORT_NAME'))
            
            if not code and not name:
                print(f"⚠️  Skipping row {index+2}: Missing code and name")
                continue

            # Check for duplicates (Name, Short Name, or Code)
            duplicate_check = Q()
            has_check = False
            
            if name:
                duplicate_check |= Q(name__iexact=name)
                has_check = True
            if short_name:
                duplicate_check |= Q(short_name__iexact=short_name)
                has_check = True
            if code:
                duplicate_check |= Q(college_code=code)
                has_check = True
                
            if has_check and College.objects.filter(duplicate_check).exists():
                print(f"⏩ Skipping {name or code}: Duplicate name/short_name/code found.")
                skipped += 1
                continue

            # Prepare data
            defaults = {
                'name': name,
                'short_name': short_name,
                'college_code': code,
                'principal': clean_value(row_data.get('PRINCIPLE')),
                'address': clean_value(row_data.get('INSTITUTE_ADDRESS')),
                'contact_no': clean_value(row_data.get('CONTACT_NUMBER')),
                'website': clean_value(row_data.get('WEBSITE_ADDRESS')),
                'university': univ,
                'is_active': True,
                # Store extra legacy fields in JSON
                'json_data': {
                    'legacy_id': clean_value(row_data.get('INSTITUTE_ID')),
                    'legacy_type': clean_value(row_data.get('INSTITUTE_TYPE')),
                }
            }

            # Create new record
            College.objects.create(**defaults)
            
            imported += 1
                
            if (imported + skipped) % 10 == 0:
                print(f"⏳ Processed {imported + skipped} colleges...")

        except Exception as e:
            errors.append(f"Row {index+2}: {str(e)}")

    print(f"\n{'='*60}")
    print(f"✅ Import Completed")
    print(f"   Created: {imported}")
    print(f"   Skipped: {skipped}")
    print(f"   Errors:  {len(errors)}")
    print(f"{'='*60}\n")
    
    if errors:
        print("⚠️ Errors:")
        for e in errors[:5]:
            print(f"  - {e}")

if __name__ == '__main__':
    run_import()
