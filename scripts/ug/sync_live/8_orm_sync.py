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
    BATCH_SIZE = 20  # Process 20 students at a time
    
    print(f"FASTER ORM Sync for '{TARGET_BATCH_NAME}' (micro-batch: {BATCH_SIZE})...")

    try:
        source_batch = UGBatch.objects.using('default').get(name=TARGET_BATCH_NAME)
        target_batch = UGBatch.objects.using('live').get(name=TARGET_BATCH_NAME)
    except UGBatch.DoesNotExist:
        print("Batch missing!")
        return

    maps = get_maps()
    
    source_qs = UGStudentProfile.objects.using('default').filter(batch=source_batch).select_related(
        'user', 'user__college', 'college', 'department', 'program', 'degree', 'major_course', 'minor_course', 'mdc_course'
    ).order_by('id')
    
    total = source_qs.count()
    print(f"Total: {total} students in batches of {BATCH_SIZE}")
    print("Starting sync...")
    
    success = 0
    failed = 0
    batch = []
    
    for i, s in enumerate(source_qs.iterator(chunk_size=100)):
        batch.append(s)
        
        # Process when batch is full or at end
        if len(batch) >= BATCH_SIZE or i == total - 1:
            if i % 100 == 0:
                print(f"Progress: {i}/{total} (✓{success} ✗{failed})", flush=True)
            
            try:
                # Reset connection every 200 students
                if i % 200 == 0:
                    connections['live'].close()
                
                # Process batch
                usernames = [s.user.username for s in batch]
                existing_users = {u.username: u for u in UserAccount.objects.using('live').filter(username__in=usernames)}
                
                users_to_update = []
                users_to_create = []
                
                # Prepare user operations
                for s in batch:
                    if s.user.username in existing_users:
                        u = existing_users[s.user.username]
                        u.email = s.user.email
                        u.first_name = s.user.first_name
                        u.last_name = s.user.last_name
                        u.phone = s.user.phone
                        u.current_profile = s.user.current_profile
                        u.is_active = s.user.is_active
                        u.user_type = 'student'
                        if s.user.college:
                            cid = get_id(s.user.college, maps['college'])
                            if cid: u.college_id = cid
                        users_to_update.append(u)
                    else:
                        u = UserAccount(
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
                            if cid: u.college_id = cid
                        users_to_create.append(u)
                
                # Execute user updates (one by one - fast enough)
                for u in users_to_update:
                    u.save(using='live')
                
                # Execute user creates
                if users_to_create:
                    UserAccount.objects.using('live').bulk_create(users_to_create, ignore_conflicts=True)
                
                # Refresh user map
                existing_users = {u.username: u for u in UserAccount.objects.using('live').filter(username__in=usernames)}
                
                # Create profiles in bulk
                existing_profile_user_ids = set(
                    UGStudentProfile.objects.using('live').filter(
                        user_id__in=[u.id for u in existing_users.values()]
                    ).values_list('user_id', flat=True)
                )
                
                profiles_to_create = []
                for s in batch:
                    user = existing_users.get(s.user.username)
                    if user and user.id not in existing_profile_user_ids:
                        profiles_to_create.append(UGStudentProfile(
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
                        ))
                
                if profiles_to_create:
                    UGStudentProfile.objects.using('live').bulk_create(profiles_to_create, ignore_conflicts=True)
                
                success += len(batch)
                
            except OperationalError:
                connections['live'].close()
                failed += len(batch)
            except Exception as e:
                failed += len(batch)
            
            # Clear batch
            batch = []
    
    print(f"\n✅ Done! Success: {success}/{total}, Failed: {failed}")

if __name__ == "__main__":
    sync_students()
