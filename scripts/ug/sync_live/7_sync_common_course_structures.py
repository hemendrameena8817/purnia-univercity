import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import CommonCourseStructure

def sync_common_course_structures():
    print("Syncing Common Course Structures (All Semesters)...")
    
    source = CommonCourseStructure.objects.using('default').all()
    print(f"Found {source.count()} common courses in source.")
    
    count_created = 0
    count_updated = 0
    
    for src in source:
        try:
            defaults = {
                'semester': src.semester,
                'course_name': src.course_name,
                'course_type': src.course_type,
                'ltp': src.ltp,
                'credit': src.credit,
                'marks': src.marks,
                'code': src.code,
                'json_data': src.json_data,
            }
            
            target, created = CommonCourseStructure.objects.using('live').update_or_create(
                uid=src.uid,
                defaults=defaults
            )
            
            if created:
                count_created += 1
                print(f"  Created: {target.course_name} ({target.course_type})")
            else:
                count_updated += 1
                
        except Exception as e:
            print(f"  ❌ Error syncing {src.course_name}: {e}")
            
    print(f"Done. Created: {count_created}, Updated: {count_updated}")

if __name__ == "__main__":
    sync_common_course_structures()
