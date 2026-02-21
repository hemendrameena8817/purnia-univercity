"""
Runner: run_check_and_create_exam_result.py

Runs check_and_create_exam_result service.

Usage:
    # Batch - Dry run
    python pg/services/run_check_and_create_exam_result.py --batch 2024-26 --semester 3RD --session 2024-25 --dry-run

    # Batch - Production
    python pg/services/run_check_and_create_exam_result.py --batch 2024-26 --semester 3RD --session 2024-25

    # Single student - Dry run
    python pg/services/run_check_and_create_exam_result.py --semester 3RD --session 2024-25 --registration-no PU2024001 --dry-run

    # Single student - Production
    python pg/services/run_check_and_create_exam_result.py --semester 3RD --session 2024-25 --registration-no PU2024001

    # All batches in session - Dry run
    python pg/services/run_check_and_create_exam_result.py --semester 3RD --session 2024-25 --include-all-batches --dry-run
"""

import os
import sys
import django
import argparse
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.services.check_and_create_exam_result import check_and_create_exam_results


def main():
    parser = argparse.ArgumentParser(
        description='Check CIA pass and create PGExamResult if not already present (skip if exists)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--semester', type=str, required=True, help='Semester (e.g. 1ST, 2ND, 3RD, 4TH)')
    parser.add_argument('--session', type=str, required=True, help='Session (e.g. 2024-25)')
    parser.add_argument('--batch', type=str, default=None, help='Batch code (e.g. 2024-26)')
    parser.add_argument('--registration-no', type=str, default=None, help='Single student registration number')
    parser.add_argument('--include-all-batches', action='store_true', help='Process all batches in session')
    parser.add_argument('--dry-run', action='store_true', help='Dry run — no DB changes')

    args = parser.parse_args()

    if not args.dry_run:
        print(f"\n⚠️  PRODUCTION MODE")
        if args.registration_no:
            print(f"  Student : {args.registration_no}")
        elif args.batch and not args.include_all_batches:
            print(f"  Batch   : {args.batch}")
        else:
            print(f"  Scope   : ALL batches in session {args.session}")
        print(f"  Semester: {args.semester}  |  Session: {args.session}")
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return

    check_and_create_exam_results(
        batch=args.batch,
        semester=args.semester,
        session=args.session,
        registration_no=args.registration_no,
        include_all_batches=args.include_all_batches,
        dry_run=args.dry_run,
    )

    print("\n✅ Done!")
    if args.dry_run:
        print("💡 This was a DRY RUN. Run without --dry-run to save.")


if __name__ == '__main__':
    main()
