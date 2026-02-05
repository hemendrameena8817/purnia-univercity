import os
import sys
import django
import time
import re
from datetime import datetime
from django.contrib.auth.hashers import make_password

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from pg.models import PGStudentProfile
from accounts.models import UserAccount
from staging.models import PGResultCurrent, RegisteredApplicantMaster

def parse_date(date_str):
    """Parse date string."""
    if not date_str:
        return None
    
    formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except:
            continue
    return None

def parse_semester(sem_str):
    """Parse semester string like 'SEM-1' or '1' to int."""
    if not sem_str:
        return None
    try:
        # Extract first digit found
        match = re.search(r'\d+', str(sem_str))
        if match:
            return int(match.group())
    except:
        pass
    return None

def migrate():
    print("\n" + "="*80)
    print("PG STUDENT IMPORT & UPDATE (Source: PGResultCurrent)")
    print("="*80)
    
    start = time.time()
    
    # 1. Identify Target Students (From PGResultCurrent)
    print("📊 Fetching target students from PGResultCurrent...")
    target_reg_nos = list(PGResultCurrent.objects.values_list('college_reg_no', flat=True).distinct())
    target_set = set(r for r in target_reg_nos if r and str(r).strip())
    print(f"   Found {len(target_set):,} unique student registration numbers.\n")
    
    if not target_set:
        print("⚠️  No students found in PGResultCurrent. Aborting.")
        return

    # 🔗 Fetch Staging Data Dictionary
    print("📊 Loading Staging Data (PGResultCurrent)...")
    staging_data = {}
    qs_staging = PGResultCurrent.objects.filter(college_reg_no__in=target_set).values(
        'college_reg_no', 'student_name', 'fathers_name', 'mothers_name',
        'session_code', 'batch_code', 'student_name_hindi',
        'course_code', 'college_roll_no', 'semester_code'
    )
    for item in qs_staging:
        r = str(item['college_reg_no']).strip()
        if r:
            staging_data[r] = item
    print(f"   Loaded {len(staging_data):,} records from Staging.")

    # 2. Ensure UserAccounts Exist
    print("\n📊 Checking UserAccounts...")
    existing_users = UserAccount.objects.filter(username__in=target_set).values_list('username', flat=True)
    existing_users_set = set(existing_users)
    
    missing_users = target_set - existing_users_set
    
    if missing_users:
        print(f"   Creating {len(missing_users):,} missing UserAccounts...")
        new_users = []
        
        for reg_no in missing_users:
            stg = staging_data.get(reg_no, {})
            raw_cc = stg.get('course_code', '').strip()
            
            # User Mapping Logic: Map course_code to current_profile
            if raw_cc.upper() == 'PG':
                curr_profile = 'pg'
            elif raw_cc.upper() == 'MCA':
                curr_profile = 'mca_sem'
            else:
                 curr_profile = raw_cc[:20]

            # Password = Registration Number
            user_password = make_password(reg_no)

            new_users.append(UserAccount(
                username=reg_no,
                password=user_password,
                user_type='student',
                current_profile=curr_profile, 
                is_active=True
            ))
            
        # Bulk create users in chunks
        batch_size = 2000
        for i in range(0, len(new_users), batch_size):
            UserAccount.objects.bulk_create(new_users[i:i+batch_size])
            print(f"     Created {min(i+batch_size, len(new_users))}/{len(new_users)} users...")

    # 3. Ensure PGStudentProfiles Exist
    print("\n📊 Checking PGStudentProfiles...")
    existing_profiles = PGStudentProfile.objects.filter(registration_no__in=target_set).values_list('registration_no', flat=True)
    existing_profiles_set = set(existing_profiles)
    
    missing_profiles = target_set - existing_profiles_set
    
    if missing_profiles:
        print(f"   Creating {len(missing_profiles):,} missing PGStudentProfiles...")
        
        users_map = {u.username: u for u in UserAccount.objects.filter(username__in=missing_profiles)}
        
        new_profiles = []
        for reg_no in missing_profiles:
            user = users_map.get(reg_no)
            if user:
                new_profiles.append(PGStudentProfile(
                    user=user,
                    registration_no=reg_no,
                    status='Active'
                ))
        
        batch_size = 2000
        for i in range(0, len(new_profiles), batch_size):
            PGStudentProfile.objects.bulk_create(new_profiles[i:i+batch_size])
            print(f"     Created {min(i+batch_size, len(new_profiles))}/{len(new_profiles)} profiles...")

    # 4. Load Applicant Data (Secondary)
    print("\n📊 Loading applicant data (Secondary)...")
    applicants = {a.college_reg_no: a for a in RegisteredApplicantMaster.objects.filter(
        college_reg_no__in=target_set
    )}
    print(f"   Loaded {len(applicants):,} records from Applicants.")

    # 5. Prepare Profile Updates
    print("\n📊 Calculating profile updates...")
    profiles_to_process = PGStudentProfile.objects.filter(registration_no__in=target_set)
    updates = []
    
    # Fields to update
    fields_to_update = [
        'first_name', 'father_name', 'mother_name', 'date_of_birth',
        'gender', 'caste', 'address', 'mobile_no', 'session', 'batch', 'hindi_name',
        'roll_no', 'current_semester', 'aadhar_no'
    ]
    
    for profile in profiles_to_process:
        reg = profile.registration_no
        staging = staging_data.get(reg)
        applicant = applicants.get(reg)
        
        if not staging and not applicant:
            continue
            
        # Defaults
        new_fname = profile.first_name
        new_father = profile.father_name
        new_mother = profile.mother_name
        new_session = profile.session
        new_batch = profile.batch
        new_hindi = profile.hindi_name
        new_dob = profile.date_of_birth
        new_gender = profile.gender
        new_caste = profile.caste
        new_addr = profile.address
        new_mobile = profile.mobile_no
        new_roll = profile.roll_no
        new_sem = profile.current_semester
        new_aadhar = profile.aadhar_no

        if staging:
            new_fname = (staging.get('student_name') or '').strip()
            new_father = (staging.get('fathers_name') or '').strip()
            new_mother = (staging.get('mothers_name') or '').strip()
            new_session = staging.get('session_code')
            val_batch = staging.get('batch_code')
            if val_batch: new_batch = val_batch.strip()
            val_hindi = staging.get('student_name_hindi')
            if val_hindi: new_hindi = val_hindi.strip()
            new_roll = staging.get('college_roll_no')
            new_sem = parse_semester(staging.get('semester_code'))

        if applicant:
            if not staging:
                new_fname = (applicant.student_name or '').strip()
                new_father = (applicant.fathers_name or '').strip()
                new_mother = (applicant.mothers_name or '').strip()
                new_session = applicant.session_code
                new_batch = applicant.batch_code
            
            parsed_dob = parse_date(applicant.dob)
            if parsed_dob: new_dob = parsed_dob
            if applicant.gender: new_gender = applicant.gender
            if applicant.category: new_caste = applicant.category
            if applicant.full_address: new_addr = applicant.full_address
            if applicant.phone: new_mobile = applicant.phone
            
            val_aadhar = applicant.aadhar_card_no
            if val_aadhar:
                val_aadhar = str(val_aadhar).strip()
                if len(val_aadhar) <= 12:
                    new_aadhar = val_aadhar
                else:
                    new_aadhar = ""

        # Detect Changes
        changed = False
        if profile.first_name != new_fname: profile.first_name = new_fname; changed = True
        if profile.father_name != new_father: profile.father_name = new_father; changed = True
        if profile.mother_name != new_mother: profile.mother_name = new_mother; changed = True
        if profile.date_of_birth != new_dob: profile.date_of_birth = new_dob; changed = True
        if profile.gender != new_gender: profile.gender = new_gender; changed = True
        if profile.caste != new_caste: profile.caste = new_caste; changed = True
        if profile.address != new_addr: profile.address = new_addr; changed = True
        if profile.mobile_no != new_mobile: profile.mobile_no = new_mobile; changed = True
        if profile.session != new_session: profile.session = new_session; changed = True
        if profile.batch != new_batch: profile.batch = new_batch; changed = True
        if profile.hindi_name != new_hindi: profile.hindi_name = new_hindi; changed = True
        if profile.roll_no != new_roll: profile.roll_no = new_roll; changed = True
        if profile.current_semester != new_sem: profile.current_semester = new_sem; changed = True
        if profile.aadhar_no != new_aadhar: profile.aadhar_no = new_aadhar; changed = True
        
        if changed:
            updates.append(profile)
            
    if updates:
        print(f"\n   Committing {len(updates):,} profile updates...")
        batch_size = 1000
        for i in range(0, len(updates), batch_size):
            PGStudentProfile.objects.bulk_update(updates[i:i+batch_size], fields_to_update)
            print(f"     Updated {min(i+batch_size, len(updates))}/{len(updates)}")

    # 6. Update User Passwords (Chunked)
    print("\n📊 Updating User Passwords and Profile Types...")
    print("   ⚠️  IMPORTANT: Setting password = username for ALL users. Writing in chunks...")
    
    all_users = UserAccount.objects.filter(username__in=target_set)
    total_users = all_users.count()
    
    users_batch = []
    processed_count = 0
    t0 = time.time()
    
    for user in all_users:
        processed_count += 1
        
        # 1. Update Profile Type (if needed)
        stg = staging_data.get(user.username)
        if stg:
            raw_cc = stg.get('course_code', '').strip()
            if raw_cc.upper() == 'PG': new_cp = 'pg'
            elif raw_cc.upper() == 'MCA': new_cp = 'mca_sem'
            else: new_cp = raw_cc[:20]
            
            if user.current_profile != new_cp:
                user.current_profile = new_cp
        
        # 2. Update Password (Always)
        user.password = make_password(user.username)
        users_batch.append(user)
        
        # Commit every 1000 users
        if len(users_batch) >= 1000:
            UserAccount.objects.bulk_update(users_batch, ['password', 'current_profile'])
            elapsed = time.time() - t0
            rate = processed_count / elapsed
            print(f"   Committed batch of 1000 users. Total: {processed_count}/{total_users} (Rate: {rate:.1f}/s)")
            users_batch = []
            
    # Final batch
    if users_batch:
        UserAccount.objects.bulk_update(users_batch, ['password', 'current_profile'])
        print(f"   Committed final batch of {len(users_batch)} users. Total: {processed_count}/{total_users}")
    
    total_elapsed = time.time() - start
    print(f"\n✅ DONE. Total Time: {total_elapsed:.1f}s.")

if __name__ == '__main__':
    migrate()
