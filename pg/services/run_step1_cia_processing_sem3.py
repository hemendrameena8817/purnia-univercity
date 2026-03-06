"""
Step 1: Dynamic PG CIA Result Processing (Ignore Eligibility)

This script allows processing any semester while ignoring previous 
semester result/eligibility checks.

Usage Examples:
    # Dry run for 1st Semester
    python pg/services/run_step1_cia_processing_sem3.py --semester 1ST --session 2025-26 --dry-run
    
    # Production run for 3rd Semester
    python pg/services/run_step1_cia_processing_sem3.py --semester 3RD --session 2024-25
    
    # SINGLE STUDENT - Dry run
    python pg/services/run_step1_cia_processing_sem3.py --semester 1ST --session 2025-26 --registration-no PU2024001 --dry-run
"""

import os
import sys
import django
from pathlib import Path    
import argparse

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.services.step1_cia_processing_sem3 import run_cia_processing_sem3


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='Step 1: Process PG CIA results (Simplified/Ignore Eligibility)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--batch',
        type=str,
        required=False,
        help='Batch code (e.g., 2023-25, 2024-26)'
    )
    
    parser.add_argument(
        '--semester',
        type=str,
        default='1ST',
        help='Semester code (e.g., 1ST, 2ND, 3RD, 4TH) - Default: 1ST'
    )

    parser.add_argument(
        '--session',
        type=str,
        default='2024-25',
        help='Academic session (default: 2024-25)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in test mode without making database changes'
    )
    
    parser.add_argument(
        '--include-all-batches',
        action='store_true',
        help='Include students from all batches'
    )

    parser.add_argument(
        '--registration-no',
        type=str,
        default=None,
        help='Process a single student by registration number'
    )
    
    parser.add_argument(
        '--ignore-eligibility',
        action='store_true',
        help='Bypass any eligibility checks (Now default in this specialized script)'
    )
    
    args = parser.parse_args()
    
    ################################################################################
    # 2. CONFIRMATION
    ################################################################################
    
    if not args.dry_run:
        print(f"\n⚠️  PRODUCTION MODE - DYNAMIC CIA PROCESSING (IGNORE ELIGIBILITY)")
        print(f"Policy: Directly processing {args.semester} (Ignoring previous semesters).")
            
        if args.registration_no:
            print(f"  Student:  {args.registration_no} (Single Student)")
        else:
            print(f"  Batch:    {args.batch if args.batch else 'ALL BATCHES (Session Wise)'}")
        print(f"  Semester: {args.semester}")
        print(f"  Session:  {args.session}")
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return
    
    ################################################################################
    # 3. EXECUTION
    ################################################################################
    
    stats = run_cia_processing_sem3(
        batch=args.batch,
        semester=args.semester,
        session=args.session,
        dry_run=args.dry_run,
        include_all_batches=args.include_all_batches,
        registration_no=args.registration_no,
        ignore_eligibility=args.ignore_eligibility
    )
    
    print(f"\n✅ Step 1 ({args.semester}) Complete!")
    
    if args.dry_run:
        print("\n💡 This was a DRY RUN. No database changes were made.")


if __name__ == '__main__':
    main()
