"""
Step 2: Final Result Processing Script (Post-ESE)

Run this script after ALL ESE marks have been entered.
It calculates final grades, SGPAs, semester results, and manages next-semester registration.

Usage:
    # Dry run (no database changes)
    poetry run python ug/services/run_step2_final_processing.py --batch 2024-28 --semester 1ST --dry-run
    
    # Production run
    poetry run python ug/services/run_step2_final_processing.py --batch 2024-28 --semester 1ST --session 2024-25
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

from ug.services.step2_final_processing import run_final_processing


def main():
    """Main entry point"""
    
    ################################################################################
    # 1. ARGUMENT PARSING
    ################################################################################
    
    parser = argparse.ArgumentParser(
        description='Step 2: Final Result Processing (Post-ESE)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test run (dry-run mode)
  python ug/services/run_step2_final_processing.py --batch 2024-28 --semester 1ST --dry-run
  
  # Production run
  python ug/services/run_step2_final_processing.py --batch 2024-28 --semester 1ST --session 2024-25
        """
    )
    
    parser.add_argument(
        '--batch',
        type=str,
        required=True,
        help='Batch code (e.g., 2024-28)'
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
        '--registration-no',
        type=str,
        help='Run for single student (e.g., 20240001)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in test mode without making database changes'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume processing from last processed student (skip completed)'
    )
    
    args = parser.parse_args()
    
    ################################################################################
    # 2. CONFIRMATION
    ################################################################################
    
    if not args.dry_run:
        print(f"\n⚠️  PRODUCTION MODE")
        print(f"This will CALCULATE FINAL RESULTS and UPDATE DATABASE for:")
        print(f"  Batch:    {args.batch}")
        print(f"  Semester: {args.semester}")
        print(f"  Session:  {args.session}")
        if args.registration_no:
            print(f"  Student:  {args.registration_no}")
        print("\nActions:")
        print("  1. Update course-level marks & grades")
        print("  2. Update SGPA & Semester Result")
        print("  3. Create Next-Semester Registrations (for Pass/Promoted)")
        
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return
    
    ################################################################################
    # 3. EXECUTION
    ################################################################################
    
    stats = run_final_processing(
        batch=args.batch,
        semester=args.semester,
        session=args.session,
        registration_no=args.registration_no,
        dry_run=args.dry_run,
        resume=args.resume
    )
    
    print("\n✅ Step 2 Complete!")
    
    if args.dry_run:
        print("\n💡 This was a DRY RUN. No database changes were made.")


if __name__ == '__main__':
    main()
