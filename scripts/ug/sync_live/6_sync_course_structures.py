import os
import django
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import CourseStructure, UGDepartment, UGBatch

def sync_course_structures():
    target_sem = '3'
    print(f"Syncing Course Structures for Semester '{target_sem}'...")
    
    source = CourseStructure.objects.using('default').filter(semester=target_sem, department__is_publish=True)
    print(f"Found {source.count()} courses for Sem '{target_sem}'.")
    
    count_created = 0
    count_updated = 0
    
    for src in source:
        try:
            # Check Department
            target_dept = None
            if src.department:
                try:
                    target_dept = UGDepartment.objects.using('live').get(uid=src.department.uid)
                except UGDepartment.DoesNotExist:
                     print(f"  Skipping {src.course_name}: Dept {src.department.name} (UID {src.department.uid}) missing in Live (likely unpublished).")
                     continue
            else:
                print(f"  Skipping {src.course_name}: No department linked.")
                continue # Course must have dept usually
                 
            # Check Batch (Required?)
            # Check Batch (Required?)
            # target_batch = None
            # if src.batch:
            #     try:
            #         target_batch = UGBatch.objects.using('live').get(uid=src.batch.uid)
            #     except UGBatch.DoesNotExist:
            #         print(f"  Warning: Batch {src.batch.name} (UID {src.batch.uid}) missing in Live. Course {src.course_name} will have no batch.")
            #         # Don't skip, just set None
            #         target_batch = None
            
            # Create/Update
            defaults = {
                'course_name': src.course_name,
                'course_short_name': src.course_short_name,
                'department': target_dept,
                'course_type': src.course_type,
                'course_code': src.course_code,
                'paper_code': src.paper_code,
                'max_credit': src.max_credit,
                'max_marks': src.max_marks,
                'min_marks': src.min_marks,
                'description': src.description,
                'label': src.label,
                'semester': src.semester,
                'json_data': src.json_data,
            }
            
            target, created = CourseStructure.objects.using('live').update_or_create(
                uid=src.uid,
                defaults=defaults
            )
            
            if created:
                count_created += 1
                print(f"  Created: {target.course_name} ({target.paper_code})")
            else:
                count_updated += 1
                
        except Exception as e:
            print(f"  ❌ Error syncing {src.course_name}: {e}")
            
    print(f"Done. Created: {count_created}, Updated: {count_updated}")

if __name__ == "__main__":
    sync_course_structures()
