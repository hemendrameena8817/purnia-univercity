import os
import sys
import django
import time
from pathlib import Path
from django.db import connections, OperationalError, InterfaceError

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import SemesterRegistration, UGStudentProfile, UGBatch

def reset_db_connection(alias='live'):
    """Force close and reset a DB connection."""
    try:
        connections[alias].close()
    except Exception:
        pass

def sync_lazy_robust():
    TARGET_BATCH_NAME = '2024-28'
    TARGET_SEM = 3
    TARGET_SESSION = '2025-26'
    
    print(f"🚀 Syncing Semester Registrations (Lazy Mode)")
    print("   Strategy: Fetch and map data in small batches to avoid timeouts.")

    # 1. Get Live Batch ID (Single small query)
    try:
        live_batch = UGBatch.objects.using('live').get(name=TARGET_BATCH_NAME)
        live_batch_id = live_batch.id
        print(f"   ✅ Found Live Batch: {live_batch.name}")
    except Exception as e:
        print(f"   ❌ Error fetching Batch: {e}")
        return

    # 2. Lazy Process Source Records
    BATCH_SIZE = 50
    start_offset = 0
    total_synced = 0
    
    print("   � Starting Loop...")
    
    while True:
        try:
            # A. Fetch small batch from Source
            # We don't use iterator() to avoid long-lived cursor issues on Source DB too
            records = list(
                SemesterRegistration.objects.using('default')
                .filter(sem=TARGET_SEM, batch__name=TARGET_BATCH_NAME, session=TARGET_SESSION)
                .select_related('student__user')
                .order_by('id')[start_offset : start_offset + BATCH_SIZE]
            )
            
            if not records:
                break # Done
            
            # B. Fetch *Corresponding* Live Students
            usernames = [r.student.user.username for r in records]
            
            # Retry logic for fetching live users
            student_map = {}
            for attempt in range(3):
                try:
                    live_users = UGStudentProfile.objects.using('live').filter(
                        user__username__in=usernames
                    ).select_related('user').values('user__username', 'id')
                    
                    student_map = {u['user__username']: u['id'] for u in live_users}
                    break
                except Exception as e:
                    print(f"      Running... (Con: {e}, Retrying...)")
                    reset_db_connection('live')
                    time.sleep(1)

            # C. Sync Records
            count_in_batch = 0
            for reg in records:
                username = reg.student.user.username
                if username not in student_map:
                    # User missing in live, skip
                    continue
                    
                live_student_id = student_map[username]
                
                # Try Sync Single Record
                for attempt in range(3):
                    try:
                        SemesterRegistration.objects.using('live').update_or_create(
                            uid=reg.uid,
                            defaults={
                                'student_id': live_student_id,
                                'batch_id': live_batch_id,
                                'start_date': reg.start_date,
                                'end_date': reg.end_date,
                                'is_open': reg.is_open,
                                'sem': reg.sem,
                                'status': reg.status,
                                'exam_eligible': reg.exam_eligible,
                                'remarks': reg.remarks,
                                'session': reg.session,
                                'json_data': reg.json_data,
                            }
                        )
                        count_in_batch += 1
                        break
                    except Exception as e:
                         # print(f"      Record sync error: {e}, retrying...")
                         reset_db_connection('live')
                         time.sleep(0.5)

            total_synced += count_in_batch
            start_offset += len(records)
            
            print(f"   ⏳ Progress: {start_offset} records checked | {total_synced} synced.", end='\r')
            
        except Exception as e:
            print(f"\n   ❌ Batch Error at offset {start_offset}: {e}")
            # Likely source DB connection issue, reset and retry same offset
            reset_db_connection('default')
            time.sleep(2)
            # Don't increment offset, retry same batch
            continue

    print(f"\n\n✅ Sync Complete! Total Synced: {total_synced}")

if __name__ == "__main__":
    sync_lazy_robust()
