"""
Import Colleges Script

This script imports/updates Colleges from an Excel file into the College model.

HOW TO RUN:
-----------
poetry run python scripts/colleges/import_colleges.py --file "/courses_data/colleges/INSTITUTE_TABLE_FINAL.xlsx"
"""

import os
import sys
import pandas as pd
import argparse
import django

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from colleges.models import College
from django.db import transaction

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    stats = {'created': 0, 'updated': 0, 'errors': 0}

    def format_code(val):
        if pd.isna(val) or str(val).strip() in ['nan', 'None', '']:
            return None
        s = str(val).strip()
        if s.endswith('.0'):
            return s[:-2]
        return s

    for index, row in df.iterrows():
        try:
            code = format_code(row.get('INSTITUTE_CODE'))
            if not code:
                continue
            
            name = str(row['INSTITUTE_NAME']).strip()
            name_hindi = str(row.get('INSTITUTE_NAME_HINDI', '')).strip()
            name_krutidev = str(row.get('INSTITUTE_NAME_KRUTIDEV', '')).strip()
            center_code = format_code(row.get('CENTER_CODE'))

            with transaction.atomic():
                college, created = College.objects.update_or_create(
                    college_code=code,
                    defaults={
                        'name': name,
                        'college_name_hindi': name_hindi,
                        'college_name_krutidev': name_krutidev,
                        'center_code': center_code,
                    }
                )
                
                if created:
                    stats['created'] += 1
                    print(f"Created: [{code}] {name}")
                else:
                    stats['updated'] += 1
                    print(f"Updated: [{code}] {name}")

        except Exception as e:
            print(f"Error at row {index + 2}: {e}")
            stats['errors'] += 1

    print(f"\nImport Finished!")
    print(f"Created: {stats['created']}")
    print(f"Updated: {stats['updated']}")
    print(f"Errors: {stats['errors']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import Colleges from Excel')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    args = parser.parse_args()
    run_import(args.file)
