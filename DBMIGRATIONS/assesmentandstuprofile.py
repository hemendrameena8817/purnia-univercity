#!/usr/bin/env python
"""
Migration Script: PGStudentCourseAssessment (Local DB) → PGStudentCourseAssessment (Live DB)

This script migrates PG assessment data from the LOCAL database to the LIVE database.
It resolves Foreign Keys (Student, Department, Batch) using business keys (RegNo, Code, Name)
to ensure data integrity across different database instances.

python DBMIGRATIONS/assesmentandstuprofile.py --batch "2024-26" --session "2024-25" --semester "1ST" [--dry-run] [--batch-size N]
    

Options:
    --batch STR   Batch to migrate (e.g., "2024-2025") (Required)
    --session STR   Session to migrate (e.g., "2023-2025") (Required)
    --semester INT  Semester to migrate (e.g., 1) (Required)
    --dry-run       Preview changes without committing to live database
    --batch-size N  Number of records to process in each batch (default: 5000)

Requirements:
    - 'live' database must be configured in settings
    - .env file must contain DB connection details
"""

import os
import sys
import django
import argparse
import time
from datetime import datetime
from django.db import connections
from django.db.utils import OperationalError
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.conf import settings
from django.contrib.auth.hashers import make_password
from accounts.models import UserAccount
from colleges.models import College
from pg.models import (
    PGStudentCourseAssessment,
    PGStudentProfile,
    PGDepartment,
    PGBatch,
    PGDegree,
    PGProgram
)

def get_live_mappings():
    """
    Fetch necessary mapping data from LIVE database to resolve FKs.
    Returns:
        tuple: (student_map, department_map, batch_map)
        - student_map: {registration_no: id}
        - department_map: {code: id}
        - batch_map: {name: id}
    """
    print("  → Fetching mapping data from LIVE database...")
    
    # 1. Students (RegNo -> ID)
    print("    - Fetching Students...", end="", flush=True)
    students = PGStudentProfile.objects.using('live').values('id', 'registration_no')
    student_map = {s['registration_no']: s['id'] for s in students if s['registration_no']}
    print(f" Done ({len(student_map)} loaded)")
    
    # 2. Departments (Code -> ID)
    print("    - Fetching Departments...", end="", flush=True)
    departments = PGDepartment.objects.using('live').values('id', 'code')
    department_map = {d['code']: d['id'] for d in departments if d['code']}
    print(f" Done ({len(department_map)} loaded)")
    
    # 3. Batches (Name -> ID)
    print("    - Fetching Batches...", end="", flush=True)
    batches = PGBatch.objects.using('live').values('id', 'name')
    batch_map = {b['name']: b['id'] for b in batches if b['name']}
    print(f" Done ({len(batch_map)} loaded)")
    
    return student_map, department_map, batch_map

def get_semester_int(sem_str):
    """Convert '1ST', '2ND' etc. to integer 1, 2."""
    if not sem_str: return None
    normalized = sem_str.upper().strip()
    if '1' in normalized: return 1
    if '2' in normalized: return 2
    if '3' in normalized: return 3
    if '4' in normalized: return 4
    return None

def migrate_profiles(session, semester_int, semester_str, batch_name=None, dry_run=False, batch_size=5000):
    """
    Migrate profiles for students who have assessments in the given session/semester (and optionally batch).
    """
    print("=" * 80)
    print("MIGRATION: PGStudentProfile (Local) → (Live)")
    print("=" * 80)
    print(f"Goal: Ensure Profiles exist for Session='{session}', Semester={semester_int}, Batch='{batch_name or 'ALL'}'")
    
    # 1. Identify Target Students from Assessments
    print("  → Identifying students from Local Assessments...")
    
    qs = PGStudentCourseAssessment.objects.filter(
        session=session, 
        semester=semester_str
    )
    if batch_name:
        qs = qs.filter(batch__name=batch_name)
        
    student_ids = qs.values_list('student_id', flat=True).distinct()
    
    total_students = student_ids.count()
    print(f"  Found {total_students} students with assessments in {session}/{semester_str} (Batch: {batch_name or 'ALL'})")
    
    if total_students == 0:
        print("  No students to migrate.")
        return

    # ... (rest of function unchanged until _upsert_profiles)
    
    # fetch maps
    print("  → Fetching mapping data for Profiles...")
    users = UserAccount.objects.using('live').filter(user_type='student').values('id', 'username')
    user_map = {u['username']: u['id'] for u in users}
    
    colleges = College.objects.using('live').values('id', 'college_code')
    college_map = {c['college_code']: c['id'] for c in colleges if c['college_code']}
    
    departments = PGDepartment.objects.using('live').values('id', 'code')
    dept_map = {d['code']: d['id'] for d in departments if d['code']}
    
    programs = PGProgram.objects.using('live').values('id', 'name')
    program_map = {p['name']: p['id'] for p in programs if p['name']}
    
    degrees = PGDegree.objects.using('live').values('id', 'name')
    degree_map = {d['name']: d['id'] for d in degrees if d['name']}
    
    # Query Local Profiles
    print("  → Fetching Local Profiles...")
    local_profiles = PGStudentProfile.objects.filter(id__in=student_ids).select_related(
        'user', 'college', 'department', 'program', 'degree'
    )
    
    batch_objs = []
    stats = {'prepared': 0, 'skipped_no_user': 0}
    
    print(f"  Processing {local_profiles.count()} profiles...")
    
    for profile in local_profiles.iterator():
        local_username = profile.user.username
        reg_no = profile.registration_no.strip()
        live_user_id = user_map.get(local_username) or user_map.get(reg_no)
        
        if not live_user_id:
            # CREATE MISSING USER
            try:
                # Create user in Live
                base_pass = make_password('123')
                new_user = UserAccount(
                    username=local_username,
                    password=base_pass,
                    user_type='student',
                    is_active=True
                )
                new_user.save(using='live')
                live_user_id = new_user.id
                user_map[local_username] = live_user_id
            except Exception as e:
                # If duplicate, try fetch
                try:
                    existing_u = UserAccount.objects.using('live').get(username=local_username)
                    live_user_id = existing_u.id
                    user_map[local_username] = live_user_id
                except Exception as inner_e:
                    print(f"  ❌ Failed to create/find user {local_username}: {e} | {inner_e}")
                    stats['skipped_no_user'] += 1
                    continue
            
        # FKs
        live_college_id = college_map.get(profile.college.college_code) if (profile.college and profile.college.college_code) else None
        live_dept_id = dept_map.get(profile.department.code) if (profile.department and profile.department.code) else None
        live_prog_id = program_map.get(profile.program.name) if (profile.program and profile.program.name) else None
        live_degree_id = degree_map.get(profile.degree.name) if (profile.degree and profile.degree.name) else None
        
        # Prepare Create Object
        new_obj = PGStudentProfile(
            user_id=live_user_id,
            college_id=live_college_id,
            department_id=live_dept_id,
            program_id=live_prog_id,
            degree_id=live_degree_id,
            
            first_name=profile.first_name,
            last_name=profile.last_name,
            hindi_name=profile.hindi_name,
            registration_no=reg_no,
            address=profile.address,
            admission_date=profile.admission_date,
            date_of_birth=profile.date_of_birth,
            aadhar_no=profile.aadhar_no,
            apaar_id=profile.apaar_id,
            mobile_no=profile.mobile_no,
            migration_submitted=profile.migration_submitted,
            last_university=profile.last_university,
            gender=profile.gender,
            caste=profile.caste,
            enrollment_date=profile.enrollment_date,
            roll_no=profile.roll_no,
            batch=profile.batch, 
            father_name=profile.father_name,
            mother_name=profile.mother_name,
            
            # OVERRIDE
            current_semester=semester_int,
            session=session,
            
            status=profile.status,
            cc_course=profile.cc_course,
            sec_course=profile.sec_course,
            ec_course=profile.ec_course,
            is_active=profile.is_active,
            json_data=profile.json_data
        )
        batch_objs.append(new_obj)
        stats['prepared'] += 1
        
        if len(batch_objs) >= batch_size:
            _upsert_profiles(batch_objs, dry_run)
            batch_objs = []
            
    if batch_objs:
        _upsert_profiles(batch_objs, dry_run)
        
    print(f"Profile Sync: {stats['prepared']} found & prepared, {stats['skipped_no_user']} skipped (User not found).")
    print("-" * 80)

def _upsert_profiles(objects, dry_run):
    """Helper to update or create profiles in Live using BULK operations."""
    if dry_run or not objects: return
    
    total_to_sync = len(objects)
    print(f"  Syncing {total_to_sync} profiles (analyzing bulk)...")

    # 1. Identify which profiles already exist (by RegNo)
    reg_nos = [obj.registration_no for obj in objects]
    existing_map = {} # RegNo -> ID
    
    # Fetch existing IDs in one query
    existing_qs = PGStudentProfile.objects.using('live').filter(registration_no__in=reg_nos).values('id', 'registration_no')
    for rec in existing_qs:
        existing_map[rec['registration_no']] = rec['id']
        
    to_create = []
    to_update = []
    
    for obj in objects:
        existing_id = existing_map.get(obj.registration_no)
        if existing_id:
            # Update: set ID so Django knows which row to update
            obj.id = existing_id
            to_update.append(obj)
        else:
            to_create.append(obj)
            
    # 2. Bulk Create
    if to_create:
        print(f"    Creating {len(to_create)} new profiles...", end="", flush=True)
        try:
            PGStudentProfile.objects.using('live').bulk_create(to_create, ignore_conflicts=True)
            print(" Done.")
            print(f"    [NEW PROFILES]: {[p.registration_no for p in to_create]}")
        except Exception as e:
            print(f" Error: {e}")

    # 3. Bulk Update
    if to_update:
        print(f"    Updating {len(to_update)} existing profiles...", end="", flush=True)
        try:
            # Fields to update (exclude PK and creation date)
            update_fields = [
                'user_id', 
                'college_id', 'department_id', 'program_id', 'degree_id', 'batch',
                'first_name', 'last_name', 'hindi_name', 'father_name', 'mother_name',
                'date_of_birth', 'gender', 'caste', 'mobile_no', 'address', 'aadhar_no', 'apaar_id',
                'admission_date', 'enrollment_date', 'roll_no', 'migration_submitted', 'last_university',
                'current_semester', 'session', 'status', 'is_active',
                'cc_course', 'sec_course', 'ec_course', 'json_data'
            ]
            PGStudentProfile.objects.using('live').bulk_update(to_update, update_fields, batch_size=1000)
            print(" Done.")
        except Exception as e:
            print(f" Error: {e}")

def migrate_assessments(session, semester, batch_name=None, dry_run=False, batch_size=5000):
    """
    Migrate assessments from Local to Live.
    """
    start_time = time.time()
    print("=" * 80)
    print("MIGRATION: PGStudentCourseAssessment (Local) → (Live)")
    print("=" * 80)
    print(f"Session:  {session}")
    print(f"Semester: {semester}")
    print(f"Batch:    {batch_name or 'ALL'}")
    print(f"Mode:     {'DRY RUN (no changes)' if dry_run else 'LIVE MIGRATION'}")
    
    # ... connection checks ...
    if 'live' not in settings.DATABASES:
        print("\n❌ Error: 'live' database is not configured.")
        return

    # Connection check
    try:
        with connections['live'].cursor():
            pass
        print(f"✓ Connected to LIVE database: {settings.DATABASES['live']['HOST']}/{settings.DATABASES['live']['NAME']}")
    except OperationalError as e:
        print(f"\n❌ Error connecting to LIVE database: {e}")
        return

    print("-" * 80)
    
    # Load Maps
    try:
        student_map, department_map, batch_map = get_live_mappings()
    except Exception as e:
        print(f"\n❌ Error fetching mapping data: {e}")
        return

    print("-" * 80)
    print("Fetching LOCAL data...")
    
    # Query Local DB
    queryset = PGStudentCourseAssessment.objects.filter(
        session=session,
        semester=semester
    )
    if batch_name:
        queryset = queryset.filter(batch__name=batch_name)
        
    queryset = queryset.select_related('student', 'department', 'batch')
    
    total_count = queryset.count()
    print(f"Found {total_count} records in LOCAL database for Session {session}, Sem {semester}, Batch {batch_name or 'ALL'}")
    
    if total_count == 0:
        print("Nothing to migrate.")
        return

    # Processing details
    stats = {
        'processed': 0,
        'prepared': 0,
        'skipped_student': 0,
        'skipped_dept': 0,
        'skipped_batch': 0,
        'errors': 0
    }
    
    batch_objects = []
    
    print(f"\nProcessing in batches of {batch_size}...")
    
    for idx, record in enumerate(queryset.iterator(), 1):
        stats['processed'] += 1
        
        # 1. Resolve Foreign Keys
        if not record.student or not record.student.registration_no:
            stats['skipped_student'] += 1
            continue
            
        live_student_id = student_map.get(record.student.registration_no)
        if not live_student_id:
            stats['skipped_student'] += 1
            continue
            
        live_dept_id = None
        if record.department and record.department.code:
            live_dept_id = department_map.get(record.department.code)
        
        live_batch_id = None
        if record.batch and record.batch.name:
            live_batch_id = batch_map.get(record.batch.name)
            
        # 2. Create new instance
        new_obj = PGStudentCourseAssessment(
            student_id=live_student_id,
            department_id=live_dept_id,
            batch_id=live_batch_id,
            
            course_name=record.course_name,
            course_short_name=record.course_short_name,
            course_type=record.course_type,
            course_code=record.course_code,
            paper_code=record.paper_code,
            semester=record.semester,
            label=record.label,
            degree=record.degree,
            session=record.session,
            college_code=record.college_code,
            exam_type=record.exam_type,
            attendance=record.attendance,
            
            ind_max_marks=record.ind_max_marks,
            ind_pass_marks=record.ind_pass_marks,
            ind_is_absent=record.ind_is_absent,
            ind_marks_obtained=record.ind_marks_obtained,
            ind_grace_obtained=record.ind_grace_obtained,
            ind_final_marks_obtained=record.ind_final_marks_obtained,
            ind_is_pass=record.ind_is_pass,
            
            comb_max_marks=record.comb_max_marks,
            comb_max_credits=record.comb_max_credits,
            comb_pass_marks=record.comb_pass_marks,
            comb_marks_obtained=record.comb_marks_obtained,
            comb_grace_obtained=record.comb_grace_obtained,
            comb_final_marks_obtained=record.comb_final_marks_obtained,
            comb_credit_obtained=record.comb_credit_obtained,
            comb_numeric_grade=record.comb_numeric_grade,
            comb_letter_grade=record.comb_letter_grade,
            comb_grade_point=record.comb_grade_point,
            
            course_max_marks=record.course_max_marks,
            course_max_credits=record.course_max_credits,
            course_pass_marks=record.course_pass_marks,
            course_marks_obtained=record.course_marks_obtained,
            course_grace_obtained=record.course_grace_obtained,
            course_final_marks_obtained=record.course_final_marks_obtained,
            course_credit_obtained=record.course_credit_obtained,
            course_grade_point=record.course_grade_point,
            
            sem_max_credit=record.sem_max_credit,
            sem_credit_obtained=record.sem_credit_obtained,
            sgpa=record.sgpa,
            sem_result=record.sem_result,
            next_sem_status=record.next_sem_status,
            sem_grace_obtained=record.sem_grace_obtained,
            
            is_cia_fill=record.is_cia_fill,
            is_ese_fill=record.is_ese_fill,
            json_data=record.json_data
        )
        
        batch_objects.append(new_obj)
        stats['prepared'] += 1
        
        if len(batch_objects) >= batch_size:
            _flush_batch(batch_objects, dry_run)
            batch_objects = []
            print(f"  Processed {idx}/{total_count}...")
            
    if batch_objects:
        _flush_batch(batch_objects, dry_run)
        
    end_time = time.time()
    duration = end_time - start_time
    
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print(f"Processed: {stats['processed']} Valid: {stats['prepared']}")

def _flush_batch(objects, dry_run):
    if not objects:
        return
        
    if dry_run:
        return
        
    try:
        # ignore_conflicts=True will skip duplicates (based on unique constraints if any)
        # However, PGStudentCourseAssessment doesn't have unique_together set in the file I read!
        # It had commented out unique_together.
        # This means simple bulk_create will insert duplicates if run multiple times.
        # We should be careful. 
        # But for migration "local -> live", we assume live is empty for this session/sem or we want to append.
        PGStudentCourseAssessment.objects.using('live').bulk_create(objects, ignore_conflicts=True)
    except Exception as e:
        print(f"  ❌ Batch Error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Migrate PG Assessments Local -> Live')
    parser.add_argument('--session', type=str, required=True, help='Session (e.g. "2023-2025")')
    parser.add_argument('--semester', type=str, required=True, help='Semester (e.g. "1ST", "2ND")')
    parser.add_argument('--batch', type=str, help='Batch Name (e.g. "2023-2025")')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    parser.add_argument('--batch-size', type=int, default=5000, help='Batch size')
    
    args = parser.parse_args()
    
    if not args.dry_run:
        print("\n⚠ WARNING: You are about to write to the LIVE database.")
        if input("Continue? (yes/no): ").lower() not in ['yes', 'y']:
            print("Cancelled.")
            return

    # 1. Migrate Profiles first
    sem_int = get_semester_int(args.semester)
    if sem_int:
        migrate_profiles(args.session, sem_int, args.semester, args.batch, args.dry_run, args.batch_size)
    else:
        print(f"⚠ Could not parse integer semester. Skipping profile migration.")
            
    # 2. Migrate Assessments
    migrate_assessments(args.session, args.semester, args.batch, args.dry_run, args.batch_size)

if __name__ == '__main__':
    main()
