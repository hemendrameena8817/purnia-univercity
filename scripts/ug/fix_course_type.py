import os
import sys
import django
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import CourseStructure

print("=" * 80)
print("🔧 FIXING COURSE_TYPE IN COURSESTRUCTURE")
print("=" * 80)

# Get all course structures
all_courses = CourseStructure.objects.all()
total = all_courses.count()

print(f"\n📊 Found {total:,} course structure records")
print(f"Updating course_type to extract prefix from course_code...\n")

updated_count = 0
batch_updates = []

for course in all_courses:
    if course.course_code and '-' in course.course_code:
        # Extract prefix (MJC from MJC-1, MIC from MIC-1, etc.)
        new_type = course.course_code.split('-')[0]
        
        if course.course_type != new_type:
            course.course_type = new_type
            batch_updates.append(course)
            updated_count += 1
            
            # Bulk update every 1000 records
            if len(batch_updates) >= 1000:
                CourseStructure.objects.bulk_update(batch_updates, ['course_type'])
                print(f"  ✅ Updated {updated_count:,} records...")
                batch_updates = []

# Update remaining records
if batch_updates:
    CourseStructure.objects.bulk_update(batch_updates, ['course_type'])
    print(f"  ✅ Updated {updated_count:,} records...")

print(f"\n{'=' * 80}")
print(f"✅ COURSE_TYPE UPDATE COMPLETE")
print(f"{'=' * 80}")
print(f"Total records updated: {updated_count:,}")
print(f"Total records checked: {total:,}")

# Verify
print(f"\n🔍 VERIFICATION:")
from django.db.models import Count
type_counts = CourseStructure.objects.values('course_type').annotate(count=Count('id')).order_by('-count')
print(f"\nCourse type distribution:")
for item in type_counts[:10]:
    print(f"  {item['course_type']}: {item['count']:,} records")

print()
