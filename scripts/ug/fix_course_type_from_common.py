import os
import sys
import django
import re
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from django.db import transaction
from ug.models import StudentCourseAssessment, CommonCourseStructure

def main():
    print("Building Common Course Structure lookup...")
    common_courses = CommonCourseStructure.objects.all()
    code_map = {}
    for c in common_courses:
        if c.code and c.semester:
            key = f"{c.semester}_{c.code}"
            code_map[key] = c.course_type # e.g. '1ST_1006' -> 'AEC-1'
            
    print(f"Loaded {len(code_map)} common course structure codes into memory.")

    batch_size = 5000
    
    # Exclude batch__name='2024-28' and exam_type='REGULAR' at the same time
    queryset = StudentCourseAssessment.objects.exclude(
        batch__name="2024-28", 
        exam_type="REGULAR"
    )
    
    total_count = queryset.count()
    print(f"Total StudentCourseAssessment records to process: {total_count}")
    
    updated_count = 0
    processed_count = 0
    start_time = time.time()
    
    updates = []
    
    for a in queryset.iterator(chunk_size=batch_size):
        processed_count += 1
        if a.paper_code:
            # Extract numeric part from paper_code: e.g., 'BA1006' -> '1006'
            numeric_match = re.search(r'\d+', a.paper_code)
            if numeric_match and a.semester:
                num = numeric_match.group()
                key = f"{a.semester}_{num}"
                if key in code_map:
                    common_course_type = code_map[key] # e.g., 'AEC-1'
                    main_course_type = common_course_type.split('-')[0] # e.g., 'AEC'
                    
                    # Check if it needs updating
                    if a.course_code != common_course_type or a.course_type != main_course_type:
                        a.course_code = common_course_type
                        a.course_type = main_course_type
                        updates.append(a)
                        
        # Flush batch
        if len(updates) >= batch_size:
            with transaction.atomic():
                StudentCourseAssessment.objects.bulk_update(updates, ['course_code', 'course_type'], batch_size=batch_size)
            updated_count += len(updates)
            updates.clear()
            
        # Log progress periodically
        if processed_count % 10000 == 0:
            elapsed = time.time() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0
            print(f"Processed {processed_count}/{total_count} (Updated: {updated_count}) | Rate: {rate:.0f} rec/sec")
            
    # Flush remaining
    if updates:
        with transaction.atomic():
            StudentCourseAssessment.objects.bulk_update(updates, ['course_code', 'course_type'], batch_size=batch_size)
        updated_count += len(updates)
        updates.clear()
            
    print("\n" + "="*50)
    print("Database Update Complete!")
    print(f"Total Processed: {processed_count}")
    print(f"Total Updated:   {updated_count}")
    print("="*50)

if __name__ == '__main__':
    main()
