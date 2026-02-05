"""
MCA Course Structure Import Script
=================================
This script imports the global MCA Course Structure (Syllabus) from an Excel file.
It creates multiple assessment records (ESE-Theory, CIA-Theory, Practical) for each paper 
based on the columns provided in the Excel sheet.

Command to run:
1. Run: poetry run python manage.py shell
2. Paste:
   >>> from scripts.mca.import_mca_course_structure import run_import
   >>> run_import(r"old_data/MCA Course Structure Google Sheet.xlsx")

Required Excel Columns:
- Semester
- Paper code
- Subject code
- Paper Name
- ESE (FM)
- ESE (PM)
- CIA (FM)
- CIA (PM)
- Practical (FM)
- Practical (PM)
"""

def normalize_semester(sem):
    """Normalize semester values to simple digits (1, 2, 3...)"""
    s = str(sem).strip().upper()
    if 'SEM' in s:
        s = s.replace('SEMESTER', '').replace('SEM', '').replace('-', '').strip()
    roman_map = {'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5', 'VI': '6'}
    return roman_map.get(s, s)
import os
import django
import pandas as pd
import argparse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from mca_sem.models import MCACourseStructure, MCACommonCourseStructure

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    print(f"Importing Global MCA Course Structure...")

    stats = {
        'rows_in_excel': len(df),
        'records_created': 0,
        'records_updated': 0,
        'errors': 0
    }

    # Iterate over rows
    for index, row in df.iterrows():
        if index % 5 == 0:
            print(f"Processing row {index}/{len(df)}...")
        
        semester = normalize_semester(row['Semester'])
        
        # Use .get() to handle potential case variations in headers
        paper_code_excel = str(row.get('Paper code') or row.get('Paper Code') or '').strip()
        course_code = str(row.get('Subject code') or row.get('Subject Code') or '').strip()
        
        # Use Subject code as base; fall back to Paper code if Subject code is empty
        base_code = course_code if course_code else paper_code_excel
        paper_name = str(row['Paper Name']).strip()
        
        # Determine Course Type 
        course_type = "CC"
        if "CE" in base_code: course_type = "CE"
        elif "SEC" in base_code: course_type = "SEC"
        elif "AECC" in base_code: course_type = "AECC"

        components = [
            {'label': 'ESE', 'fm_col': 'ESE (FM)', 'pm_col': 'ESE (PM)'},
            {'label': 'CIA', 'fm_col': 'CIA (FM)', 'pm_col': 'CIA (PM)'},
            {'label': 'CIA', 'fm_col': 'Practical (FM)', 'pm_col': 'Practical (PM)'},
        ]

        for comp in components:
            fm_val = row.get(comp['fm_col'])
            pm_val = row.get(comp['pm_col'])

            # Only create record if FM exists and is > 0
            if pd.isna(fm_val) or fm_val <= 0:
                continue

            # Handle Pass Marks
            if pd.isna(pm_val):
                pm_val = 0

            try:
                # 1. Update/Create the Paper-level summary (Common Course Structure)
                MCACommonCourseStructure.objects.update_or_create(
                    code=base_code,
                    semester=semester,
                    defaults={
                        'course_name': paper_name,
                        'course_type': course_type,
                        'marks': int(row.get('Total FM', 100)),
                    }
                )

                # 2. Update/Create the detailed component (ESE/CIA/Prac)
                # Uniqueness is now: base_code + label + semester
                obj, created = MCACourseStructure.objects.update_or_create(
                    course_code=base_code,
                    label=comp['label'],
                    semester=semester,
                    defaults={
                        'course_name': paper_name,
                        'course_type': course_type,
                        'max_marks': fm_val,
                        'min_marks': pm_val,
                    }
                )

                if created: stats['records_created'] += 1
                else: stats['records_updated'] += 1
            except Exception as e:
                print(f"Error on row {index} ({base_code}): {e}")
                stats['errors'] += 1

    print("\nImport completed!")
    print(f"Final Statistics: {stats}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Global MCA Course Structure')
    parser.add_argument('--file', type=str, required=True, help='Path to Excel file')

    args = parser.parse_args()
    run_import(args.file)
