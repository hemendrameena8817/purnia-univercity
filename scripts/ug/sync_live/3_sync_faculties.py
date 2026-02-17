import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import UGFaculty, UGDepartment
from university.models import University

def sync_faculties():
    print("Syncing UG Faculties (is_publish=True)...")
    source = UGFaculty.objects.using('default').filter(is_publish=True)

    count_created = 0
    count_updated = 0
    
    for src in source:
        try:
            # Validate Source University
            if not src.university:
                print(f"  Skipping {src.name}: No university linked.")
                continue
                
            src_univ_uid = src.university.pk
            
            # Check Target University
            try:
                target_univ = University.objects.using('live').get(pk=src_univ_uid)
            except University.DoesNotExist:
                # Fallback: Try finding by Name
                try:
                    target_univ = University.objects.using('live').get(name=src.university.name)
                    print(f"  Note: University '{src.university.name}' found by Name (UID mismatch). Using Live UID: {target_univ.uid}")
                except University.DoesNotExist:
                    print(f"  Skipping {src.name}: Target University {src_univ_uid} not found by UID or Name.")
                    continue

            defaults = {
                'name': src.name,
                'short_name': src.short_name,
                'description': src.description,
                'university': target_univ, # Assign target instance
                'is_publish': src.is_publish,
                'json_data': src.json_data,
            }
            
            target, created = UGFaculty.objects.using('live').update_or_create(
                uid=src.uid,
                defaults=defaults
            )
            
            # Sync M2M Departments
            src_depts = src.departments.all()
            target_depts = []
            for d in src_depts:
                # If dept is published, it should be in live. If not, maybe skip.
                try:
                    td = UGDepartment.objects.using('live').get(uid=d.uid)
                    target_depts.append(td)
                except UGDepartment.DoesNotExist:
                    # Only warn if source dept was published (should have been synced)
                    if d.is_publish:
                        print(f"  Warning: Published Department {d.name} missing in Live for Faculty {src.name}")
            
            if target_depts:
                target.departments.set(target_depts)
            
            if created:
                count_created += 1
                print(f"  Created: {target.name}")
            else:
                count_updated += 1
                
        except Exception as e:
            print(f"  ❌ Error syncing {src.name}: {e}")
            
    print(f"Done. Created: {count_created}, Updated: {count_updated}")

if __name__ == "__main__":
    sync_faculties()
