#!/usr/bin/env python
"""
Standalone script to run data_fix.py

Usage:
    # Dry run (preview only, no changes)
    poetry run python scripts/ug/run_data_fix.py

    # Dry run with limit
    poetry run python scripts/ug/run_data_fix.py --limit 10

    # Actually update the database
    poetry run python scripts/ug/run_data_fix.py --no-dry-run

    # Update with limit
    poetry run python scripts/ug/run_data_fix.py --no-dry-run --limit 100
"""

import os
import sys
import django
import argparse

# Setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

# Now import the function
from scripts.ug.data_fix import fix_assessment_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fix StudentCourseAssessment data')
    parser.add_argument(
        '--no-dry-run',
        action='store_true',
        help='Actually update the database (default is dry-run mode)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of records to process (for testing)'
    )
    parser.add_argument(
        '--semester',
        type=str,
        default=None,
        help='Filter by semester (e.g., 1ST, 2ND, 3RD)'
    )
    parser.add_argument(
        '--session',
        type=str,
        default=None,
        help='Filter by session (e.g., 2025-26)'
    )
    
    args = parser.parse_args()
    
    dry_run = not args.no_dry_run
    
    print("="*80)
    print("StudentCourseAssessment Data Fix Script")
    print("="*80)
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE UPDATE'}")
    if args.semester:
        print(f"Semester: {args.semester}")
    if args.session:
        print(f"Session: {args.session}")
    if args.limit:
        print(f"Limit: {args.limit} records")
    print("="*80)
    print()
    
    if not dry_run:
        confirm = input("⚠️  This will UPDATE the database. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    fix_assessment_data(dry_run=dry_run, limit=args.limit, semester=args.semester, session=args.session)
