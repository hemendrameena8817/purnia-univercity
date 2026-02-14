import os
import sys
import django
import time
from pathlib import Path
from django.db import connections, OperationalError

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from accounts.models import UserAccount
from ug.models import UGStudentProfile, UGBatch, UGDepartment, UGProgram, UGDegree, SemesterRegistration
from colleges.models import College

def reset_db_connection(alias='live'):
    try:
        connections[alias].close()
    except Exception:
        pass

def get_maps():
    print("   📊 Fetching Maps for FKs...")
    try:
        return {
            'dept': {str(d.uid): d.id for d in UGDepartment.objects.using('live').all()},
            'college': {str(c.uid): c.id for c in College.objects.using('live').all()},
            'program': {str(p.uid): p.id for p in UGProgram.objects.using('live').all()},
            'degree': {str(d.uid): d.id for d in UGDegree.objects.using('live').all()},
        }
    except Exception as e:
        print(f"   ❌ Error fetching maps: {e}")
        return {}

def get_id(src_obj, mapping):
    if not src_obj: return None
    return mapping.get(str(src_obj.uid))

def sync_missing_users_bulk():
    TARGET_BATCH_NAME = '2024-28'
    TARGET_SEM = 3
    TARGET_SESSION = '2025-26'
    
    print(f"🚀 Syncing Missing Users + Registrations (Bulk Optimized)")

    # 1. Fetch Live Batch ID
    try:
        live_batch = UGBatch.objects.using('live').get(name=TARGET_BATCH_NAME)
        live_batch_id = live_batch.id
    except Exception as e:
        print(f"   ❌ Error fetching Batch: {e}")
        return

    # 2. Build Mappings
    maps = get_maps()
    if not maps: return

    # 3. Fetch Missing Profiles
    print("   📥 Finding missing profiles...")
    live_profile_usernames = set(UGStudentProfile.objects.using('live').values_list('user__username', flat=True))
    
    source_regs = SemesterRegistration.objects.using('default').filter(
        sem=TARGET_SEM,
        batch__name=TARGET_BATCH_NAME,
        session=TARGET_SESSION
    ).select_related('student__user')
    
    missing_regs = []
    missing_usernames = set()
    
    for reg in source_regs.iterator(chunk_size=5000):
        uname = reg.student.user.username
        if uname not in live_profile_usernames:
            missing_regs.append(reg)
            missing_usernames.add(uname)
            
    print(f"   ✅ Found {len(missing_regs)} regs with {len(missing_usernames)} missing users.")
    if not missing_regs: return

    # Fetch Source Profiles for these users
    source_profiles = UGStudentProfile.objects.using('default').filter(
        user__username__in=missing_usernames
    ).select_related(
        'user', 'user__college', 'college', 'department', 'program', 'degree', 'major_course', 'minor_course', 'mdc_course'
    )
    profile_map = {p.user.username: p for p in source_profiles}

    # BATCH PROCESS
    BATCH_SIZE = 50 
    # Smaller batch size for connection stability, but bulk operations
    
    users_to_create = [] # (username, user_obj)
    profiles_to_create = []
    
    # We process in chunks to flush to DB frequently
    chunk_regs = []
    
    total_processed = 0
    
    print("   🔄 Starting Batch Sync...")

    print("   🔄 Starting Hybrid Sync (Bulk -> One-by-One Fallback)...")

    for i, reg in enumerate(missing_regs):
        chunk_regs.append(reg)
        
        if len(chunk_regs) >= BATCH_SIZE or i == len(missing_regs) - 1:
            # Try Bulk
            try:
                _process_chunk(chunk_regs, profile_map, maps, live_batch_id)
                total_processed += len(chunk_regs)
                print(f"      ⏳ Processed {total_processed}/{len(missing_regs)}...", end='\r')
            except Exception as e:
                # Fallback to One-by-One
                reset_db_connection('live')
                for single_reg in chunk_regs:
                    try:
                        _process_chunk([single_reg], profile_map, maps, live_batch_id)
                        total_processed += 1
                        print(f"      ⏳ Processed {total_processed}/{len(missing_regs)}...", end='\r')
                    except Exception as e2:
                        print(f"\n      ❌ Failed {single_reg.student.user.username}: {e2}")
                        reset_db_connection('live')
            
            chunk_regs = []

    print("\n\n🎉 Done!")

def _process_chunk(regs, profile_map, maps, live_batch_id):
    # This function handles a small batch (~50) safely
    
    # 1. Ensure Users Exist (Bulk Check/Create)
    chunk_usernames = list(set(r.student.user.username for r in regs))
    
    # Check existing in Live (to avoid errors)
    existing_live_users = set(UserAccount.objects.using('live').filter(username__in=chunk_usernames).values_list('username', flat=True))
    
    new_users = []
    for uname in chunk_usernames:
        if uname not in existing_live_users:
            src_profile = profile_map.get(uname)
            if not src_profile: continue
            
            new_users.append(UserAccount(
                username=uname,
                uid=src_profile.user.uid, # Try to keep UID sync if possible
                email=src_profile.user.email,
                first_name=src_profile.user.first_name,
                last_name=src_profile.user.last_name,
                phone=src_profile.user.phone,
                user_type='student',
                current_profile=src_profile.user.current_profile,
                is_active=src_profile.user.is_active,
                college_id=get_id(src_profile.user.college, maps['college'])
            ))
            
    if new_users:
        UserAccount.objects.using('live').bulk_create(new_users, ignore_conflicts=True)
    
    # 2. Re-fetch Live Users to get IDs
    live_user_map = {
        u['username']: u['id'] 
        for u in UserAccount.objects.using('live').filter(username__in=chunk_usernames).values('username', 'id')
    }
    
    # 3. Ensure Profiles Exist
    # Check existing profiles
    existing_profile_user_ids = set(UGStudentProfile.objects.using('live').filter(user_id__in=live_user_map.values()).values_list('user_id', flat=True))
    
    new_profiles = []
    for uname in chunk_usernames:
        live_uid = live_user_map.get(uname)
        if live_uid and live_uid not in existing_profile_user_ids:
            src = profile_map.get(uname)
            if not src: continue
            
            new_profiles.append(UGStudentProfile(
                user_id=live_uid,
                first_name=src.first_name,
                last_name=src.last_name,
                hindi_name=src.hindi_name,
                registration_no=src.registration_no,
                address=src.address,
                admission_date=src.admission_date,
                date_of_birth=src.date_of_birth,
                aadhar_no=src.aadhar_no,
                apaar_id=src.apaar_id,
                mobile_no=src.mobile_no,
                migration_submitted=src.migration_submitted,
                last_university=src.last_university,
                gender=src.gender,
                caste=src.caste,
                enrollment_date=src.enrollment_date,
                roll_no=src.roll_no,
                father_name=src.father_name,
                mother_name=src.mother_name,
                current_semester=src.current_semester,
                session=src.session,
                status=src.status,
                is_active=src.is_active,
                json_data=src.json_data,
                batch_id=live_batch_id,
                college_id=get_id(src.college, maps['college']),
                department_id=get_id(src.department, maps['dept']),
                program_id=get_id(src.program, maps['program']),
                degree_id=get_id(src.degree, maps['degree']),
                major_course_id=get_id(src.major_course, maps['dept']),
                minor_course_id=get_id(src.minor_course, maps['dept']),
                mdc_course_id=get_id(src.mdc_course, maps['dept']),
            ))
            
    if new_profiles:
        UGStudentProfile.objects.using('live').bulk_create(new_profiles, ignore_conflicts=True)

    # 4. Create Registrations
    # Re-fetch profiles to get IDs
    live_profile_map = {
        p['user__username']: p['id'] 
        for p in UGStudentProfile.objects.using('live').filter(user__username__in=chunk_usernames).select_related('user').values('user__username', 'id')
    }
    
    new_regs = []
    for reg in regs:
        uname = reg.student.user.username
        pid = live_profile_map.get(uname)
        if pid:
            new_regs.append(SemesterRegistration(
                uid=reg.uid,
                student_id=pid,
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
            ))
            
    if new_regs:
        SemesterRegistration.objects.using('live').bulk_create(new_regs, ignore_conflicts=True)

if __name__ == "__main__":
    sync_missing_users_bulk()
