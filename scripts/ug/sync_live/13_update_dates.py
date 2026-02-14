import os
import sys
import django
from pathlib import Path
from django.utils import timezone
from datetime import datetime, time as datetime_time
import pytz

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import SemesterRegistration

def update_registration_dates():
    # Configuration
    TARGET_BATCH_NAME = '2024-28'
    TARGET_SEM = 3
    TARGET_SESSION = '2025-26'
    
    # Dates (India Time - Asia/Kolkata)
    tz = pytz.timezone('Asia/Kolkata')
    
    # Feb 15, 2026 at 10:00 AM
    start_dt = tz.localize(datetime(2026, 2, 15, 3, 30, 0))
    
    # Feb 20, 2026 at 11:59 PM
    end_dt = tz.localize(datetime(2026, 2, 20, 23, 59, 59))
    
    print(f"🚀 Updating Semester Registration Dates (Live DB)")
    print(f"   Batch: {TARGET_BATCH_NAME} | Sem: {TARGET_SEM}")
    print(f"   New Start: {start_dt}")
    print(f"   New End:   {end_dt}")
    
    # Update Query
    try:
        updated_count = SemesterRegistration.objects.using('default').filter(
            sem=TARGET_SEM,
            batch__name=TARGET_BATCH_NAME,
            session=TARGET_SESSION
        ).update(
            start_date=start_dt,
            end_date=end_dt,
            is_open=True ,
            status='OPEN'
        )
        
        print(f"\n✅ Successfully updated {updated_count} records!")
        
    except Exception as e:
        print(f"\n❌ Error updating dates: {e}")

if __name__ == "__main__":
    update_registration_dates()
