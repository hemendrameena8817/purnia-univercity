"""
Import MCA Subjects Script

This script imports MCA Semester subjects from an Excel file into the MCASubject model.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.mca.import_mca_sem_subjects import run_import
>>> run_import('old_data/MCA_SUBJECTS.xlsx')

OR run directly:
poetry run python scripts/mca/import_mca_sem_subjects.py --file "old_data/MCA_SUBJECTS.xlsx"

Excel columns required: 
- Name
- Paper code
- Subject code (Optional)
- Semester
- Full marks
- Pass marks
- Credit (Optional)
"""

import os
import sys
import pandas as pd
import argparse
from django.conf import settings

# Setup Django if running directly
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    import django
    django.setup()

from mca_sem.models import MCASubject

def run_import(file_path):
    """
    Main entry point for importing MCA subjects.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    try:
        df = pd.read_excel(file_path)
        # Normalize columns: lowercase and strip whitespace
        df.columns = [str(col).strip().lower() for col in df.columns]
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    print("Normalized Columns found:", df.columns.tolist())
    
    count = 0
    created_count = 0
    updated_count = 0

    for index, row in df.iterrows():
        try:
            # Safely get values using lowercase keys
            name = str(row.get('name', '')).strip()
            paper_code = str(row.get('paper code', '')).strip()
            subject_code = str(row.get('subject code', paper_code)).strip() # Default to paper_code if missing
            
            # Handle potential NaN or non-integer values
            try:
                semester = int(row.get('semester', 1))
            except (ValueError, TypeError):
                semester = 1 # Default

            try:
                full_marks = int(row.get('full marks', 100))
            except (ValueError, TypeError):
                full_marks = 100 # Default
                
            try:
                pass_marks = int(row.get('pass marks', 33))
            except (ValueError, TypeError):
                pass_marks = 33 # Default

            try:
                credit = int(row.get('credit', 0))
            except (ValueError, TypeError):
                credit = 0 # Default
            
            if not name or not paper_code:
                print(f"Row {index + 2}: Skipping due to missing Name or Paper code.")
                continue

            subject, created = MCASubject.objects.update_or_create(
                paper_code=paper_code,
                defaults={
                    'name': name,
                    'subject_code': subject_code,
                    'semester': semester,
                    'full_marks': full_marks,
                    'pass_marks': pass_marks,
                    'credit': credit
                }
            )
            
            if created:
                print(f"Created: {subject}")
                created_count += 1
            else:
                print(f"Updated: {subject}")
                updated_count += 1
            
            count += 1
        except Exception as e:
            print(f"Error processing row {index + 2}: {e}")
            
    print(f"\nTotal Processed: {count}")
    print(f"Created: {created_count}")
    print(f"Updated: {updated_count}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import MCA Subjects from Excel')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    run_import(file_path)
