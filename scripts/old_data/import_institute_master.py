"""
Import Institute Master Script
===============================

Imports institute master data from Excel file into StagingInstituteMaster table.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
from scripts.old_data.import_institute_master import run_import
run_import()

OR run directly:
poetry run python scripts/old_data/import_institute_master.py
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

from staging.models import StagingInstituteMaster

EXCEL_PATH = 'old_data/institute_master.xlsx'


def clean_value(value):
    """Clean Excel value - convert NaN, \\N, NULL to None"""
    if pd.isna(value):
        return None
    if value in ('\\N', '', 'NULL', 'null'):
        return None
    # Convert to string and strip whitespace
    return str(value).strip() if value else None


def run_import(excel_path=None, sheet=0):
    """
    Import institute master Excel file into staging table.
    
    Args:
        excel_path (str): Path to Excel file (default: old_data/colleges/institute_master_xml.xlsx)
        sheet (int|str): Sheet index or name (default: 0)
    
    Returns:
        dict: Summary with imported count and errors
    """
    file_path = excel_path or EXCEL_PATH
    
    if not os.path.exists(file_path):
        print(f"❌ Error: Excel file not found at {file_path}")
        return {'status': 'failed', 'error': 'File not found'}
    
    print(f"\n📂 Reading Excel file: {file_path}")
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name=sheet)
        print(f"✅ Found {len(df)} rows in Excel file\n")
    except Exception as e:
        print(f"❌ Error reading Excel file: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
    
    # Count existing records
    existing_count = StagingInstituteMaster.objects.count()
    print(f"📊 Existing records in staging table: {existing_count}")
    
    imported = 0
    errors = []
    
    for index, row in df.iterrows():
        try:
            # Create a case-insensitive lookup
            row_data = {k.upper(): v for k, v in row.items()}
            
            StagingInstituteMaster.objects.create(
                institute_id=clean_value(row_data.get('INSTITUTE_ID')),
                institute_code=clean_value(row_data.get('INSTITUTE_CODE')),
                institute_name=clean_value(row_data.get('INSTITUTE_NAME')),
                principal=clean_value(row_data.get('PRINCIPLE')),
                short_name=clean_value(row_data.get('SHORT_NAME')),
                website_address=clean_value(row_data.get('WEBSITE_ADDRESS')),
                contact_number=clean_value(row_data.get('CONTACT_NUMBER')),
                institute_address=clean_value(row_data.get('INSTITUTE_ADDRESS'))
            )
            imported += 1
            
            if imported % 10 == 0:
                print(f"⏳ Processed {imported} rows...")
                
        except Exception as e:
            error_msg = f"Row {index + 2}: {str(e)}"
            errors.append(error_msg)
            print(f"⚠️  {error_msg}")
    
    print(f"\n{'='*60}")
    print(f"✅ Import completed!")
    print(f"{'='*60}")
    print(f"   Imported: {imported} records")
    print(f"   Errors: {len(errors)}")
    
    if errors and len(errors) <= 10:
        print("\n⚠️  Error details:")
        for err in errors:
            print(f"  - {err}")
    elif errors:
        print(f"\n⚠️  First 10 errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        print(f"  ... and {len(errors) - 10} more errors")
    
    # Show total count
    total = StagingInstituteMaster.objects.count()
    print(f"\n📊 Total records in staging table: {total}")
    print(f"   New records added: {total - existing_count}\n")
    
    return {
        'status': 'completed',
        'imported': imported,
        'errors': len(errors),
        'total': total
    }


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Importing Institute Master Data")
    print("="*60 + "\n")
    
    run_import()

