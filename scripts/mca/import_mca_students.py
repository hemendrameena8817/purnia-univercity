"""
This script imports student profiles from an Excel file.
It creates Users (using Registration No as username/password) and MCAStudentProfile.

Required Excel Columns:
- Roll No
- Registration No
- Student Name
- Father Name (optional)
- Mother Name (optional)
- Gender
- Current Semester (e.g., 1ST, 4TH)
- Batch (e.g., 2022-24)
- Session (e.g., 2022-23)
- Course (e.g., MCA)
- Institute code (College Code)
- Status (e.g., REGULAR, SUSPENDED, ALUMNI)
- Profile Picture (optional, local path)
- Signature (optional, local path)

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.mca.import_mca_students import run_import
>>> run_import('old_data/MCA_SEM_STUDENT_PROFILE.xlsx')
"""

import os
import sys
import pandas as pd
import argparse
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.files import File

# Setup Django if running directly
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
    import django
    django.setup()

from mca_sem.models import (
    MCAStudentProfile, MCABatch, MCASession, MCACourse
)
from colleges.models import College

User = get_user_model()

def get_or_create_user(reg_no, full_name):
    """
    Get or create a User based on Registration Number.
    """
    user = User.objects.filter(username=reg_no).first()
    if user:
        # Update name if user exists
        user.first_name = full_name.strip()
        user.save()
        return user, False
    
    first_name = full_name.strip()
    
    # Create new user
    user = User.objects.create_user(
        username=reg_no,
        first_name=first_name,
        last_name="",
        password=reg_no, # Default password is reg no
        current_profile="mca_sem"
    )
    return user, True

def parse_semester(sem_str):
    """
    Convert 1ST, 2ND, 3RD, 4TH to integer 1, 2, 3, 4
    """
    if pd.isna(sem_str):
        return None
    sem_str = str(sem_str).strip().upper()
    if '1' in sem_str: return 1
    if '2' in sem_str: return 2
    if '3' in sem_str: return 3
    if '4' in sem_str: return 4
    return None

def parse_gender(gender_str):
    """
    Convert M/F to Male/Female
    """
    if pd.isna(gender_str):
        return None
    val = str(gender_str).strip().upper()
    if val in ['M', 'MALE']:
        return 'Male'
    if val in ['F', 'FEMALE']:
        return 'Female'
    if val in ['O', 'OTHER']:
        return 'Other'
    return None

def clean_file_path(path_str):
    """
    Clean file paths from Excel (removes file:/// prefix)
    """
    if pd.isna(path_str):
        return None
    path_str = str(path_str).strip()
    if path_str.startswith('file:///'):
        path_str = path_str.replace('file:///', '')
    
    # Replace potential URL encoded spaces
    path_str = path_str.replace('%20', ' ')
    
    # Handle forward/backward slash consistency
    return os.path.normpath(path_str)

def parse_status(status_str):
    """
    Convert Regular/Suspended/Alumni to REGULAR/SUSPENDED/ALUMNI
    """
    if pd.isna(status_str):
        return 'REGULAR'
    val = str(status_str).strip().upper()
    if val in ['REGULAR', 'REG', 'ACTIVE']:
        return 'REGULAR'
    if val in ['SUSPENDED', 'SUSP']:
        return 'SUSPENDED'
    if val in ['ALUMNI', 'ALUM']:
        return 'ALUMNI'
    return 'REGULAR'

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    
    print("Columns:", df.columns.tolist())
    
    # --- PHASE 1: VALIDATION ---
    print("\nStarting Validation Pass...")
    errors = []
    
    # Cache to avoid duplicate DB lookups
    cache = {
        'colleges': {}, 'sessions': {}, 'batches': {}, 'courses': {}
    }

    for index, row in df.iterrows():
        row_num = index + 2
        
        # 1. Registration No
        reg_no = str(row.get('Registration No', '')).strip()
        if not reg_no or reg_no == 'nan':
            errors.append(f"Row {row_num}: Registration No is required.")

        # 2. Institute code
        inst_code = str(row.get('Institute code', '')).strip()
        if inst_code not in cache['colleges']:
            college = College.objects.filter(college_code=inst_code).first()
            cache['colleges'][inst_code] = college
        if not cache['colleges'][inst_code]:
            errors.append(f"Row {row_num}: College code '{inst_code}' not found.")

        # 3. Session
        session_name = str(row.get('Session', '')).strip()
        if session_name not in cache['sessions']:
            cache['sessions'][session_name] = MCASession.objects.filter(name=session_name).first()
        if not cache['sessions'][session_name]:
            # Optional: handle if session doesn't exist? The previous script required it.
            errors.append(f"Row {row_num}: MCA Session '{session_name}' not found.")

        # 4. Batch
        batch_name = str(row.get('Batch', '')).strip()
        if batch_name not in cache['batches']:
            sess = cache['sessions'].get(session_name)
            if sess:
                cache['batches'][batch_name] = MCABatch.objects.filter(name=batch_name, session=sess).first()
            else:
                cache['batches'][batch_name] = None
        if not cache['batches'][batch_name]:
            errors.append(f"Row {row_num}: MCA Batch '{batch_name}' not found.")

        # 5. Course
        course_name = str(row.get('Course', 'MCA')).strip()
        if course_name not in cache['courses']:
            cache['courses'][course_name] = MCACourse.objects.filter(name__iexact=course_name).first()
        if not cache['courses'][course_name]:
            errors.append(f"Row {row_num}: MCA Course '{course_name}' not found.")

    if errors:
        print("\nVALIDATION FAILED!")
        for err in errors[:50]:
            print(f"  - {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more errors.")
        return

    print("Validation Successful! Starting Import...\n")

    # --- PHASE 2: IMPORT ---
    stats = {
        'users_created': 0, 'users_updated': 0,
        'profiles_created': 0, 'profiles_updated': 0
    }

    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                reg_no = str(row['Registration No']).strip()
                name = str(row['Student Name']).strip()
                roll_no = str(row.get('Roll No', '')).strip() if not pd.isna(row.get('Roll No')) else ""
                
                college = cache['colleges'][str(row['Institute code']).strip()]
                session_obj = cache['sessions'][str(row['Session']).strip()]
                batch_obj = cache['batches'][str(row['Batch']).strip()]
                course = cache['courses'][str(row.get('Course', 'MCA')).strip()]
                
                father_name = str(row.get('Father Name', '')).strip() if not pd.isna(row.get('Father Name')) else ""
                mother_name = str(row.get('Mother Name', '')).strip() if not pd.isna(row.get('Mother Name')) else ""
                gender = parse_gender(row.get('Gender'))
                current_sem = parse_semester(row.get('Current Semester'))
                status_val = parse_status(row.get('Status'))
                
                # User creation/update
                user, u_created = get_or_create_user(reg_no, name)
                if u_created: stats['users_created'] += 1
                else: stats['users_updated'] += 1
                
                # Student Profile creation/update
                student, p_created = MCAStudentProfile.objects.update_or_create(
                    registration_no=reg_no,
                    defaults={
                        'user': user,
                        'first_name': name,
                        'roll_no': roll_no,
                        'father_name': father_name,
                        'mother_name': mother_name,
                        'gender': gender,
                        'college': college,
                        'course': course,
                        'batch': batch_obj,
                        'session_str': session_obj.name if session_obj else "",
                        'current_semester': current_sem,
                        'status': status_val
                    }
                )
                
                # Handle images
                profile_pic_path = clean_file_path(row.get('Profile Picture'))
                signature_path = clean_file_path(row.get('Signature'))
                
                if profile_pic_path and os.path.exists(profile_pic_path):
                    with open(profile_pic_path, 'rb') as f:
                        student.profile_image.save(
                            os.path.basename(profile_pic_path),
                            File(f),
                            save=False
                        )
                
                if signature_path and os.path.exists(signature_path):
                    with open(signature_path, 'rb') as f:
                        student.signature.save(
                            os.path.basename(signature_path),
                            File(f),
                            save=False
                        )
                
                student.save()
                
                if p_created: stats['profiles_created'] += 1
                else: stats['profiles_updated'] += 1

                if index % 10 == 0:
                    print(f"Processed {index} rows...")

        except Exception as e:
            print(f"Error processing row {index + 2} (Reg: {row.get('Registration No')}): {e}")

    print("\nImport Completed!")
    print(f"Users Created: {stats['users_created']}, Updated: {stats['users_updated']}")
    print(f"Profiles Created: {stats['profiles_created']}, Updated: {stats['profiles_updated']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import MCA Students from Excel (New Format)')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    run_import(file_path)
