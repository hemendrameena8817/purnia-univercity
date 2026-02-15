import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import UGDepartment

def sync_departments():
    print("Syncing UG Departments (is_publish=True)...")
    
    # Source (default DB)
    source_depts = UGDepartment.objects.using('default').filter(is_publish=True)
    print(f"Found {source_depts.count()} published departments in source.")
    
    count_created = 0
    count_updated = 0
    
    for src in source_depts:
        try:
            # Try to match by UID first (Replica logic)
            # If not found, create new with source UID
            defaults = {
                'name': src.name,
                'code': src.code,
                'head_of_department': src.head_of_department,
                'is_publish': src.is_publish, # Should always be True based on filter
                'json_data': src.json_data,
            }
            
            target, created = UGDepartment.objects.using('live').update_or_create(
                uid=src.uid,
                defaults=defaults
            )
            
            if created:
                count_created += 1
                print(f"  Created: {target.name} ({target.code})")
            else:
                count_updated += 1
                # print(f"  Updated: {target.name}")
                
        except Exception as e:
            print(f"  ❌ Error syncing {src.name}: {e}")

    print(f"Done. Created: {count_created}, Updated: {count_updated}")

if __name__ == "__main__":
    sync_departments()
