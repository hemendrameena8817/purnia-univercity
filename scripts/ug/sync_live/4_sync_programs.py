import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import UGProgram, UGDegree, UGDepartment

def sync_programs():
    print("Syncing UG Programs...")
    source = UGProgram.objects.using('default').all()
    
    count_created = 0
    count_updated = 0
    
    for src in source:
        try:
            # Check Degree
            if not src.degree:
                print(f"  Skipping {src.name}: No degree linked.")
                continue
            
            # Check Target Degree (by UID)
            try:
                target_degree = UGDegree.objects.using('live').get(uid=src.degree.uid)
            except UGDegree.DoesNotExist:
                print(f"  Skipping {src.name}: Target Degree {src.degree.name} (UID {src.degree.uid}) not found.")
                continue
                
            # Check Department
            target_dept = None
            if src.department:
                try:
                    target_dept = UGDepartment.objects.using('live').get(uid=src.department.uid)
                except UGDepartment.DoesNotExist:
                     print(f"  Skipping {src.name}: Target Dept {src.department.name} (UID {src.department.uid}) not found.")
                     continue
            
            defaults = {
                'name': src.name,
                'short_name': src.short_name,
                'degree': target_degree,
                'department': target_dept,
                'json_data': src.json_data,
            }
            
            target, created = UGProgram.objects.using('live').update_or_create(
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
    sync_programs()
