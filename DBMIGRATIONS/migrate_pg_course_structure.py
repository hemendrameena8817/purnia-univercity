#!/usr/bin/env python
"""
Migration Script: PGCourseStructure (Local DB) → Live DB

Migrates PGCourseStructure records.
Resolves Foreign Keys:
- Department (via code)
- Batch (via name)

Usage:
    python DBMIGRATIONS/migrate_pg_course_structure.py
"""

import os
import sys
import django
import argparse
from django.db import connections

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.conf import settings
from pg.models import PGCourseStructure, PGDepartment, PGBatch

def migrate_course_structure(dry_run=False):
    print("=" * 80)
    print("MIGRATION: PGCourseStructure (Local) → (Live)")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    if 'live' not in settings.DATABASES:
        print("❌ 'live' DB not configured.")
        return

    # 1. Fetch Maps from Live
    print("  → Fetching mapping data from LIVE database...")
    
    # Department
    departments = PGDepartment.objects.using('live').values('id', 'code')
    dept_map = {d['code']: d['id'] for d in departments if d['code']}
    print(f"    - Departments: {len(dept_map)} loaded")
    
    # Batch
    batches = PGBatch.objects.using('live').values('id', 'name')
    batch_map = {b['name']: b['id'] for b in batches if b['name']}
    print(f"    - Batches:     {len(batch_map)} loaded")
    
    # 2. Fetch Local Data
    print("  → Fetching Local PGCourseStructure...")
    local_qs = PGCourseStructure.objects.all().select_related('department', 'batch')
    total = local_qs.count()
    print(f"    Found {total} records.")
    
    to_create = []
    skipped = 0
    
    # 3. Analyze for Bulk Ops
    print(f"  Analysing {total} records for BULK operations...")
    
    # Fetch existing from Live to identify U/C
    # We need to construct a map of unique keys to IDs.
    # Key: (course_code, semester, department_id, batch_id, label)
    # Note: Dealing with NULLs in DB vs None in Python.
    
    print("    Fetching existing PGCourseStructure from Live...")
    live_qs = PGCourseStructure.objects.using('live').values(
        'id', 'course_code', 'course_name', 'semester', 'department_id', 'batch_id', 'label'
    )
    
    existing_map = {}
    for item in live_qs:
        # Key construction logic must match strict uniqueness
        # If course_code is empty, we used course_name as fallback in previous logic.
        # Let's standardize: use course_code if present, else course_name.
        key_code = item['course_code'] if item['course_code'] else item['course_name']
        
        # Tuple key
        key = (
            key_code,
            item['semester'],
            item['department_id'],
            item['batch_id'],
            item['label']
        )
        existing_map[key] = item['id']
        
    print(f"    Mapped {len(existing_map)} existing records.")
    
    to_create = []
    to_update = []
    
    processed = 0
    for obj in local_qs.iterator():
        processed += 1
        
        # FK Resolution
        live_dept_id = dept_map.get(obj.department.code) if (obj.department and obj.department.code) else None
        live_batch_id = batch_map.get(obj.batch.name) if (obj.batch and obj.batch.name) else None
        
        # Construct Key for this object
        key_code = obj.course_code if obj.course_code else obj.course_name
        if not key_code:
            # Skip invalid
            skipped += 1
            print(f"    ⚠ Skipped Local ID {obj.id}: No Code/Name")
            continue
            
        key = (
            key_code,
            obj.semester,
            live_dept_id,
            live_batch_id,
            obj.label
        )
        
        # Prepare Live Object Instance (in memory)
        new_obj = PGCourseStructure(
            course_name=obj.course_name,
            course_short_name=obj.course_short_name,
            course_type=obj.course_type,
            department_id=live_dept_id,
            batch_id=live_batch_id,
            code=obj.code,
            course_code=obj.course_code,
            paper_code=obj.paper_code,
            max_credit=obj.max_credit,
            effective_credit=obj.effective_credit,
            max_marks=obj.max_marks,
            min_marks=obj.min_marks,
            description=obj.description,
            label=obj.label,
            semester=obj.semester,
            json_data=obj.json_data
        )
        
        if key in existing_map:
            # UPDATE
            new_obj.id = existing_map[key]
            to_update.append(new_obj)
        else:
            # CREATE
            to_create.append(new_obj)
            
    # 4. Execute Bulk
    print(f"  Ready to process: {len(to_create)} New, {len(to_update)} Updates.")
    
    created_count = 0
    updated_count = 0
    
    if not dry_run:
        # Create
        if to_create:
            print(f"    Creating {len(to_create)} records...", end="", flush=True)
            try:
                PGCourseStructure.objects.using('live').bulk_create(to_create, batch_size=500, ignore_conflicts=True)
                print(" Done.")
                created_count = len(to_create)
            except Exception as e:
                print(f"\n    ❌ Bulk Create Failed: {e}")
        
        # Update
        if to_update:
            print(f"    Updating {len(to_update)} records...", end="", flush=True)
            try:
                fields = [
                    'course_name', 'course_short_name', 'course_type', 'department_id', 'batch_id',
                    'code', 'course_code', 'paper_code', 'max_credit', 'effective_credit',
                    'max_marks', 'min_marks', 'description', 'label', 'semester', 'json_data'
                ]
                PGCourseStructure.objects.using('live').bulk_update(to_update, fields, batch_size=500)
                print(" Done.")
                updated_count = len(to_update)
            except Exception as e:
                print(f"\n    ❌ Bulk Update Failed: {e}")
    else:
        created_count = len(to_create)
        updated_count = len(to_update)
        print("  [Dry Run] No changes made.")

    print(f"\nMigration Complete.")
    print(f"Created/Ready: {created_count}")
    print(f"Updated/Ready: {updated_count}")
    print(f"Skipped/Error: {skipped}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    if not args.dry_run:
        if input("\nWrite to LIVE DB? (y/n): ").lower() != 'y': return
        
    migrate_course_structure(args.dry_run)

if __name__ == '__main__':
    main()
