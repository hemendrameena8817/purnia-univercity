"""
Import PLW Subjects Script

This script imports PLW subjects from an Excel file into the PLWSubject model.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.plw.import_plw_subjects import run_import
>>> run_import('old_data/PLW_PART_I_Subjects_with_code.xlsx')

OR run directly:
poetry run python scripts/plw/import_plw_subjects.py --file "old_data/PLW_PART_I_Subjects_with_code.xlsx"

Excel columns required: Name, Paper code, Full marks, Pass marks
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

from plw.models import PLWSubject

def run_import(file_path):
    """
    Main entry point for importing subjects.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    print("Columns found:", df.columns.tolist())
    
    count = 0
    created_count = 0
    updated_count = 0

    for index, row in df.iterrows():
        try:
            # Safely get values with stripping
            name = str(row['Name']).strip()
            paper_code = str(row['Paper code']).strip()
            
            # Handle potential NaN or non-integer values
            try:
                full_marks = int(row['Full marks'])
            except (ValueError, TypeError):
                full_marks = 100 # Default
                
            try:
                pass_marks = int(row['Pass marks'])
            except (ValueError, TypeError):
                pass_marks = 33 # Default
            
            subject, created = PLWSubject.objects.update_or_create(
                paper_code=paper_code,
                defaults={
                    'name': name,
                    'full_marks': full_marks,
                    'pass_marks': pass_marks
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
    parser = argparse.ArgumentParser(description='Import PLW Subjects from Excel')
    parser.add_argument('--file', type=str, help='Path to the Excel file', 
                        default=r'old_data/PLW_PART_I_Subjects_with_code.xlsx')
    
    args = parser.parse_args()
    
    # Resolve absolute path if needed, or use as provided
    file_path = args.file
    if not os.path.isabs(file_path):
        # Assuming run from project root
        file_path = os.path.abspath(file_path)

    run_import(file_path)
