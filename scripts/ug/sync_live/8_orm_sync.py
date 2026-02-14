import os
import django
import sys
from pathlib import Path
from django.db import connections
from django.db.utils import OperationalError

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from accounts.models import UserAccount
from ug.models import UGStudentProfile, UGBatch, UGDepartment, UGProgram, UGDegree
from colleges.models import College

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

def sync_students():
    TARGET_BATCH_NAME = "2024-28"
    print(f"ORM Sync for '{TARGET_BATCH_NAME}' (one-by-one, skip errors)...")

    try:
        source_batch = UGBatch.objects.using('default').get(name=TARGET_BATCH_NAME)
        target_batch = UGBatch.objects.using('live').get(name=TARGET_BATCH_NAME)
    except UGBatch.DoesNotExist:
        print("Batch missing!")
        return

    maps = get_maps()
    connections['live'].close()
    
    source_qs = UGStudentProfile.objects.using('default').filter(batch=source_batch).select_related(
        'user', 'user__college', 'college', 'department', 'program', 'degree', 'major_course', 'minor_course', 'mdc_course'
    ).order_by('id')
    
    total = source_qs.count()
    print(f"Total: {total} students")
    print("Processing...")
    
    success = 0
    failed = 0
    
    for i, s in enumerate(source_qs.iterator(chunk_size=1000)):
        if i % 100 == 0:
            print(f"Progress: {i}/{total} (✓{success} ✗{failed})", flush=True)
        
        try:
            if i % 50 == 0:
                connections['live'].close()
            
            # Update or create user
            try:
                user = UserAccount.objects.using('live').get(username=s.user.username)
                user.email = s.user.email
                user.first_name = s.user.first_name
                user.last_name = s.user.last_name
                user.phone = s.user.phone
                user.current_profile = s.user.current_profile
                user.is_active = s.user.is_active
                user.user_type = 'student'
                if s.user.college:
                    cid = get_id(s.user.college, maps['college'])
                    if cid: user.college_id = cid
                user.save(using='live')
            except UserAccount.DoesNotExist:
                user = UserAccount(
                    uid=s.user.uid,
                    username=s.user.username,
                    email=s.user.email,
                    first_name=s.user.first_name,
                    last_name=s.user.last_name,
                    phone=s.user.phone,
                    user_type='student',
                    current_profile=s.user.current_profile,
                    is_active=s.user.is_active,
                )
                if s.user.college:
                    cid = get_id(s.user.college, maps['college'])
                    if cid: user.college_id = cid
                user.save(using='live')
            
            # Create profile if missing
            if not UGStudentProfile.objects.using('live').filter(user_id=user.id).exists():
                UGStudentProfile.objects.using('live').create(
                    user_id=user.id,
                    first_name=s.first_name,
                    last_name=s.last_name,
                    hindi_name=s.hindi_name,
                    registration_no=s.registration_no,
                    address=s.address,
                    admission_date=s.admission_date,
                    date_of_birth=s.date_of_birth,
                    aadhar_no=s.aadhar_no,
                    apaar_id=s.apaar_id,
                    mobile_no=s.mobile_no,
                    migration_submitted=s.migration_submitted,
                    last_university=s.last_university,
                    gender=s.gender,
                    caste=s.caste,
                    enrollment_date=s.enrollment_date,
                    roll_no=s.roll_no,
                    father_name=s.father_name,
                    mother_name=s.mother_name,
                    current_semester=s.current_semester,
                    session=s.session,
                    status=s.status,
                    profile_image=s.profile_image,
                    signature=s.signature,
                    is_active=s.is_active,
                    json_data=s.json_data,
                    batch=target_batch,
                    college_id=get_id(s.college, maps['college']),
                    department_id=get_id(s.department, maps['dept']),
                    program_id=get_id(s.program, maps['program']),
                    degree_id=get_id(s.degree, maps['degree']),
                    major_course_id=get_id(s.major_course, maps['dept']),
                    minor_course_id=get_id(s.minor_course, maps['dept']),
                    mdc_course_id=get_id(s.mdc_course, maps['dept']),
                )
            
            success += 1
            
        except OperationalError:
            connections['live'].close()
            failed += 1
            continue
        except Exception as e:
            failed += 1
            continue
    
    print(f"\n✅ Done! Success: {success}/{total}, Failed: {failed}")

if __name__ == "__main__":
    sync_students()
