#!/usr/bin/env python
"""
Script to Update UG Student Roll Numbers from Staging Data

This script:
1. Reads RegisteredApplicantMaster from staging app
2. Matches reg_no with UGStudentProfile.user.username
3. Updates roll_no with college_roll_no
4. Uses bulk updates for performance

Usage:
    python scripts/ug/update_roll_numbers.py
"""

import os
import sys
import django
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug.models import UGStudentProfile
from staging.models import RegisteredApplicantMaster


def update_roll_numbers_bulk(batch_size=5000, dry_run=False):
    """
    Update UG student roll numbers from staging data using bulk operations
    """
    print("=" * 80)
    print("UPDATE ROLL NUMBERS FROM STAGING DATA")
    print("=" * 80)
    print(f"Batch size: {batch_size}")
    if dry_run:
        print("Mode: DRY RUN (no saving)")
    print("-" * 80)
    
    # Statistics
    stats = {
        'staging_records': 0,
        'profiles_found': 0,
        'profiles_updated': 0,
        'no_match': 0,
        'no_roll_no': 0,
        'already_set': 0,
    }
    
    # Step 1: Get all staging records with college_roll_no
    print("\n→ Loading staging records...")
    staging_records = RegisteredApplicantMaster.objects.filter(
        college_roll_no__isnull=False
    ).exclude(
        college_roll_no=''
    ).values('college_reg_no', 'college_roll_no')
    
    stats['staging_records'] = len(staging_records)
    print(f"  ✓ Loaded {stats['staging_records']:,} staging records with roll numbers")
    
    # Step 2: Create mapping of college_reg_no -> college_roll_no
    print("\n→ Creating college_reg_no → college_roll_no mapping...")
    roll_no_map = {}
    for record in staging_records:
        # Explicitly use college_reg_no from the record
        c_reg_no = record['college_reg_no'].strip() if record['college_reg_no'] else None
        c_roll_no = record['college_roll_no'].strip() if record['college_roll_no'] else None
        
        # Only add if both exist
        if c_reg_no and c_roll_no:
            roll_no_map[c_reg_no] = c_roll_no
    
    print(f"  ✓ Created mapping for {len(roll_no_map):,} unique college_reg_nos")
    
    # DEBUG: Check user's specific case
    debug_key = '2330B060036'
    if debug_key in roll_no_map:
        print(f"\n[DEBUG] Found {debug_key} in map! Value: '{roll_no_map[debug_key]}'")
    else:
        print(f"\n[DEBUG] {debug_key} NOT found in map (college_reg_no). Checking if it exists in DB as reg_no...")
        try:
            r = RegisteredApplicantMaster.objects.filter(reg_no=debug_key).first()
            if r:
                print(f"  Found in DB via reg_no! college_reg_no='{r.college_reg_no}', college_roll_no='{r.college_roll_no}'")
            else:
                print("  Not found in DB via reg_no either.")
        except Exception as e:
            print(f"  Error checking DB: {e}")
    
    # Step 3: Get all UG student profiles with users
    print("\n→ Loading UG student profiles...")
    total_profiles = UGStudentProfile.objects.count()
    print(f"  Total profiles: {total_profiles:,}")
    
    # Step 4: Process in batches
    print(f"\n→ Processing in batches of {batch_size:,}...\n")
    
    offset = 0
    while offset < total_profiles:
        # Get batch of profiles with related user data
        profiles = UGStudentProfile.objects.select_related('user')[offset:offset + batch_size]
        
        profiles_to_update = []
        
        for profile in profiles:
            stats['profiles_found'] += 1
            
            # Get username from ugstudentprofile.user
            if not profile.user or not profile.user.username:
                stats['no_match'] += 1
                continue
            
            # This is the value we match against college_reg_no
            profile_username = profile.user.username.strip()
            
            # MATCH: Check if profile_username exists in our college_reg_no map
            if profile_username not in roll_no_map:
                stats['no_match'] += 1
                continue
            
            # Retrieve the college_roll_no from the map
            new_roll_no = roll_no_map[profile_username]
            
            # Check if update is needed
            if profile.roll_no == new_roll_no:
                stats['already_set'] += 1
                continue
            
            # Update profile roll_no
            profile.roll_no = new_roll_no
            profiles_to_update.append(profile)
            stats['profiles_updated'] += 1
        
        # Bulk update this batch
        if profiles_to_update:
            if not dry_run:
                UGStudentProfile.objects.bulk_update(
                    profiles_to_update, 
                    ['roll_no'], 
                    batch_size=500
                )
                print(f"  ✓ Updated {len(profiles_to_update):,} profiles (batch {offset:,}-{offset+batch_size:,})")
            else:
                print(f"  [DRY RUN] Would update {len(profiles_to_update):,} profiles (batch {offset:,}-{offset+batch_size:,})")
        else:
            print(f"  - No updates needed for batch {offset:,}-{offset+batch_size:,}")
        
        offset += batch_size
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Staging records found:     {stats['staging_records']:,}")
    print(f"Profiles processed:        {stats['profiles_found']:,}")
    print(f"Profiles updated:          {stats['profiles_updated']:,}")
    print(f"Already set correctly:     {stats['already_set']:,}")
    print(f"No matching reg_no:        {stats['no_match']:,}")
    print("-" * 80)
    
    if dry_run:
        print("\n⚠ DRY RUN - No changes were saved")
    else:
        print("\n✓ Roll number update completed successfully!")


def validate_update():
    """
    Validate that the update worked correctly
    """
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    # Count profiles with roll_no set
    total_profiles = UGStudentProfile.objects.count()
    with_roll_no = UGStudentProfile.objects.exclude(roll_no__isnull=True).exclude(roll_no='').count()
    without_roll_no = total_profiles - with_roll_no
    
    print(f"Total UG profiles:          {total_profiles:,}")
    print(f"With roll_no set:           {with_roll_no:,} ({with_roll_no/total_profiles*100:.1f}%)")
    print(f"Without roll_no:            {without_roll_no:,} ({without_roll_no/total_profiles*100:.1f}%)")
    
    # Sample check
    print("\nSample Records:")
    print("-" * 80)
    samples = UGStudentProfile.objects.select_related('user').exclude(
        roll_no__isnull=True
    ).exclude(roll_no='')[:5]
    
    for profile in samples:
        print(f"  Username: {profile.user.username:<20} → Roll No: {profile.roll_no}")
    
    print("=" * 80)


def main():
    """
    Main entry point
    """
    import argparse
    parser = argparse.ArgumentParser(description='Update Roll Numbers from Staging')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not save')
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("Starting Roll Number Update Script")
    if args.dry_run:
        print("MODE: DRY RUN (No changes will be saved)")
    else:
        print("MODE: LIVE UPDATE")
    print("=" * 80 + "\n")
    
    # Configuration
    batch_size = 5000  # Process 5k profiles at a time
    
    # Run update
    update_roll_numbers_bulk(batch_size=batch_size, dry_run=args.dry_run)
    
    # Validate
    validate_update()


if __name__ == '__main__':
    main()
