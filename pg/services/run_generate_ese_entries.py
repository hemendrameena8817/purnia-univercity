"""
Script to run ESE Entry Generation.

Usage Examples:
    # Full batch - Dry run
    python pg/services/run_generate_ese_entries.py --batch 2024-26 --semester 3RD --session 2024-25 --dry-run

    # Full batch - Production
    python pg/services/run_generate_ese_entries.py --batch 2024-26 --semester 3RD --session 2024-25

    # SINGLE student - Dry run
    python pg/services/run_generate_ese_entries.py --semester 3RD --session 2024-25 --registration-no PU2024001 --dry-run

    # SINGLE student - Production
    python pg/services/run_generate_ese_entries.py --semester 3RD --session 2024-25 --registration-no PU2024001

    # MULTIPLE students - Dry run (comma-separated)
    python pg/services/run_generate_ese_entries.py --semester 3RD --session 2024-25 --registration-nos PU2024001,PU2024002,PU2024003 --dry-run

    # MULTIPLE students - Production
    python pg/services/run_generate_ese_entries.py --semester 3RD --session 2024-25 --registration-nos PU2024001,PU2024002,PU2024003

    # All batches in session
    python pg/services/run_generate_ese_entries.py --semester 3RD --session 2024-25 --include-all-batches --dry-run
"""
import os
import sys
import django
import argparse
from pathlib import Path

# Setup Project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.services.generate_ese_entries import generate_ese_entries

def main():
    parser = argparse.ArgumentParser(description="Generate ESE Assessment Entries for CIA Passed Students")
    
    parser.add_argument('--batch', type=str, help='Batch Code (e.g. 2023-25)')
    parser.add_argument('--semester', type=str, required=True, help='Semester (e.g. 1ST, 3RD)')
    parser.add_argument('--session', type=str, required=True, help='Session (e.g. 2024-25)')
    parser.add_argument('--dry-run', action='store_true', help='Dry Run Mode')
    parser.add_argument('--include-all-batches', action='store_true', help='Include all batches in session')
    parser.add_argument('--registration-no', type=str, default=None,
                        help='Process a SINGLE student by registration number (e.g. PU2024001)')
    parser.add_argument('--registration-nos', type=str, default=None,
                        help='Process MULTIPLE students by comma-separated registration numbers (e.g. PU2024001,PU2024002)')
    
    args = parser.parse_args()

    # Parse comma-separated registration numbers
    reg_nos_list = None
    if args.registration_nos:
        reg_nos_list = [r.strip() for r in args.registration_nos.split(',') if r.strip()]

    if not args.dry_run:
        print(f"\n⚠️  PRODUCTION MODE")
        print(f"This will create ESE entries for:")
        if args.registration_no:
            print(f"  Student:  {args.registration_no} (Single Student)")
        elif reg_nos_list:
            print(f"  Students: {', '.join(reg_nos_list)} ({len(reg_nos_list)} students)")
        else:
            print(f"  Batch:    {args.batch if args.batch else 'ALL BATCHES (Session Wise)'}")
        print(f"  Semester: {args.semester}")
        print(f"  Session:  {args.session}")
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return

    generate_ese_entries(
        batch=args.batch,
        semester=args.semester,
        session=args.session,
        dry_run=args.dry_run,
        include_all_batches=args.include_all_batches,
        registration_no=args.registration_no,
        registration_nos=reg_nos_list
    )

if __name__ == "__main__":
    main()
