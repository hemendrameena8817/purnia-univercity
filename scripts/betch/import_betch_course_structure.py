"""
BTech Course Structure Import Script
===================================
This script imports the BTech Course Structure (Syllabus) from an Excel file.
It adds a strict validation pass before any database writes.

Command to run:
1. Run: poetry run python manage.py shell
2. Paste:
   from scripts.betch.import_betch_course_structure import run_import
run_import(r"old_data/btech/BTECH_COURSE_STRUCTURE.xlsx")

Excel Column Mapping (Positional):
0: Branch
1: Year
2: Subject code
3: Paper Name
4: Theory Full Marks
5: Theory Pass Marks
6: Periodical Exam Full Marks
7: Periodical Exam Pass Marks
8: Sessional Full Marks
9: Sessional Pass Marks
"""

import os
import django
import pandas as pd
import argparse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from btech.models import (
    BTechCourse, BTechBranch, BTechCourseStructure, BTechCommonCourseStructure
)

def normalize_year_to_sem(year_str):
    s = str(year_str).strip().upper()
    if '1' in s: return "1"
    if '2' in s: return "2"
    if '3' in s: return "3"
    if '4' in s: return "4"
    return s

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

    # --- PHASE 1: VALIDATION PASS ---
    print("\nStarting Validation Pass...")
    validation_errors = []
    rows_to_process = []

    for index, row in df.iterrows():
        row_num = index + 2  # Excel row number
        
        # 1. Skip obvious headers or empty rows
        branch_val = str(row.iloc[0]).strip()
        if branch_val == 'Branch' or branch_val == 'nan' or not branch_val:
            continue
            
        course_code = str(row.iloc[2]).strip()
        if not course_code or course_code == 'nan' or course_code == 'Subject code':
            continue

        paper_name = str(row.iloc[3]).strip()
        if not paper_name or paper_name == 'nan':
            validation_errors.append(f"Row {row_num}: Paper Name is missing.")
            continue

        # 2. Check for at least one valid mark component
        has_marks = False
        components = [
            {'label': 'THEORY', 'fm': row.iloc[4], 'pm': row.iloc[5]},
            {'label': 'PERIODICAL', 'fm': row.iloc[6], 'pm': row.iloc[7]},
            {'label': 'SESSIONAL', 'fm': row.iloc[8], 'pm': row.iloc[9]},
        ]
        
        valid_components = []
        for comp in components:
            fm = comp['fm']
            if not pd.isna(fm) and str(fm).strip() != "":
                try:
                    fm_val = float(fm)
                    if fm_val > 0:
                        has_marks = True
                        pm = comp['pm']
                        pm_val = float(pm) if not pd.isna(pm) else 0
                        valid_components.append({
                            'label': comp['label'],
                            'fm': fm_val,
                            'pm': pm_val
                        })
                except (ValueError, TypeError):
                    validation_errors.append(f"Row {row_num}: Invalid Full Marks '{fm}' for {comp['label']}.")

        if not has_marks:
            validation_errors.append(f"Row {row_num}: No valid marks (Theory/Periodical/Sessional) found for {course_code}.")
        else:
            rows_to_process.append({
                'branch': branch_val,
                'year': normalize_year_to_sem(row.iloc[1]),
                'code': course_code,
                'name': paper_name,
                'components': valid_components
            })

    if validation_errors:
        print("\n!!! VALIDATION FAILED - IMPORT ABORTED !!!")
        print(f"Total Errors Found: {len(validation_errors)}")
        for err in validation_errors[:20]:
            print(f"  - {err}")
        if len(validation_errors) > 20:
            print(f"  ... and {len(validation_errors) - 20} more errors.")
        return

    print(f"Validation Successful! Found {len(rows_to_process)} papers to import.\n")

    # --- PHASE 2: IMPORT PASS ---
    print("Starting Database Update...")
    from django.db import transaction
    
    stats = {'created': 0, 'updated': 0}

    # Get/Create default BTech Course
    btech_course, _ = BTechCourse.objects.get_or_create(
        name="BTech", defaults={'duration_years': 4}
    )

    try:
        with transaction.atomic():
            for data in rows_to_process:
                # 1. Branch
                branch, _ = BTechBranch.objects.get_or_create(
                    name=data['branch'], course=btech_course
                )

                total_fm = 0
                for comp in data['components']:
                    total_fm += int(comp['fm'])
                    
                    # 2. Detailed Structure
                    obj, created = BTechCourseStructure.objects.update_or_create(
                        course_code=data['code'],
                        label=comp['label'],
                        year=data['year'],
                        branch=branch,
                        defaults={
                            'course_name': data['name'],
                            'max_marks': comp['fm'],
                            'min_marks': comp['pm'],
                        }
                    )
                    if created: stats['created'] += 1
                    else: stats['updated'] += 1

                # 3. Common Structure
                BTechCommonCourseStructure.objects.update_or_create(
                    code=data['code'],
                    year=data['year'],
                    branch=branch,
                    defaults={
                        'course_name': data['name'],
                        'marks': total_fm,
                    }
                )
        
        print(f"Import Finished! Components Created: {stats['created']}, Updated: {stats['updated']}")
    
    except Exception as e:
        print(f"FATAL ERROR during DB write: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import BTech Course Structure (Strict)')
    parser.add_argument('--file', type=str, required=True, help='Path to Excel file')
    args = parser.parse_args()
    run_import(args.file)
