"""
This script imports student profiles from an Excel file.
It creates Users (using Registration No as username/password) and BTechStudentProfile.

Required Excel Columns:
- Roll No
- Registration No
- Branch Code
- Current Year
- Gender
- Student Name
- Father Name
- Mother Name
- Profile Picture (optional, local path)
- Signature (optional, local path)
- Status (REGULAR, SUSPENDED, ALUMNI)
- Batch (e.g., 2021-2025)
- Session (e.g., 2021-22)
- Course (e.g., BTech)
- Institute code (College Code)

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
from scripts.betch.import_btech_students import run_import
>>> run_import('old_data/btech/BTECH_STUDENT_PROFILE.xlsx')
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

from btech.models import (
    BTechStudentProfile, BTechBatch, BTechSession, BTechCourse, BTechBranch
)
from colleges.models import College

User = get_user_model()

def get_or_create_user(reg_no, full_name):
    """
    Get or create a User based on Registration Number.
    """
    reg_no = str(reg_no).strip()
    user = User.objects.filter(username=reg_no).first()
    if user:
        # Update name if user exists
        user.first_name = str(full_name).strip()
        user.save()
        return user, False
    
    first_name = str(full_name).strip()
    
    # Create new user
    user = User.objects.create_user(
        username=reg_no,
        first_name=first_name,
        last_name="",
        password=reg_no,
        current_profile="btech"
    )
    return user, True

def parse_year(year_val):
    """
    Convert 1, 2, 3, 4 or 1ST, 2ND etc to integer
    """
    if pd.isna(year_val):
        return None
    val = str(year_val).strip().upper()
    if '1' in val: return 1
    if '2' in val: return 2
    if '3' in val: return 3
    if '4' in val: return 4
    try:
        return int(val)
    except:
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
    if pd.isna(path_str) or not str(path_str).strip():
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

def parse_date(date_val):
    """
    Safely parse date from Excel/String.
    """
    if pd.isna(date_val) or str(date_val).strip().lower() == 'na':
        return None
    try:
        return pd.to_datetime(date_val).date()
    except:
        return None

def run_import(file_path, media_dir=None):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Reading file: {file_path}")
    if media_dir:
        print(f"Media directory: {media_dir}")
    try:
        # Try to read all sheets or specific one. Assuming sheet 0.
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return
    
    print("Columns found in Excel:", df.columns.tolist())
    
    # Required columns check
    required_cols = [
        'Roll No', 'Registration No', 'Branch Code', 'Current Year', 
        'Gender', 'Student Name', 'Father Name', 'Mother Name',
        'Status', 'Batch', 'Session', 'Course', 'Institute code'
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"Error: Missing required columns: {missing}")
        return

    # --- PHASE 1: VALIDATION ---
    print("\nStarting Validation Pass...")
    errors = []
    
    # Cache to avoid duplicate DB lookups
    cache = {
        'colleges': {}, 'sessions': {}, 'batches': {}, 'courses': {}, 'branches': {}
    }

    processed_rows = []

    for index, row in df.iterrows():
        row_num = index + 2
        
        # 1. Registration No
        reg_no = str(row.get('Registration No', '')).strip()
        if not reg_no or reg_no == 'nan':
            errors.append(f"Row {row_num}: Registration No is required.")
            continue

        # 2. Institute code
        inst_code = str(row.get('Institute code', '')).strip()
        if inst_code not in cache['colleges']:
            college = College.objects.filter(college_code=inst_code).first()
            cache['colleges'][inst_code] = college
        if not cache['colleges'][inst_code]:
            errors.append(f"Row {row_num}: College code '{inst_code}' not found.")

        # 3. Course
        course_name = str(row.get('Course', 'BTech')).strip()
        if course_name not in cache['courses']:
            cache['courses'][course_name] = BTechCourse.objects.filter(name__iexact=course_name).first()
        course_obj = cache['courses'][course_name]
        if not course_obj:
            errors.append(f"Row {row_num}: BTech Course '{course_name}' not found.")

        # 4. Branch Code
        branch_code = str(row.get('Branch Code', '')).strip()
        branch_key = (course_name, branch_code)
        if branch_key not in cache['branches']:
            if course_obj:
                cache['branches'][branch_key] = BTechBranch.objects.filter(code=branch_code, course=course_obj).first()
            else:
                cache['branches'][branch_key] = None
        if not cache['branches'][branch_key]:
            errors.append(f"Row {row_num}: BTech Branch Code '{branch_code}' not found for course '{course_name}'.")

        # 5. Session
        session_name = str(row.get('Session', '')).strip()
        if session_name.lower() == 'na':
            # Handle 'na' if session is not strictly required or if there's a default
            session_obj = None
        else:
            if session_name not in cache['sessions']:
                cache['sessions'][session_name] = BTechSession.objects.filter(name=session_name).first()
            session_obj = cache['sessions'][session_name]
            if not session_obj:
                errors.append(f"Row {row_num}: BTech Session '{session_name}' not found.")

        # 6. Batch
        batch_name = str(row.get('Batch', '')).strip()
        if batch_name not in cache['batches']:
            if session_obj:
                cache['batches'][batch_name] = BTechBatch.objects.filter(name=batch_name, session=session_obj).first()
            else:
                # If no session, try finding batch by name only?
                cache['batches'][batch_name] = BTechBatch.objects.filter(name=batch_name).first()
                
        if not cache['batches'][batch_name]:
            errors.append(f"Row {row_num}: BTech Batch '{batch_name}' not found.")

        processed_rows.append(row)

    if errors:
        print("\nVALIDATION FAILED!")
        for err in errors[:50]:
            print(f"  - {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more errors.")
        return

    print(f"Validation Successful! Found {len(processed_rows)} valid rows. Starting Import...\n")

    # --- PHASE 2: IMPORT ---
    stats = {
        'users_created': 0, 'users_updated': 0,
        'profiles_created': 0, 'profiles_updated': 0
    }

    for index, row in enumerate(processed_rows):
        total_index = index + 2
        try:
            with transaction.atomic():
                reg_no = str(row['Registration No']).strip()
                name = str(row['Student Name']).strip()
                roll_no = str(row.get('Roll No', '')).strip() if not pd.isna(row.get('Roll No')) else ""
                
                course_name = str(row.get('Course', 'BTech')).strip()
                branch_code = str(row.get('Branch Code', '')).strip()
                
                college = cache['colleges'][str(row['Institute code']).strip()]
                course = cache['courses'][course_name]
                branch = cache['branches'][(course_name, branch_code)]
                batch_obj = cache['batches'][str(row['Batch']).strip()]
                
                # Session can be None or from cache
                session_name = str(row.get('Session', '')).strip()
                if session_name.lower() == 'na':
                    session_str = ""
                else:
                    session_obj = cache['sessions'].get(session_name)
                    session_str = session_obj.name if session_obj else session_name
                
                father_name = str(row.get('Father Name', '')).strip() if not pd.isna(row.get('Father Name')) else ""
                mother_name = str(row.get('Mother Name', '')).strip() if not pd.isna(row.get('Mother Name')) else ""
                gender = parse_gender(row.get('Gender'))
                year_val = parse_year(row.get('Current Year'))
                status_val = parse_status(row.get('Status'))

                # Additional Fields
                dob = parse_date(row.get('DOB'))
                phone = str(row.get('Phone', '')).strip() if not pd.isna(row.get('Phone')) else ""
                address = str(row.get('Address', '')).strip() if not pd.isna(row.get('Address')) else ""
                aadhar = str(row.get('Aadhar No', '')).strip() if not pd.isna(row.get('Aadhar No')) else ""
                apaar = str(row.get('Apaar Id', '')).strip() if not pd.isna(row.get('Apaar Id')) else ""
                category = str(row.get('Category', '')).strip() if not pd.isna(row.get('Category')) else ""
                adm_date = parse_date(row.get('Admission Date'))
                
                # User creation/update
                user, u_created = get_or_create_user(reg_no, name)
                if u_created: stats['users_created'] += 1
                else: stats['users_updated'] += 1
                
                # Student Profile creation/update
                student, p_created = BTechStudentProfile.objects.update_or_create(
                    registration_no=reg_no,
                    defaults={
                        'user': user,
                        'first_name': name,
                        'roll_no': roll_no,
                        'father_name': father_name,
                        'mother_name': mother_name,
                        'gender': gender,
                        'date_of_birth': dob,
                        'mobile_no': phone,
                        'address': address,
                        'aadhar_no': aadhar,
                        'apaar_id': apaar,
                        'category': category,
                        'admission_date': adm_date,
                        'college': college,
                        'course': course,
                        'branch': branch,
                        'batch': batch_obj,
                        'session_str': session_str,
                        'current_year': year_val,
                        'status': status_val
                    }
                )
                
                # Handle images
                profile_pic_path = clean_file_path(row.get('Profile Picture'))
                signature_path = clean_file_path(row.get('Signature'))
                
                # Auto-lookup by Roll No if media_dir is provided
                if media_dir and roll_no:
                    auto_pic = os.path.join(media_dir, f"{roll_no}_picture.png")
                    auto_sig = os.path.join(media_dir, f"{roll_no}_signature.png")
                    
                    if not profile_pic_path or not os.path.exists(profile_pic_path):
                        if os.path.exists(auto_pic):
                            profile_pic_path = auto_pic
                    
                    if not signature_path or not os.path.exists(signature_path):
                        if os.path.exists(auto_sig):
                            signature_path = auto_sig

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

                if index > 0 and index % 50 == 0:
                    print(f"Processed {index} profiles...")

        except Exception as e:
            print(f"Error processing row {total_index} (Reg: {row.get('Registration No')}): {e}")

    print("\nImport Completed!")
    print(f"Users Created: {stats['users_created']}, Updated: {stats['users_updated']}")
    print(f"Profiles Created: {stats['profiles_created']}, Updated: {stats['profiles_updated']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import BTech Students from Excel (New Format)')
    parser.add_argument('--file', type=str, required=True, help='Path to the Excel file')
    parser.add_argument('--media-dir', type=str, help='Directory containing profile pictures and signatures')
    args = parser.parse_args()
    
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    media_dir = args.media_dir
    if media_dir and not os.path.isabs(media_dir):
        media_dir = os.path.abspath(media_dir)
        
    run_import(file_path, media_dir)
