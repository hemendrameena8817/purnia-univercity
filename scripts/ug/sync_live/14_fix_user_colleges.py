import os
import sys
import django
from pathlib import Path
from django.db import connections

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from accounts.models import UserAccount
from ug.models import SemesterRegistration
from colleges.models import College

def fix_user_college_mapping():
    TARGET_BATCH_NAME = '2024-28'
    TARGET_SEM = 3
    TARGET_SESSION = '2025-26'
    
    print("🚀 Fixing User -> College Mapping (via College Code)...")
    
    # 1. Build Map: College Code -> Live College ID
    print("   📊 Building College Map (Code -> ID)...")
    college_map = {
        c.college_code: c.id 
        for c in College.objects.using('live').exclude(college_code__isnull=True)
    }
    print(f"   ✅ Mapped {len(college_map)} colleges by code.")

    # 2. Iterate Source Registrations (Source of Truth)
    print("   📥 Fetching Source Registrations...")
    source_regs = SemesterRegistration.objects.using('default').filter(
        sem=TARGET_SEM,
        batch__name=TARGET_BATCH_NAME,
        session=TARGET_SESSION
    ).select_related('student__user', 'student__college')
    
    print(f"   ✅ Found {source_regs.count()} registrations to check.")
    
    updated_count = 0
    missing_code_count = 0
    missing_user_count = 0
    error_count = 0
    
    # Pre-fetch Live Users to optimize
    # We can't fetch all 30k at once? Actually 30k is fine.
    # But let's do it in batches to be safe and allow user updates.
    
    BATCH_SIZE = 1000
    
    print("   🔄 Starting Fix Loop...")
    
    # We will process source regs in chunks
    regs_iterator = source_regs.iterator(chunk_size=2000)
    
    current_batch_users = {} # username -> Live User Obj
    current_batch_data = [] # (username, target_college_id)
    
    for i, reg in enumerate(regs_iterator):
        username = reg.student.user.username
        src_college = reg.student.college
        
        if not src_college or not src_college.college_code:
            missing_code_count += 1
            continue
            
        target_college_id = college_map.get(src_college.college_code)
        
        if not target_college_id:
            # print(f"      ⚠️ College Code {src_college.college_code} not found in Live DB.")
            missing_code_count += 1
            continue
            
        current_batch_data.append((username, target_college_id))
        
        # Process Batch
        if len(current_batch_data) >= BATCH_SIZE:
            _process_user_batch(current_batch_data)
            updated_count += len(current_batch_data)
            print(f"      ⏳ Processed {i+1} users...", end='\r')
            current_batch_data = []

    # Final batch
    if current_batch_data:
        _process_user_batch(current_batch_data)
        updated_count += len(current_batch_data)

    print(f"\n✅ Done! Checked/Updated: {updated_count}")
    print(f"   Missing/Invalid College Codes: {missing_code_count}")

def _process_user_batch(batch_data):
    """
    batch_data: list of (username, target_college_id)
    """
    usernames = [b[0] for b in batch_data]
    
    # Fetch Live Users
    live_users = UserAccount.objects.using('live').filter(username__in=usernames)
    user_map = {u.username: u for u in live_users}
    
    users_to_update = []
    
    for username, target_cid in batch_data:
        user = user_map.get(username)
        if user:
            # Only update if different
            if user.college_id != target_cid:
                user.college_id = target_cid
                users_to_update.append(user)
    
    # Bulk Update
    if users_to_update:
        try:
            UserAccount.objects.using('live').bulk_update(users_to_update, ['college'])
        except Exception as e:
            print(f"\n      ❌ Bulk update failed: {e}. Retrying one-by-one...")
            # Fallback
            for u in users_to_update:
                try:
                    u.save(using='live', update_fields=['college'])
                except:
                    pass

if __name__ == "__main__":
    fix_user_college_mapping()
