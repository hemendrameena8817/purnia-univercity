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
from ug.models import UGStudentProfile, UGBatch, UGDepartment, UGProgram, UGDegree, SemesterRegistration
from colleges.models import College

def close_db():
    try: connections['live'].close()
    except: pass
    try: connections['default'].close()
    except: pass

def get_maps():
    return {
        'dept': {str(d.uid): d.id for d in UGDepartment.objects.using('live').all()},
        'college': {str(c.uid): c.id for c in College.objects.using('live').all()},
        'program': {str(p.uid): p.id for p in UGProgram.objects.using('live').all()},
        'degree': {str(d.uid): d.id for d in UGDegree.objects.using('live').all()},
    }

def get_id(src_obj, mapping):
    if not src_obj: return None
    return mapping.get(str(src_obj.uid))

def sync_gap_filler():
    TARGET_BATCH_NAME = '2024-28'
    TARGET_SEM = 3
    print("🚀 Starting Gap Filler Sync...")
    
    # 1. Fetch Basic Data
    try:
        live_batch_id = UGBatch.objects.using('live').get(name=TARGET_BATCH_NAME).id
        maps = get_maps()
    except Exception as e:
        print(f"❌ Init failed: {e}")
        return

    # 2. Find Missing UIDs (The Gap)
    print("📥 Calculating Gap...")
    source_uids = set(str(u) for u in SemesterRegistration.objects.using('default').filter(sem=TARGET_SEM, batch__name=TARGET_BATCH_NAME).values_list('uid', flat=True))
    live_uids = set(str(u) for u in SemesterRegistration.objects.using('live').filter(sem=TARGET_SEM, batch__name=TARGET_BATCH_NAME).values_list('uid', flat=True))
    
    missing_uids = source_uids - live_uids
    print(f"✅ Found {len(missing_uids)} missing registrations to sync.")
    
    if not missing_uids:
        print("🎉 No gap found!")
        return

    # 3. Process Missing One-by-One
    count = 0
    errors = 0
    
    # Fetch source objects for missing UIDs
    # We fetch in small batches to keep memory low
    missing_uids_list = list(missing_uids)
    
    print("🔄 Starting processing...")
    
    BATCH_SIZE = 100
    for i in range(0, len(missing_uids_list), BATCH_SIZE):
        batch_uids = missing_uids_list[i : i+BATCH_SIZE]
        
        # Fetch source details
        source_regs = SemesterRegistration.objects.using('default').filter(uid__in=batch_uids).select_related(
            'student__user', 
            'student__user__college', 
            'student__college', 
            'student__department', 
            'student__program', 
            'student__degree', 
            'student__major_course', 
            'student__minor_course', 
            'student__mdc_course'
        )
        
        for reg in source_regs:
            try:
                # A. Ensure User Account
                src_user = reg.student.user
                uname = src_user.username
                
                live_user_id = None
                try:
                    u = UserAccount.objects.using('live').get(username=uname)
                    live_user_id = u.id
                except UserAccount.DoesNotExist:
                    # Create User
                    u = UserAccount(
                        username=uname,
                        uid=src_user.uid,
                        email=src_user.email,
                        first_name=src_user.first_name,
                        last_name=src_user.last_name,
                        phone=src_user.phone,
                        user_type='student',
                        is_active=src_user.is_active,
                        college_id=get_id(src_user.college, maps['college'])
                    )
                    u.save(using='live')
                    live_user_id = u.id

                # B. Ensure Profile
                src_p = reg.student
                live_profile_id = None
                
                try:
                    p = UGStudentProfile.objects.using('live').get(user_id=live_user_id)
                    live_profile_id = p.id
                except UGStudentProfile.DoesNotExist:
                    # Create Profile
                    p = UGStudentProfile(
                        user_id=live_user_id,
                        first_name=src_p.first_name,
                        last_name=src_p.last_name,
                        hindi_name=src_p.hindi_name,
                        registration_no=src_p.registration_no,
                        address=src_p.address,
                        admission_date=src_p.admission_date,
                        date_of_birth=src_p.date_of_birth,
                        aadhar_no=src_p.aadhar_no,
                        apaar_id=src_p.apaar_id,
                        mobile_no=src_p.mobile_no,
                        migration_submitted=src_p.migration_submitted,
                        last_university=src_p.last_university,
                        gender=src_p.gender,
                        caste=src_p.caste,
                        enrollment_date=src_p.enrollment_date,
                        roll_no=src_p.roll_no,
                        father_name=src_p.father_name,
                        mother_name=src_p.mother_name,
                        current_semester=src_p.current_semester,
                        session=src_p.session,
                        status=src_p.status,
                        is_active=src_p.is_active,
                        json_data=src_p.json_data,
                        batch_id=live_batch_id,
                        college_id=get_id(src_p.college, maps['college']),
                        department_id=get_id(src_p.department, maps['dept']),
                        program_id=get_id(src_p.program, maps['program']),
                        degree_id=get_id(src_p.degree, maps['degree']),
                        major_course_id=get_id(src_p.major_course, maps['dept']),
                        minor_course_id=get_id(src_p.minor_course, maps['dept']),
                        mdc_course_id=get_id(src_p.mdc_course, maps['dept']),
                    )
                    p.save(using='live')
                    live_profile_id = p.id

                # C. Create Registration
                SemesterRegistration.objects.using('live').create(
                    uid=reg.uid,
                    student_id=live_profile_id,
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
                )
                count += 1
                
            except Exception as e:
                print(f"   ❌ Failed {reg.student.user.username}: {e}")
                errors += 1
                close_db()
                time.sleep(1) # Panic wait
            
            print(f"   ⏳ Progress: {count+errors}/{len(missing_uids)} (Ok:{count} Err:{errors})", end='\r')

    print(f"\n✅ Finished! Synced: {count}, Errors: {errors}")

if __name__ == "__main__":
    sync_gap_filler()
