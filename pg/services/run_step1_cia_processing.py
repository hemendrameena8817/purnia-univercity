"""
Step 1: PG CIA Result Processing Script

Run this script after CIA marks entry is complete.

Usage Examples:
    # Regular students (single batch) - Dry run
    python pg/services/run_step1_cia_processing.py --batch 2024-26 --semester 1ST --session 2024-25 --dry-run
    
    # Regular students - Production run
    python pg/services/run_step1_cia_processing.py --batch 2024-26 --semester 1ST --session 2024-25
    
    # SINGLE STUDENT - Dry run
    python pg/services/run_step1_cia_processing.py --semester 1ST --session 2024-25 --registration-no PU2024001 --dry-run

    # SINGLE STUDENT - Production run
    python pg/services/run_step1_cia_processing.py --semester 2nd --session 2024-25 --registration-no 1907B060207 --dry-run

    # Back paper students (all batches in session) - Dry run
    python pg/services/run_step1_cia_processing.py --batch 2024-26 --semester 1ST --session 2024-25 --include-all-batches --dry-run
    
    # Back paper students - Production run
    python pg/services/run_step1_cia_processing.py --batch 2023-25 --semester 1st --session 2023-24 --include-all-batches
    python pg/services/run_step1_cia_processing.py --batch 2023-25 --semester 2nd --session 2023-24 --include-all-batches
    python pg/services/run_step1_cia_processing.py --batch 2023-25 --semester 3rd --session 2024-25 --include-all-batches
    python pg/services/run_step1_cia_processing.py --batch 2023-25 --semester 4th --session 2024-25 --include-all-batches
    
    # Session-wise processing (no batch specified)
    python pg/services/run_step1_cia_processing.py --semester 1ST --session 2024-25 --dry-run
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

from pg.services.step1_cia_processing import run_cia_processing


def main():
    """Main entry point"""
    
    ################################################################################
    # 1. ARGUMENT PARSING
    ################################################################################
    
    parser = argparse.ArgumentParser(
        description='Step 1: Process PG CIA results and create PGExamResult entries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test run (dry-run mode)
  python pg/services/run_step1_cia_processing.py --batch 2023-25 --semester 1ST --dry-run
  
  # Production run
  python pg/services/run_step1_cia_processing.py --batch 2023-25 --semester 1ST --session 2024-25
        """
    )
    
    parser.add_argument(
        '--batch',
        type=str,
        required=False,
        help='Batch code (e.g., 2023-25, 2024-26) - Optional for session-wise processing'
    )
    
    parser.add_argument(
        '--semester',
        type=str,
        required=True,
        help='Semester code (e.g., 1ST, 2ND, 3RD, 4TH)'
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
        help='Include students from all batches who have assessments in this session (for back paper processing)'
    )

    parser.add_argument(
        '--registration-no',
        type=str,
        default=None,
        help='Process a single student by registration number (e.g., PU2024001)'
    )
    
    args = parser.parse_args()
    
    ################################################################################
    # 2. CONFIRMATION
    ################################################################################
    
    if not args.dry_run:
        print(f"\n⚠️  PRODUCTION MODE")
        print(f"This will create/update PGExamResult entries for:")
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
    
    stats = run_cia_processing(
        batch=args.batch,
        semester=args.semester,
        session=args.session,
        dry_run=args.dry_run,
        include_all_batches=args.include_all_batches,
        registration_no=args.registration_no
    )
    
    print("\n✅ Step 1 Complete!")
    
    if args.dry_run:
        print("\n💡 This was a DRY RUN. No database changes were made.")
        print("   Run without --dry-run flag to save results.")


if __name__ == '__main__':
    main()
