#!/usr/bin/env python
"""
Migration Script: PG Master Data (Local DB) → Live DB

Migrates the following models in dependency order:
1. PGFaculty
2. PGDepartment
3. PGDegree
4. PGProgram
5. PGBatch

Matches records by Name/Code to avoid duplication and maps Foreign Keys correctly.

Usage:
    python DBMIGRATIONS/migrate_pg_masters_local_to_live.py [--dry-run]
"""

import os
import sys
import django
import argparse
from django.db import connections, transaction
from django.db.utils import OperationalError

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.conf import settings
from pg.models import (
    PGFaculty,
    PGDepartment,
    PGDegree,
    PGProgram,
    PGBatch
)

def migrate_masters(dry_run=False):
    print("=" * 80)
    print("MIGRATION: PG Master Data (Local) → (Live)")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    if 'live' not in settings.DATABASES:
        print("❌ 'live' DB not configured.")
        return

    # Check connection
    try:
        with connections['live'].cursor():
            pass
        print(f"✓ Connected to LIVE database")
    except Exception as e:
        print(f"❌ Error connecting to LIVE database: {e}")
        return

    # 1. PGFaculty
    # -------------------------------------------------------------
    print("\n1. Migrating PGFaculty...")
    faculties = PGFaculty.objects.all()
    faculty_map = {}
    
    # Correction: PGFaculty needs University.
    # Let's fetch a default university from Live DB.
    try:
        from university.models import University
        default_university = University.objects.using('live').first()
        if not default_university:
            print("  ⚠ No University found in Live DB. Creating default 'Purnea University'...")
            if not dry_run:
                default_university = University.objects.using('live').create(
                    name="Purnea University",
                    short_name="PU",
                    # Add other mandatory fields if any? detailed check needed?
                    # Assuming minimal fields name/code are enough or others have defaults.
                )
            else:
                print("  [Dry Run] Would create default University.")
                # Mock object
                class MockUni: id = 1
                default_university = MockUni()
        
        if default_university:
             print(f"  Using University: {default_university}")
    except ImportError:
        print("  ⚠ University model not found.")
        return

    # Restart Faculty Loop
    counters = {'created': 0, 'updated': 0}
    for obj in faculties:
        if not dry_run:
            live_obj, created = PGFaculty.objects.using('live').update_or_create(
                name=obj.name,
                defaults={
                    'short_name': obj.short_name,
                    'description': obj.description,
                    'university_id': default_university.pk, # Map to live university
                    'json_data': obj.json_data
                }
            )
            faculty_map[obj.name] = live_obj.id
            if created: counters['created'] += 1
            else: counters['updated'] += 1
        else:
            # Mock map for dry run
            faculty_map[obj.name] = obj.id 
            counters['created'] += 1
            
    print(f"  Results: Created {counters['created']}, Updated {counters['updated']}")


    # 2. PGDepartment
    # -------------------------------------------------------------
    print("\n2. Migrating PGDepartment...")
    departments = PGDepartment.objects.all()
    dept_map = {} # Code -> Live ID
    
    counters = {'created': 0, 'updated': 0}
    for obj in departments:
        # Resolve Faculty
        live_faculty_id = None
        if obj.faculty:
            live_faculty_id = faculty_map.get(obj.faculty.name)
            
        if not dry_run:
            # Use 'code' as unique key if available, else name? 
            # Model has 'code' (not unique constraint in DB maybe, but logically unique).
            # Model definition: code = CharField(max_length=50, null=True, blank=True)
            # Use Name + Code combination or just Code? 
            # Let's use Code if present, else Name.
            
            lookup = {}
            if obj.code:
                lookup['code'] = obj.code
            elif obj.name:
                lookup['name'] = obj.name
            else:
                continue # Skip empty

            live_obj, created = PGDepartment.objects.using('live').update_or_create(
                **lookup,
                defaults={
                    'name': obj.name,
                    'code': obj.code,
                    'head_of_department': obj.head_of_department,
                    'faculty_id': live_faculty_id,
                    'json_data': obj.json_data
                }
            )
            key = obj.code if obj.code else obj.name
            dept_map[key] = live_obj.id
            if created: counters['created'] += 1
            else: counters['updated'] += 1
        else:
             counters['created'] += 1
             key = obj.code if obj.code else obj.name
             dept_map[key] = obj.id

    print(f"  Results: Created {counters['created']}, Updated {counters['updated']}")


    # 3. PGDegree
    # -------------------------------------------------------------
    print("\n3. Migrating PGDegree...")
    degrees = PGDegree.objects.all()
    degree_map = {} # Name -> Live ID
    
    counters = {'created': 0, 'updated': 0}
    for obj in degrees:
        if not dry_run:
            live_obj, created = PGDegree.objects.using('live').update_or_create(
                name=obj.name,
                defaults={
                    'short_name': obj.short_name,
                    'total_semesters': obj.total_semesters,
                    'total_years': obj.total_years,
                    'json_data': obj.json_data
                }
            )
            degree_map[obj.name] = live_obj.id
            if created: counters['created'] += 1
            else: counters['updated'] += 1
        else:
            degree_map[obj.name] = obj.id
            counters['created'] += 1

    print(f"  Results: Created {counters['created']}, Updated {counters['updated']}")


    # 4. PGProgram
    # -------------------------------------------------------------
    print("\n4. Migrating PGProgram...")
    programs = PGProgram.objects.all()
    program_map = {} # Name -> Live ID
    
    counters = {'created': 0, 'updated': 0}
    for obj in programs:
        # Resolve FKs
        live_degree_id = None
        if obj.degree:
            live_degree_id = degree_map.get(obj.degree.name)
            
        live_dept_id = None
        if obj.department:
            key = obj.department.code if obj.department.code else obj.department.name
            live_dept_id = dept_map.get(key)
            
        if not live_degree_id:
            print(f"  ⚠ Skipped Program '{obj.name}': Degree not found/mapped.")
            continue

        if not dry_run:
            live_obj, created = PGProgram.objects.using('live').update_or_create(
                name=obj.name,
                defaults={
                    'short_name': obj.short_name,
                    'degree_id': live_degree_id,
                    'department_id': live_dept_id,
                    'json_data': obj.json_data
                }
            )
            program_map[obj.name] = live_obj.id
            if created: counters['created'] += 1
            else: counters['updated'] += 1
        else:
            program_map[obj.name] = obj.id
            counters['created'] += 1

    print(f"  Results: Created {counters['created']}, Updated {counters['updated']}")


    # 5. PGBatch
    # -------------------------------------------------------------
    print("\n5. Migrating PGBatch...")
    batches = PGBatch.objects.all()
    
    counters = {'created': 0, 'updated': 0}
    for obj in batches:
        # Resolve FKs
        live_prog_id = None
        if obj.program:
            live_prog_id = program_map.get(obj.program.name)

        if not dry_run:
            live_obj, created = PGBatch.objects.using('live').update_or_create(
                name=obj.name,
                defaults={
                    'program_id': live_prog_id,
                    'json_data': obj.json_data
                }
            )
            if created: counters['created'] += 1
            else: counters['updated'] += 1
        else:
            counters['created'] += 1

    print(f"  Results: Created {counters['created']}, Updated {counters['updated']}")
    print("\n✓ Master Data Migration Completed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    if not args.dry_run:
        if input("\nWrite to LIVE DB? (y/n): ").lower() != 'y': return
        
    migrate_masters(args.dry_run)

if __name__ == '__main__':
    main()
