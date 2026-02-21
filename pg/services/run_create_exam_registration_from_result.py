"""
Runner: run_create_exam_registration_from_result.py

Creates PGExamRegistration entries from PGExamResult.
Skips students who already have a registration for the given semester/session/exam_type.

Usage Examples:

    # All batches in session - Dry run
    python pg/services/run_create_exam_registration_from_result.py --semester 3RD --session 2024-25 --dry-run

    # All batches in session - Production
    python pg/services/run_create_exam_registration_from_result.py --semester 3RD --session 2024-25

    # Specific batch - Dry run
    python pg/services/run_create_exam_registration_from_result.py --semester 3RD --session 2024-25 --batch 2024-26 --dry-run

    # Specific batch - Production
    python pg/services/run_create_exam_registration_from_result.py --semester 3RD --session 2024-25 --batch 2024-26

    # Single student - Dry run
    python pg/services/run_create_exam_registration_from_result.py --semester 3RD --session 2024-25 --registration-no PU2024001 --dry-run

    # Multiple students - Dry run
    python pg/services/run_create_exam_registration_from_result.py --semester 3RD --session 2024-25 --registration-nos PU2024001,PU2024002 --dry-run

    # Back exam type
    python pg/services/run_create_exam_registration_from_result.py --semester 3RD --session 2024-25 --exam-type BACK --dry-run
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

from pg.services.create_exam_registration_from_result import create_exam_registration_from_result


def main():
    parser = argparse.ArgumentParser(
        description='Create PGExamRegistration entries from PGExamResult (skips if already exists)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--semester', type=str, required=True,
                        help='Semester (e.g. 1ST, 2ND, 3RD, 4TH)')
    parser.add_argument('--session', type=str, required=True,
                        help='Session (e.g. 2024-25)')
    parser.add_argument('--batch', type=str, default=None,
                        help='Batch code (e.g. 2024-26). Ignored if --include-all-batches is set.')
    parser.add_argument('--registration-no', type=str, default=None,
                        help='Single student registration number (e.g. PU2024001)')
    parser.add_argument('--registration-nos', type=str, default=None,
                        help='Comma-separated registration numbers (e.g. PU2024001,PU2024002)')
    parser.add_argument('--include-all-batches', action='store_true',
                        help='Process all batches in the session (ignores --batch)')
    parser.add_argument('--exam-type', type=str, default='REGULAR',
                        choices=['REGULAR', 'BACK', 'IMPROVEMENT'],
                        help='Exam type for the registration (default: REGULAR)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dry run — shows what would be created without saving')

    args = parser.parse_args()

    # Parse comma-separated registration numbers
    reg_nos_list = None
    if args.registration_nos:
        reg_nos_list = [r.strip() for r in args.registration_nos.split(',') if r.strip()]

    if not args.dry_run:
        print(f"\n⚠️  PRODUCTION MODE")
        print(f"This will create PGExamRegistration entries for:")
        if args.registration_no:
            print(f"  Student  : {args.registration_no}")
        elif reg_nos_list:
            print(f"  Students : {', '.join(reg_nos_list)}  ({len(reg_nos_list)} students)")
        elif args.batch and not args.include_all_batches:
            print(f"  Batch    : {args.batch}")
        else:
            print(f"  Scope    : ALL batches in session {args.session}")
        print(f"  Semester : {args.semester}")
        print(f"  Session  : {args.session}")
        print(f"  Exam Type: {args.exam_type}")
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return

    create_exam_registration_from_result(
        semester=args.semester,
        session=args.session,
        batch=args.batch,
        registration_no=args.registration_no,
        registration_nos=reg_nos_list,
        include_all_batches=args.include_all_batches,
        exam_type=args.exam_type,
        dry_run=args.dry_run,
    )

    print("\n✅ Done!")
    if args.dry_run:
        print("💡 This was a DRY RUN. Run without --dry-run to apply changes.")


if __name__ == '__main__':
    main()
