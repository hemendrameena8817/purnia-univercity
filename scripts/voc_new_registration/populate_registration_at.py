import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from voc_new_registration.models import NewRegistration
from django.db import transaction

def update_existing_registrations():
    """
    Sets registration_at as updated_at for all records where is_registration_completed is True.
    """
    completed_regs = NewRegistration.objects.filter(
        is_registration_completed=True,
        registration_at__isnull=True
    )
    
    count = completed_regs.count()
    print(f"Found {count} completed registrations to update...")
    
    updated_count = 0
    with transaction.atomic():
        for reg in completed_regs:
            reg.registration_at = reg.updated_at
            # We use save() to avoid auto_now updating updated_at again during this specific script if desired, 
            # though it doesn't matter much for a one-time fix.
            reg.save(update_fields=['registration_at'])
            updated_count += 1
            
    print(f"Successfully updated {updated_count} records.")

if __name__ == "__main__":
    update_existing_registrations()
