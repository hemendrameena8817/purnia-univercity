#!/usr/bin/env python
"""
Migration Script: UserAccount (Local DB) → UserAccount (Live DB)

This script migrates UserAccount records from LOCAL database to LIVE database.
It handles all user types (student, faculty, admin, etc.) and resolves college 
foreign keys using college_code for data integrity across database instances.

Optimized for performance using bulk_create and bulk_update operations.

Usage:
    python DBMIGRATIONS/migrate_users_local_to_live.py [--dry-run] [--user-type TYPE] [--limit N] [--batch-size N]

Options:
    --dry-run       Preview changes without committing to live database
    --user-type     Filter by user type (student, faculty, admin, etc.)
    --limit N       Limit migration to N records (useful for testing)
    --batch-size N  Number of records to process in each batch (default: 5000)

Requirements:
    - 'live' database must be configured in settings
    - .env file must contain DB connection details for both local and live databases
"""

import os
import sys
import django
import argparse
import time
from datetime import datetime
from django.db import connections
from django.db.utils import OperationalError

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.conf import settings
from accounts.models import UserAccount
from colleges.models import College


def get_live_college_mapping():
    """
    Fetch college mapping from LIVE database for FK resolution.
    Returns: {college_code: college_id}
    """
    print("  → Fetching colleges from LIVE database...", end="", flush=True)
    colleges = College.objects.using('live').values('id', 'college_code')
    college_map = {c['college_code'].strip(): c['id'] for c in colleges if c['college_code']}
    print(f" Done ({len(college_map)} colleges loaded)")
    return college_map


def migrate_users(dry_run=False, user_type=None, limit=None, batch_size=5000):
    """
    Migrate UserAccount records from LOCAL to LIVE database using bulk operations.
    """
    start_time = time.time()
    print("=" * 80)
    print("MIGRATION: UserAccount (Local) → UserAccount (Live)")
    print("=" * 80)
    print(f"Mode:       {'DRY RUN (no changes)' if dry_run else 'LIVE MIGRATION'}")
    print(f"User Type:  {user_type if user_type else 'ALL'}")
    print(f"Limit:      {limit if limit else 'No limit (process all)'}")
    print(f"Batch Size: {batch_size}")
    
    # Check if 'live' database is configured
    if 'live' not in settings.DATABASES:
        print("\n❌ Error: 'live' database is not configured in settings.")
        return

    # Test connection to live database
    try:
        with connections['live'].cursor():
            pass
        print(f"✓ Connected to LIVE database: {settings.DATABASES['live']['HOST']}/{settings.DATABASES['live']['NAME']}")
    except OperationalError as e:
        print(f"\n❌ Error connecting to LIVE database: {e}")
        return

    print("-" * 80)
    print("Preparing data...")

    # 1. Fetch college mapping from LIVE DB
    college_map = get_live_college_mapping()

    # 2. Fetch existing usernames from LIVE DB to avoid duplicates
    print("  → Fetching existing users from LIVE database...", end="", flush=True)
    existing_usernames = set(
        UserAccount.objects.using('live').values_list('username', flat=True)
    )
    print(f" Done ({len(existing_usernames)} users loaded)")

    # 3. Query LOCAL database for users to migrate
    print("  → Fetching users from LOCAL database...", end="", flush=True)
    queryset = UserAccount.objects.using('default').all()
    
    if user_type:
        queryset = queryset.filter(user_type=user_type)
    
    if limit:
        queryset = queryset[:limit]
    
    # Select related to optimize queries
    queryset = queryset.select_related('college')
    
    total_records = queryset.count()
    print(f" Done ({total_records} users to process)")
    
    if total_records == 0:
        print("\n✓ No records to migrate. All done!")
        return

    # Statistics
    stats = {
        'processed': 0,
        'created': 0,
        'updated': 0,
        'skipped_duplicate': 0,
        'college_mapped': 0,
        'college_not_found': 0,
        'no_college': 0
    }

    # Batches
    users_to_create = []
    users_to_update = []
    batch_usernames = set()  # Track usernames in current batch

    print(f"\nProcessing in batches of {batch_size}...\n")

    count = 0
    for local_user in queryset.iterator():
        count += 1
        stats['processed'] += 1
        
        username = local_user.username.strip() if local_user.username else ""
        
        if not username:
            continue
        
        # Check if user already exists in LIVE DB or current batch
        if username in existing_usernames:
            stats['skipped_duplicate'] += 1
            continue
        
        if username in batch_usernames:
            stats['skipped_duplicate'] += 1
            continue
            
        # Add to batch tracking
        batch_usernames.add(username)
        
        # Resolve College FK
        live_college_id = None
        if local_user.college:
            college_code = local_user.college.college_code.strip() if local_user.college.college_code else ""
            if college_code and college_code in college_map:
                live_college_id = college_map[college_code]
                stats['college_mapped'] += 1
            else:
                stats['college_not_found'] += 1
        else:
            stats['no_college'] += 1
        
        # Create User Object (in memory)
        new_user = UserAccount(
            username=username,
            password=local_user.password,  # Copy hashed password as-is
            first_name=local_user.first_name or '',
            email=local_user.email or '',
            user_type=local_user.user_type or 'student',
            current_profile=local_user.current_profile or '',
            college_id=live_college_id,
            is_active=local_user.is_active,
            is_verified=local_user.is_verified,
            is_staff=local_user.is_staff,
            is_superuser=local_user.is_superuser,
            # date_joined=local_user.date_joined,
            # last_login=local_user.last_login
        )
        
        users_to_create.append(new_user)
        stats['created'] += 1
        
        # Flush batch when size reached
        if len(users_to_create) >= batch_size:
            _flush_batch(users_to_create, existing_usernames, dry_run)
            users_to_create = []
            batch_usernames = set()
            print(f"  Processed {count}/{total_records} records...")

    # Flush remaining users
    if users_to_create:
        _flush_batch(users_to_create, existing_usernames, dry_run)

    end_time = time.time()
    duration = end_time - start_time
    
    # Print summary
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Time Taken:              {duration:.2f} seconds")
    print(f"Total processed:         {stats['processed']}")
    print(f"Users created:           {stats['created']}")
    print(f"Skipped (duplicate):     {stats['skipped_duplicate']}")
    print(f"College mapped:          {stats['college_mapped']}")
    print(f"College not found:       {stats['college_not_found']}")
    print(f"No college:              {stats['no_college']}")
    print("-" * 80)
    
    if dry_run:
        print(f"\n⚠ DRY RUN MODE - No changes were saved")
        print(f"Users that WOULD be created: {stats['created']}")
    else:
        print(f"\n✓ Migration completed successfully!")
        print(f"Total users migrated: {stats['created']}")


def _flush_batch(users, existing_usernames_set, dry_run):
    """Helper to bulk create users in LIVE database."""
    if not users:
        return

    if dry_run:
        # Just simulate
        return

    try:
        # Bulk create users on LIVE db
        created_users = UserAccount.objects.using('live').bulk_create(
            users, 
            ignore_conflicts=True
        )
        
        # Update existing_usernames_set for subsequent batches
        for u in users:
            existing_usernames_set.add(u.username)
            
        print(f"    ✓ Created {len(users)} users in LIVE database")
            
    except Exception as e:
        print(f"  ❌ Batch Error: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Migration: UserAccount (local) → UserAccount (live)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without committing')
    parser.add_argument('--user-type', type=str, help='Filter by user type (student, faculty, admin, etc.)')
    parser.add_argument('--limit', type=int, help='Limit number of records to migrate')
    parser.add_argument('--batch-size', type=int, default=5000, help='Batch size for bulk operations')
    
    args = parser.parse_args()
    
    # Confirm before running in live mode
    if not args.dry_run:
        print("\n⚠ WARNING: You are about to run this migration in LIVE mode.")
        if 'live' in settings.DATABASES:
            print(f"Destination: {settings.DATABASES['live']['HOST']}/{settings.DATABASES['live']['NAME']}")
        else:
            print("Destination: 'live' database (not configured!)")
            
        print("\nThis will create new UserAccount records in the LIVE database.")
        response = input("\nDo you want to continue? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("Migration cancelled.")
            return
        print()
    
    migrate_users(
        dry_run=args.dry_run, 
        user_type=args.user_type, 
        limit=args.limit, 
        batch_size=args.batch_size
    )


if __name__ == '__main__':
    main()
