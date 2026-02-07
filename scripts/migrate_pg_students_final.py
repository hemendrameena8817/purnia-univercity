import os
import sys
import django
import time
import re
from datetime import datetime

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.hashers import make_password
from pg.models import PGStudentProfile, PGDepartment, PGProgram, PGDegree
from accounts.models import UserAccount
from staging.models import PGResultCurrent, RegisteredApplicantMaster

def parse_semester(sem_str):
    if not sem_str: return None
    try:
        match = re.search(r'\d+', str(sem_str))
        if match: return int(match.group())
    except: pass
    return None

def parse_date(date_str):
    if not date_str: return None
    formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
    for fmt in formats:
        try: return datetime.strptime(str(date_str).strip(), fmt).date()
        except: continue
    return None

def migrate():
    print("\n" + "="*80)
    print("PG STUDENT IMPORT & UPDATE (Constant Password '123')")
    print("="*80)
    
    start = time.time()
    
    # 1. Identify Target Students
    print("📊 Fetching target students...")
    target_reg_nos = list(PGResultCurrent.objects.values_list('college_reg_no', flat=True).distinct())
    target_set = set(r for r in target_reg_nos if r and str(r).strip())
    print(f"   Found {len(target_set):,} unique students.")
    
    if not target_set: return

    # 🔗 Load Staging Data
    print("📊 Loading Staging Data...")
    staging_data = {}
    qs_staging = PGResultCurrent.objects.filter(college_reg_no__in=target_set).values(
        'college_reg_no', 'course_code', 'discipline_code', 
        'college_roll_no', 'semester_code', 'session_code', 'batch_code',
        'student_name', 'fathers_name', 'mothers_name', 'student_name_hindi'
    )
    for item in qs_staging:
        r = str(item['college_reg_no']).strip()
        if r: staging_data[r] = item

    # 🏫 Cache Academic Structure
    print("📊 Caching Academic Structure...")
    dept_map = {d.code: d for d in PGDepartment.objects.all() if d.code}
    prog_map = {}
    for prog in PGProgram.objects.select_related('degree').all():
        if prog.department_id and prog.department_id not in prog_map:
            prog_map[prog.department_id] = prog
            
    # 2. Existing User/Profile Checks
    print("\n📊 Checking Accounts (Fast)...")
    existing_users = set(UserAccount.objects.filter(username__in=target_set).values_list('username', flat=True))
    missing_users = target_set - existing_users
    
    # Pre-calculate Hash for '123'
    # This is the key optimization requested
    DEFAULT_PASS_HASH = make_password('123')
    print(f"   ℹ️  Using default password '123' for all users.")

    if missing_users:
        print(f"   Creating {len(missing_users):,} missing users...")
        new_users = [
            UserAccount(username=r, password=DEFAULT_PASS_HASH, user_type='student', is_active=True)
            for r in missing_users
        ]
        UserAccount.objects.bulk_create(new_users, batch_size=2000)

    # Missing Profiles
    existing_profiles = set(PGStudentProfile.objects.filter(registration_no__in=target_set).values_list('registration_no', flat=True))
    missing_profiles = target_set - existing_profiles
    if missing_profiles:
        print(f"   Creating {len(missing_profiles):,} missing profiles...")
        u_map = {u.username: u for u in UserAccount.objects.filter(username__in=missing_profiles)}
        new_profiles = []
        for r in missing_profiles:
            if r in u_map:
                new_profiles.append(PGStudentProfile(user=u_map[r], registration_no=r, status='Active'))
        PGStudentProfile.objects.bulk_create(new_profiles, batch_size=2000)

    # 3. Update Profiles (Fields + Academics)
    print("\n📊 Calculating updates...")
    applicants = {a.college_reg_no: a for a in RegisteredApplicantMaster.objects.filter(college_reg_no__in=target_set)}
    
    profiles_to_process = PGStudentProfile.objects.filter(registration_no__in=target_set)
    updates = []
    # Fields logic same as before...
    
    for profile in profiles_to_process:
        reg = profile.registration_no
        stg = staging_data.get(reg)
        app = applicants.get(reg)
        
        if not stg and not app: continue
        
        # ... (Abbreviated update logic for brevity, but logically identical to before)
        # Defaults
        new_fname = profile.first_name; new_father = profile.father_name; new_mother = profile.mother_name
        new_session = profile.session; new_batch = profile.batch; new_hindi = profile.hindi_name
        new_dob = profile.date_of_birth; new_gender = profile.gender; new_caste = profile.caste
        new_addr = profile.address; new_mobile = profile.mobile_no; new_roll = profile.roll_no
        new_sem = profile.current_semester; new_aadhar = profile.aadhar_no
        new_dept = profile.department; new_prog = profile.program; new_degree = profile.degree

        if stg:
            new_fname = (stg.get('student_name') or '').strip()
            new_father = (stg.get('fathers_name') or '').strip()
            new_mother = (stg.get('mothers_name') or '').strip()
            new_session = stg.get('session_code')
            if stg.get('batch_code'): new_batch = stg.get('batch_code').strip()
            if stg.get('student_name_hindi'): new_hindi = stg.get('student_name_hindi').strip()
            new_roll = stg.get('college_roll_no')
            new_sem = parse_semester(stg.get('semester_code'))
            disc = stg.get('discipline_code')
            if disc and disc.strip() in dept_map:
                new_dept = dept_map[disc.strip()]
                if new_dept.id in prog_map:
                    new_prog = prog_map[new_dept.id]
                    if new_prog.degree: new_degree = new_prog.degree

        if app:
            if not stg:
                new_fname = (app.student_name or '').strip()
                new_father = (app.fathers_name or '').strip()
                new_mother = (app.mothers_name or '').strip()
                new_session = app.session_code
                new_batch = app.batch_code
            pdob = parse_date(app.dob)
            if pdob: new_dob = pdob
            if app.gender: new_gender = app.gender
            if app.category: new_caste = app.category
            if app.full_address: new_addr = app.full_address
            if app.phone: new_mobile = app.phone
            if app.aadhar_card_no and len(str(app.aadhar_card_no).strip()) <= 12: new_aadhar = str(app.aadhar_card_no).strip()

        # Check for changes
        c = False
        if profile.first_name != new_fname: profile.first_name = new_fname; c = True
        if profile.father_name != new_father: profile.father_name = new_father; c = True
        if profile.mother_name != new_mother: profile.mother_name = new_mother; c = True
        if profile.date_of_birth != new_dob: profile.date_of_birth = new_dob; c = True
        if profile.gender != new_gender: profile.gender = new_gender; c = True
        if profile.caste != new_caste: profile.caste = new_caste; c = True
        if profile.address != new_addr: profile.address = new_addr; c = True
        if profile.mobile_no != new_mobile: profile.mobile_no = new_mobile; c = True
        if profile.session != new_session: profile.session = new_session; c = True
        if profile.batch != new_batch: profile.batch = new_batch; c = True
        if profile.hindi_name != new_hindi: profile.hindi_name = new_hindi; c = True
        if profile.roll_no != new_roll: profile.roll_no = new_roll; c = True
        if profile.current_semester != new_sem: profile.current_semester = new_sem; c = True
        if profile.aadhar_no != new_aadhar: profile.aadhar_no = new_aadhar; c = True
        if profile.department_id != (new_dept.id if new_dept else None): profile.department = new_dept; c = True
        if profile.program_id != (new_prog.id if new_prog else None): profile.program = new_prog; c = True
        if profile.degree_id != (new_degree.id if new_degree else None): profile.degree = new_degree; c = True
        
        if c: updates.append(profile)

    if updates:
        print(f"   Committing {len(updates):,} profile updates...")
        fields = [
            'first_name', 'father_name', 'mother_name', 'date_of_birth',
            'gender', 'caste', 'address', 'mobile_no', 'session', 'batch', 'hindi_name',
            'roll_no', 'current_semester', 'aadhar_no',
            'department', 'program', 'degree'
        ]
        PGStudentProfile.objects.bulk_update(updates, fields, batch_size=2000)

    # 4. Update Passwords (Constant)
    print("\n🚀 Setting Passwords to '123' (Instant)...")
    all_users = UserAccount.objects.filter(username__in=target_set)
    
    users_to_update = []
    
    # We update ALL users to ensure they are consistent
    for user in all_users:
        # Update Profile Type logic
        stg = staging_data.get(user.username)
        if stg:
            raw_cc = stg.get('course_code', '').strip()
            if raw_cc.upper() == 'PG': new_cp = 'pg'
            elif raw_cc.upper() == 'MCA': new_cp = 'mca_sem'
            else: new_cp = raw_cc[:20]
            if user.current_profile != new_cp:
                user.current_profile = new_cp
        
        # Set Password
        user.password = DEFAULT_PASS_HASH
        users_to_update.append(user)
    
    print(f"   Bulk updating {len(users_to_update):,} users...")
    UserAccount.objects.bulk_update(users_to_update, ['password', 'current_profile'], batch_size=2000)

    total_time = time.time() - start
    print(f"\n✅ DONE. Total Time: {total_time:.1f}s")

if __name__ == '__main__':
    migrate()
