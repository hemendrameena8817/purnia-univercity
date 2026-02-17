import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import UGDegree

def sync_degrees():
    print("Syncing UG Degrees...")
    source = UGDegree.objects.using('default').all()
    
    count_created = 0
    count_updated = 0
    
    for src in source:
        try:
            defaults = {
                'name': src.name,
                'short_name': src.short_name,
                'total_semesters': src.total_semesters,
                'total_years': src.total_years,
                'json_data': src.json_data,
            }
            
            target, created = UGDegree.objects.using('live').update_or_create(
                uid=src.uid,
                defaults=defaults
            )
            
            if created:
                count_created += 1
                print(f"  Created: {target.name}")
            else:
                count_updated += 1
                
        except Exception as e:
            print(f"  ❌ Error syncing {src.name}: {e}")
            
    print(f"Done. Created: {count_created}, Updated: {count_updated}")

if __name__ == "__main__":
    sync_degrees()
