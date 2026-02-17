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

from ug.models import SemesterRegistration, UGStudentProfile, UGBatch

def reset_db_connection(alias='live'):
    try:
        connections[alias].close()
    except:
        pass

def sync_missing_only():
    TARGET_BATCH_NAME = '2024-28'
    TARGET_SEM = 3
    TARGET_SESSION = '2025-26'
    
    # 1. Get Live Batch ID
    try:
        live_batch = UGBatch.objects.using('live').get(name=TARGET_BATCH_NAME)
        live_batch_id = live_batch.id
        print(f"✅ Found Live Batch: {live_batch.name}")
    except Exception as e:
        print(f"❌ Error fetching Batch: {e}")
        return

    # 2. Fetch Existing UIDs from Live (Optimization)
    print("📥 Fetching existing Live UIDs to skip duplicates...")
    existing_uids = set()
    try:
        # Fetching only UIDs is very lightweight
        # We use iterator to be memory efficient just in case
        qs = SemesterRegistration.objects.using('live').filter(
            sem=TARGET_SEM, 
            batch_id=live_batch_id, 
            session=TARGET_SESSION
        ).values_list('uid', flat=True)
        
        for uid in qs.iterator(chunk_size=5000):
            existing_uids.add(str(uid))
            
        print(f"✅ Found {len(existing_uids)} existing records in Live DB.")
    except Exception as e:
        print(f"❌ Error fetching existing UIDs: {e}")
        return

    # 3. Process Source Records
    print("🔄 Processing Source Records for Missing Items...")
    
    # We iterate source records in small batches to avoid source DB timeouts
    BATCH_SIZE = 1000
    last_id = 0
    
    created_count = 0
    skipped_count = 0
    missing_user_count = 0
    
    while True:
        try:
            # Fetch batch from source
            source_batch = list(
                SemesterRegistration.objects.using('default')
                .filter(sem=TARGET_SEM, batch__name=TARGET_BATCH_NAME, session=TARGET_SESSION, id__gt=last_id)
                .select_related('student__user')
                .order_by('id')[:BATCH_SIZE]
            )
            
            if not source_batch:
                break # Done
            
            last_id = source_batch[-1].id
            
            # Filter for missing ones *in memory* first
            missing_batch = [r for r in source_batch if str(r.uid) not in existing_uids]
            skipped_in_batch = len(source_batch) - len(missing_batch)
            skipped_count += skipped_in_batch
            
            if not missing_batch:
                print(f"   ⏩ {skipped_in_batch} records already exist. Moving to next batch...", end='\r')
                continue
                
            print(f"   ⚡ Found {len(missing_batch)} missing records in batch. Syncing...", end='\r')
            
            # Resolve Users for Missing Batch
            usernames = [r.student.user.username for r in missing_batch]
            student_map = {}
            
            # Fetch Live Users for this batch (robust fetch)
            for attempt in range(3):
                try:
                    live_users = UGStudentProfile.objects.using('live').filter(
                        user__username__in=usernames
                    ).select_related('user').values('user__username', 'id')
                    student_map = {u['user__username']: u['id'] for u in live_users}
                    break
                except Exception:
                    reset_db_connection('live')
                    time.sleep(1)
            
            # Perform Sync One-by-One (Robust)
            for reg in missing_batch:
                username = reg.student.user.username
                if username not in student_map:
                    missing_user_count += 1
                    continue
                
                live_student_id = student_map[username]
                
                # Try create
                for attempt in range(3):
                    try:
                        SemesterRegistration.objects.using('live').create(
                            uid=reg.uid,
                            student_id=live_student_id,
                            batch_id=live_batch_id,
                            start_date=reg.start_date,
                            end_date=reg.end_date,
                            is_open=reg.is_open,
                            sem=reg.sem,
                            status=reg.status,
                            exam_eligible=reg.exam_eligible,
                            remarks=reg.remarks,
                            session=reg.session,
                            json_data=reg.json_data,
                            # created_at=reg.created_at, # created_at is auto_now_add, difficult to force without bulk_create or updating later
                            # updated_at=reg.updated_at
                        )
                        created_count += 1
                        break
                    except Exception as e:
                        if "Duplicate entry" in str(e): # Race condition check
                            break 
                        reset_db_connection('live')
                        time.sleep(0.5)
            
            print(f"   ✅ Created {created_count} | Skipped (Exist): {skipped_count} | Missing User: {missing_user_count}", end='\r')
            
        except Exception as e:
            print(f"\n   ❌ Batch fetch error: {e}. Retrying same offset...")
            reset_db_connection('default')
            time.sleep(2)
            # In retry logic, we might need to adjust `last_id` if we want to retry exact batch,
            # but getting `last_id` relies on successful fetch. 
            # If batch fetch fails, `last_id` isn't updated, so `continue` works perfectly to retry.
            continue

    print(f"\n\n🎉 Sync Complete!")
    print(f"   Total Created: {created_count}")
    print(f"   Total Skipped (Already Exists): {skipped_count}")
    print(f"   Total Missing Users in Live: {missing_user_count}")

if __name__ == "__main__":
    sync_missing_only()
