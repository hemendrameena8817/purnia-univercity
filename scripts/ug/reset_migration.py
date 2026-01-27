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

from ug.models import StudentCourseAssessment
from staging.models import UGSemResultCurrent

print("=" * 80)
print("RESET SCRIPT: Clear All Data and Reset Staging Flags")
print("=" * 80)

# Step 1: Delete StudentCourseAssessment in batches
print("\n🗑️  Step 1: Deleting StudentCourseAssessment records in batches...")
batch_size = 10000
total_deleted = 0

while True:
    # Get IDs of next batch
    ids = list(StudentCourseAssessment.objects.values_list('id', flat=True)[:batch_size])
    if not ids:
        break
    
    # Delete this batch
    StudentCourseAssessment.objects.filter(id__in=ids).delete()
    total_deleted += len(ids)
    print(f"   Deleted {total_deleted:,} records...")

print(f"✅ Total deleted: {total_deleted:,} records\n")

# Step 2: Reset is_migrated flag
print("🔄 Step 2: Resetting is_migrated flags...")
migrated_count = UGSemResultCurrent.objects.filter(is_migrated=True).count()
print(f"   Resetting {migrated_count:,} staging records...")
UGSemResultCurrent.objects.update(is_migrated=False)
print(f"✅ All staging records marked as unmigrated\n")

# Verify
final_count = StudentCourseAssessment.objects.count()
unmigrated_count = UGSemResultCurrent.objects.filter(is_migrated=False).count()
print("=" * 80)
print("📊 FINAL STATUS:")
print("=" * 80)
print(f"   StudentCourseAssessment: {final_count:,} records")
print(f"   Unmigrated staging: {unmigrated_count:,} records")
print(f"\n✅ Ready to run migration!\n")
