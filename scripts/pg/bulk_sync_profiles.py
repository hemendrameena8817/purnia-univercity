
import os
import sys
import django
from pathlib import Path

# Setup Project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from accounts.models import UserAccount
from pg.models import PGStudentProfile

def bulk_sync_profiles():
    print("--- Starting Bulk Profile Sync ---")
    
    # 1. Iterate Existing Profiles
    profiles = PGStudentProfile.objects.all()
    count = profiles.count()
    print(f"Found {count} student profiles to sync.")
    
    updated_count = 0
    errors = 0
    
    with transaction.atomic():
        for i, profile in enumerate(profiles):
            try:
                user = profile.user
                
                # Update fields from user account
                profile.first_name = user.first_name
                profile.last_name = user.last_name
                # profile.registration_no = user.username # Make sure this is desired. Likely yes.
                
                # Update UserAccount current_profile
                if user.current_profile != 'pg':
                    user.current_profile = 'pg'
                    user.save()
                    # print(f"Updated current_profile for {user.username}")
                
                profile.save()
                updated_count += 1
                
                if (i + 1) % 100 == 0:
                   print(f"Processed {i + 1}/{count} profiles...")
                
            except Exception as e:
                print(f"Error syncing profile for {profile.registration_no}: {e}")
                errors += 1
                
    print("\n--- Summary ---")
    print(f"Total Profiles: {count}")
    print(f"Profiles Synced: {updated_count}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    bulk_sync_profiles()
