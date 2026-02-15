import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from university.models import University

def sync_university():
    print("Syncing University...")
    
    # Try to find "Purnea University" in source
    # We relax the filter to get the main university object. 
    # Usually there is only one, or we filter by name.
    source_univ = University.objects.using('default').filter(name__icontains="Purnea").first()
    
    if not source_univ:
        # If no explicit "Purnea" match, take the first one available
        source_univ = University.objects.using('default').first()
        
    if not source_univ:
        print("❌ Error: No University found in Source DB. Cannot sync.")
        return

    print(f"Found source university: {source_univ.name} (UID: {source_univ.uid})")
    
    defaults = {
        'name': source_univ.name,
        'short_name': source_univ.short_name,
        'address': source_univ.address,
        'vice_chancellor': source_univ.vice_chancellor,
        'contact_no': source_univ.contact_no,
        'email': source_univ.email,
        'website': source_univ.website,
        'established_date': source_univ.established_date,
        'json_data': source_univ.json_data,
    }
    
    try:
        # Check if university exists by name but different UID
        existing_by_name = University.objects.using('live').filter(name=source_univ.name).exclude(uid=source_univ.uid).first()
        
        if existing_by_name:
            print(f"  Warning: University '{source_univ.name}' exists in Live with DIFFERENT UID ({existing_by_name.uid}).")
            print("  Updating existing record explicitly.")
            
            for key, value in defaults.items():
                setattr(existing_by_name, key, value)
            existing_by_name.save()
            print(f"  Updated: {existing_by_name.name}")
        else:
            # Normal sync using UID
            target, created = University.objects.using('live').update_or_create(
                uid=source_univ.uid,
                defaults=defaults
            )
            
            if created:
                print(f"  Created: {target.name}")
            else:
                print(f"  Updated: {target.name}")
            
    except Exception as e:
        print(f"  ❌ Error syncing university: {e}")

if __name__ == "__main__":
    sync_university()
