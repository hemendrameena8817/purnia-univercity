"""
Import LLB Users and Profiles Only Script

This script imports ONLY users and LLB student profiles from an Excel file.
It does NOT import results - only creates the basic user accounts and profiles.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.llb.import_llb_user_and_profile import run_import
>>> run_import('old_data/llb_student_profiles.xlsx')

OR run directly:
poetry run python scripts/llb/import_llb_user_and_profile.py --file "old_data/llb_profiles.xlsx"

Required Excel Columns:
- Roll Number
- Name of Candidate
- Reg No
- Batch (e.g., 2021-2024)
- Session (e.g., 2021-24)
- College
- Course (e.g., LLB)
- Father Name (optional)
- Mother Name (optional)
- DOB (optional)
- Mobile (optional)
"""

import os
import sys
import pandas as pd
import argparse
from datetime import date, datetime
from django.db import transaction
from django.contrib.auth import get_user_model

# Setup Django if running directly
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    import django
    django.setup()

from llb.models import (
    LLBStudentProfile, LLBBatch, LLBSession, LLBCourse
)
from colleges.models import College

User = get_user_model()

def get_or_create_user(reg_no, full_name):
    """
    Get or create a User based on Registration Number.
    """
    # Try to find by username (Reg No)
    user = User.objects.filter(username=reg_no).first()
    if user:
        return user
    
    first_name = full_name.strip()
    
    # Create new user
    user = User.objects.create_user(
        username=reg_no,
        first_name=first_name,
        last_name="",
        password=reg_no, # Default password is reg no
        current_profile="llb"
    )
    print(f"Created User: {reg_no}")
    return user

def parse_date(date_value):
    """Parse date from various formats"""
    if pd.isna(date_value) or str(date_value).strip() == '':
        return None
    
    try:
        if isinstance(date_value, datetime):
            return date_value.date()
        elif isinstance(date_value, date):
            return date_value
        elif isinstance(date_value, str):
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_value.strip(), fmt).date()
                except ValueError:
                    continue
    except:
        pass
    
    return None

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    
    print("Columns:", df.columns.tolist())
    
    # --- COLUMN VALIDATION ---
    print("\nValidating required columns...")
    required_columns = ['Roll Number', 'Name of Candidate', 'Reg No', 'Batch', 'Session', 'College', 'Course']
    
    # Convert DataFrame columns to exact case-sensitive match
    df_columns = df.columns.tolist()
    missing_columns = []
    
    for required_col in required_columns:
        if required_col not in df_columns:
            missing_columns.append(required_col)
    
    if missing_columns:
        print("\nVALIDATION FAILED! Missing required columns:")
        for col in missing_columns:
            print(f"  - '{col}'")
        print("\nAvailable columns:", df_columns)
        return
    
    print("All required columns found!")
    
    # --- PHASE 1: VALIDATION ---
    print("\nStarting Validation Pass...")
    errors = []
    
    # Cache to avoid duplicate DB lookups
    cache = {
        'colleges': {}, 'sessions': {}, 'batches': {}, 'courses': {}
    }

    for index, row in df.iterrows():
        row_num = index + 2
        
        # Skip empty rows
        if pd.isna(row.get('Roll Number')) and pd.isna(row.get('Reg No')):
            continue
            
        # 1. College
        college_name = str(row['College']).strip()
        if college_name not in cache['colleges']:
            college = College.objects.filter(name__iexact=college_name).first()
            if not college:
                college = College.objects.filter(name__icontains=college_name).first()
            cache['colleges'][college_name] = college
        if not cache['colleges'][college_name]:
            errors.append(f"Row {row_num}: College '{college_name}' not found.")

        # 2. Session
        session_name = str(row['Session']).strip()
        if session_name not in cache['sessions']:
            cache['sessions'][session_name] = LLBSession.objects.filter(name=session_name).first()
        if not cache['sessions'][session_name]:
            errors.append(f"Row {row_num}: Session '{session_name}' not found.")

        # 3. Batch
        batch_name = str(row['Batch']).strip()
        if batch_name not in cache['batches']:
            sess = cache['sessions'].get(session_name)
            if sess:
                cache['batches'][batch_name] = LLBBatch.objects.filter(name=batch_name, session=sess).first()
            else:
                cache['batches'][batch_name] = None
        if not cache['batches'][batch_name]:
            errors.append(f"Row {row_num}: Batch '{batch_name}' not found for session '{session_name}'.")

        # 4. Course
        course_name = str(row.get('Course', 'LLB')).strip()
        if course_name not in cache['courses']:
            cache['courses'][course_name] = LLBCourse.objects.filter(name__iexact=course_name).first()
        if not cache['courses'][course_name]:
            errors.append(f"Row {row_num}: Course '{course_name}' not found.")
            
        # 5. Validate required data
        if pd.isna(row.get('Roll Number')) or str(row['Roll Number']).strip() == '':
            errors.append(f"Row {row_num}: Roll Number is required.")
            
        if pd.isna(row.get('Reg No')) or str(row['Reg No']).strip() == '':
            errors.append(f"Row {row_num}: Reg No is required.")
            
        if pd.isna(row.get('Name of Candidate')) or str(row['Name of Candidate']).strip() == '':
            errors.append(f"Row {row_num}: Name of Candidate is required.")

    if errors:
        print("\nVALIDATION FAILED! Please fix the following errors before re-running:")
        for err in errors[:50]:
            print(f"  - {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors)-50} more errors.")
        return

    print("Validation Successful! All dependencies found. Starting Import...\n")

    # --- PHASE 2: IMPORT ---
    stats = {
        'users_created': 0, 'users_existing': 0,
        'profiles_created': 0, 'profiles_updated': 0
    }

    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                roll_no = str(row['Roll Number']).strip()
                reg_no = str(row['Reg No']).strip()
                name = str(row['Name of Candidate']).strip()
                
                college = cache['colleges'][str(row['College']).strip()]
                session_obj = cache['sessions'][str(row['Session']).strip()]
                batch_obj = cache['batches'][str(row['Batch']).strip()]
                course = cache['courses'][str(row.get('Course', 'LLB')).strip()]
                
                father_name = str(row.get('Father Name', '')).strip() if not pd.isna(row.get('Father Name')) else ""
                mother_name = str(row.get('Mother Name', '')).strip() if not pd.isna(row.get('Mother Name')) else ""
                
                dob = parse_date(row.get('DOB'))
                mobile = str(row.get('Mobile', '')).strip() if not pd.isna(row.get('Mobile')) else ""
                
                # 1. User
                user = get_or_create_user(reg_no, name)
                if user:
                    if user.first_name == name.strip():  # User was just created
                        stats['users_created'] += 1
                    else:
                        stats['users_existing'] += 1
                
                # 2. Student Profile
                student, created = LLBStudentProfile.objects.update_or_create(
                    registration_no=reg_no,
                    defaults={
                        'user': user,
                        'roll_no': roll_no,
                        'father_name': father_name,
                        'mother_name': mother_name,
                        'college': college,
                        'course': course,
                        'batch': batch_obj,
                        'date_of_birth': dob,
                        'mobile': mobile
                    }
                )
                if created:
                    stats['profiles_created'] += 1
                    print(f"Created Profile: {reg_no} - {name}")
                else:
                    stats['profiles_updated'] += 1
                    print(f"Updated Profile: {reg_no} - {name}")

        except Exception as e:
            print(f"Error processing row {index + 2} (Roll: {row.get('Roll Number')}): {e}")
            import traceback
            traceback.print_exc()

    print("\nImport Completed!")
    print(f"Users Created: {stats['users_created']}, Existing: {stats['users_existing']}")
    print(f"Profiles Created: {stats['profiles_created']}, Updated: {stats['profiles_updated']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import LLB Users and Profiles Only')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    run_import(file_path)
