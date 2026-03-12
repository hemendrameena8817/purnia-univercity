"""
Step 1: CIA Result Processing Script

Run this script after CIA marks entry is complete.

Usage:
    # Dry run - by session (all batches)
    poetry run python ug/services/run_step1_cia_processing.py --semester 1ST --session 2022-23 --dry-run
    
    # Production run - filter by batch
    poetry run python ug/services/run_step1_cia_processing.py --batch 2024-28 --semester 1ST --session 2024-25
    
    # Back exams
    poetry run python ug/services/run_step1_cia_processing.py --semester 1ST --session 2024-25 --exam-type BACK
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
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.services.step1_cia_processing import run_cia_processing


def main():
    """Main entry point"""
    
    ################################################################################
    # 1. ARGUMENT PARSING
    ################################################################################
    
    parser = argparse.ArgumentParser(
        description='Step 1: Process CIA results and create UGExamResult entries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test run (dry-run mode)
  python ug/services/run_step1_cia_processing.py --batch 2024-28 --semester 1ST --dry-run
  
  # Production run
  python ug/services/run_step1_cia_processing.py --batch 2024-28 --semester 1ST --session 2024-25
        """
    )
    
    parser.add_argument(
        '--batch',
        type=str,
        required=False,
        default=None,
        help='Batch code (e.g., 2024-28). Optional - if omitted, all batches in session are processed.'
    )
    
    parser.add_argument(
        '--semester',
        type=str,
        required=True,
        help='Semester code (e.g., 1ST, 2ND, 3RD, etc.)'
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
        '--exam-type',
        type=str,
        default='REGULAR',
        choices=['REGULAR', 'BACK'],
        help='Exam type (default: REGULAR)'
    )
    
    args = parser.parse_args()
    
    ################################################################################
    # 2. CONFIRMATION
    ################################################################################
    
    if not args.dry_run:
        print(f"\n⚠️  PRODUCTION MODE")
        print(f"This will create/update UGExamResult entries for:")
        print(f"  Batch:     {args.batch or 'ALL'}")
        print(f"  Semester:  {args.semester}")
        print(f"  Session:   {args.session}")
        print(f"  Exam Type: {args.exam_type}")
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
        exam_type=args.exam_type,
        dry_run=args.dry_run
    )
    
    print("\n✅ Step 1 Complete!")
    
    if args.dry_run:
        print("\n💡 This was a DRY RUN. No database changes were made.")
        print("   Run without --dry-run flag to save results.")


if __name__ == '__main__':
    main()
