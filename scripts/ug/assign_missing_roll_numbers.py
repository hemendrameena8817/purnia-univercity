#!/usr/bin/env python
import os
import sys
from pathlib import Path

import django
from django.db import transaction

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug.models import UGStudentProfile



def get_existing_numeric_roll_numbers():
    return {
        int(str(roll_no).strip())
        for roll_no in UGStudentProfile.objects.select_for_update()
        .exclude(roll_no__isnull=True)
        .exclude(roll_no='')
        .values_list('roll_no', flat=True)
        if str(roll_no).strip().isdigit()
    }



def get_next_available_roll_number(existing_roll_numbers):
    next_roll_no = max(existing_roll_numbers, default=0) + 1
    while next_roll_no in existing_roll_numbers:
        next_roll_no += 1
    return str(next_roll_no)



def print_short_roll_no_usernames():
    rows = []
    queryset = UGStudentProfile.objects.select_related('user').exclude(roll_no__isnull=True).exclude(roll_no='')
    for profile in queryset.iterator(chunk_size=500):
        roll_no = str(profile.roll_no).strip()
        if len(roll_no) < 5:
            rows.append(
                f"username={getattr(profile.user, 'username', '') or '-'} | registration_no={profile.registration_no or '-'} | roll_no={roll_no or '-'}"
            )

    if not rows:
        return

    print('\n' + '=' * 100)
    print('USERNAMES WITH EXISTING ROLL NO LENGTH LESS THAN 5')
    print('=' * 100)
    for row in rows:
        print(row)



def assign_missing_roll_numbers(dry_run=False):
    print('\n' + '=' * 100)
    print('ASSIGN MISSING UG STUDENT ROLL NUMBERS')
    print('=' * 100)
    if dry_run:
        print('MODE: DRY RUN')
    else:
        print('MODE: LIVE UPDATE')

    existing_roll_numbers_snapshot = {
        int(str(roll_no).strip())
        for roll_no in UGStudentProfile.objects.exclude(roll_no__isnull=True)
        .exclude(roll_no='')
        .values_list('roll_no', flat=True)
        if str(roll_no).strip().isdigit()
    }
    largest_roll_no = max(existing_roll_numbers_snapshot, default=0)
    print(f'Largest existing numeric roll_no      {largest_roll_no}')

    print_short_roll_no_usernames()

    with transaction.atomic():
        existing_roll_numbers = get_existing_numeric_roll_numbers()
        missing_profiles = list(
            UGStudentProfile.objects.select_for_update().select_related('user').filter(roll_no__isnull=True).order_by('id')
        )

        print(f"Profiles with roll_no=NULL            {len(missing_profiles):,}")
        print(f"Existing numeric roll_no count        {len(existing_roll_numbers):,}")

        if not missing_profiles:
            print('\nNo profiles found with roll_no=NULL')
            return

        assigned_rows = []
        for profile in missing_profiles:
            next_roll_no = get_next_available_roll_number(existing_roll_numbers)
            existing_roll_numbers.add(int(next_roll_no))
            assigned_rows.append((profile, next_roll_no))

        print(f"Profiles to assign                    {len(assigned_rows):,}")
        print('\n' + '=' * 100)
        print('ASSIGNMENTS')
        print('=' * 100)
        for profile, next_roll_no in assigned_rows:
            print(
                f"username={getattr(profile.user, 'username', '') or '-'} | registration_no={profile.registration_no or '-'} | assigned_roll_no={next_roll_no}"
            )

        if dry_run:
            print('\nDRY RUN: no changes saved')
            return

        for profile, next_roll_no in assigned_rows:
            profile.roll_no = next_roll_no

        UGStudentProfile.objects.bulk_update(
            [profile for profile, _ in assigned_rows],
            ['roll_no'],
            batch_size=500,
        )

        print(f"\nUpdated {len(assigned_rows):,} profiles")



def main():
    import argparse

    parser = argparse.ArgumentParser(description='Assign next sequential roll_no only where UGStudentProfile.roll_no is NULL.')
    parser.add_argument('--dry-run', action='store_true', help='Preview assignments without saving')
    args = parser.parse_args()

    assign_missing_roll_numbers(dry_run=args.dry_run)



if __name__ == '__main__':
    main()
