import os
import sys

# Setup Django path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')

import django
django.setup()

from ug.models import ExamRegistration


def run():
    print("Finding open Exam Registrations in LOCAL (session 2025-26, sem 1)...")
    
    # 1. Fetch exactly the students who are legitimately OPEN in the local DB.
    #    This inherently handles our PROMOTED/PARTLY_QUALIFIED/DISQUALIFIED logic
    #    since we only opened them locally first!
    local_open_regs = ExamRegistration.objects.using('default').filter(
        session='2025-26',
        sem=1,
        status='OPEN'
    )
    
    local_count = local_open_regs.count()
    print(f"Found {local_count} registrations clearly marked OPEN locally.")
    
    if local_count == 0:
        print("Nothing to sync to live DB!")
        return

    # Grab the exact registration numbers from the local open ones
    reg_nos = list(local_open_regs.values_list('student__registration_no', flat=True).distinct())

    # Get the precise start and end date you already set locally from a random entry
    sample_reg = local_open_regs.first()
    start_date = sample_reg.start_date
    end_date = sample_reg.end_date
    
    print(f"Syncing exactly these dates directly to live:")
    print(f"   START: {start_date}")
    print(f"   END:   {end_date}")

    # 2. Target the exact registrations on the live DB using the Reg Nos
    live_regs = ExamRegistration.objects.using('live').filter(
        student__registration_no__in=reg_nos,
        session='2025-26',
        sem=1
    )
    
    live_count_before = live_regs.count()
    print(f"\nDiscovered {live_count_before} matching exam registrations natively in live DB...")

    # 3. Force update the live DB to mirror the exact OPEN state
    updated_count = live_regs.update(
        status='OPEN',
        is_open=True,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"🎉 Successfully forced {updated_count} LIVE registrations to OPEN utilizing exact local config!")


if __name__ == "__main__":
    run()
