import os
import sys
import django
import time
from pathlib import Path
from django.db import connections

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from accounts.models import UserAccount
from ug.models import SemesterRegistration
from colleges.models import College

def reset_connections():
    try: connections['live'].close()
    except: pass
    try: connections['default'].close()
    except: pass

def simple_college_sync():
    print("🚀 Simple User -> College Sync (Source: Local College Code -> Live College ID)")
    
    # 1. Get Live College Map (Code -> ID)
    print("   📊 Building Live College Map...")
    try:
        live_college_map = {
            c.college_code: c.id 
            for c in College.objects.using('live').exclude(college_code__isnull=True)
        }
    except Exception as e:
        print(f"   ❌ Error fetching live colleges: {e}")
        return

    # 2. Get Target Users (Local Semester Registration)
    # We use this to identify WHICH users to update
    print("   📥 Fetching Local Users (Sem 3, 2024-28)...")
    source_regs = SemesterRegistration.objects.using('default').filter(
        sem=3,
        batch__name='2024-28',
        session='2025-26'
    ).select_related('student__user', 'student__college')
    
    # 3. Iterate and Update
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    print("   🔄 Starting Loop...")
    
    for i, reg in enumerate(source_regs.iterator(chunk_size=2000)):
        try:
            student = reg.student
            if not student or not student.user:
                continue
                
            local_user = student.user
            local_college = student.college
            
            if not local_college or not local_college.college_code:
                # print(f"      ⚠️ No College Code for {local_user.username}")
                skipped_count += 1
                continue
                
            # Get Target College ID from Map
            target_college_id = live_college_map.get(local_college.college_code)
            
            if not target_college_id:
                # print(f"      ⚠️ Code {local_college.college_code} not found in Live.")
                skipped_count += 1
                continue

            # Update Live User
            # We fetch by Username to be safe (IDs might differ)
            # Efficient Update: directly update the field if it exists
            
            # Check/Update Logic
            # We use filter().update() to avoid fetching the full object if possible, 
            # maximizing speed and minimizing memory.
            
            rows = UserAccount.objects.using('live').filter(
                username=local_user.username
            ).update(college_id=target_college_id)
            
            if rows > 0:
                updated_count += 1
            else:
                # User might not exist in live?
                skipped_count += 1

        except Exception as e:
            # print(f"      ❌ Error on {reg.uid}: {e}")
            error_count += 1
            reset_connections()
            time.sleep(0.5)

        if (i + 1) % 100 == 0:
            print(f"      ⏳ Processed {i+1} | Updated: {updated_count} | Errors: {error_count}", end='\r')

    print(f"\n✅ Done!")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped/Missing: {skipped_count}")
    print(f"   Errors: {error_count}")

if __name__ == "__main__":
    simple_college_sync()
