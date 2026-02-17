import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import UGBatch, UGProgram

def sync_batches():
    print("Syncing UG Batches...")
    source = UGBatch.objects.using('default').all()
    
    count_created = 0
    count_updated = 0
    
    for src in source:
        try:
            # Check Target Program
            target_program = None
            if src.program:
                try:
                    target_program = UGProgram.objects.using('live').get(uid=src.program.uid)
                except UGProgram.DoesNotExist:
                    print(f"  Skipping {src.name}: Target Program {src.program.name} (UID {src.program.uid}) not found.")
                    continue
            
            defaults = {
                'name': src.name,
                'program': target_program,
                'json_data': src.json_data,
            }
            
            target, created = UGBatch.objects.using('live').update_or_create(
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
    sync_batches()
