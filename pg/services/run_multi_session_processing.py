
import os
import sys
import django
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.services.step1_cia_processing import run_cia_processing
from pg.services.calculate_batch_results import calculate_results

def process_session(session, dry_run=False):
    print(f"\n\n{'#'*80}")
    print(f"🚀 STARTING PROCESSING FOR SESSION: {session}")
    print(f"{'#'*80}")
    
    semesters = ['1ST', '2ND', '3RD', '4TH']
    
    for sem in semesters:
        print(f"\n{'-'*60}")
        print(f"💠 SEMESTER: {sem} ({session})")
        print(f"{'-'*60}")
        
        # Step 1: CIA Processing
        print(f"🔹 [Step 1] CIA Processing...")
        try:
            run_cia_processing(
                batch=None, 
                semester=sem, 
                session=session, 
                dry_run=dry_run
            )
        except Exception as e:
            print(f"❌ [Step 1] FAILED: {e}")
            print(f"⚠️ Skipping Step 2 due to CIA failure.")
            continue

        # Step 2: Final Result
        print(f"🔹 [Step 2] Final Result Calculation...")
        try:
            calculate_results(
                batch_name=None,
                semester=sem, 
                session=session, 
                dry_run=dry_run
            )
        except Exception as e:
            print(f"❌ [Step 2] FAILED: {e}")

    print(f"\n✅ COMPLETED SESSION: {session}\n")

if __name__ == "__main__":
    sessions = ['2022-23', '2023-24', '2024-25']
    
    # Check for dry-run argument
    dry_run = '--dry-run' in sys.argv
    
    print(f"ℹ️  Mode: {'DRY RUN' if dry_run else 'PRODUCTION (DB Changes)'}")
    
    for session in sessions:
        process_session(session, dry_run=dry_run)
        
    print(f"\n{'='*80}")
    print("🙌 ALL REQUESTED SESSIONS PROCESSED")
    print(f"{'='*80}")
