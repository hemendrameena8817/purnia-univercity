"""
ULTRA-FAST UG Student Migration Script

Performance optimizations:
- Uses bulk_create for 100x faster inserts
- Pre-computed password hash (avoids CPU bottleneck)
- Processes in batches of 500
- Minimal database queries
- Real-time progress updates

Safe features:
- Does NOT delete existing data
- Checks for duplicates
- Only creates missing students
- Can run multiple times
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.hashers import make_password
from staging.models import UGSemResultCurrent, RegisteredApplicantMaster
from accounts.models import UserAccount
from ug.models import UGStudentProfile, UGDepartment, UGDegree, UGProgram, UGFaculty
from colleges.models import College
from university.models import University
from datetime import datetime
import time


# Pre-compute a default password hash (for "password123")
# This avoids hashing 58K+ passwords individually
DEFAULT_PASSWORD_HASH = make_password("password123")


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


def get_lookups():
    """Pre-load all lookup data."""
    university = University.objects.first()
    default_faculty = None
    
    if university:
        default_faculty, _ = UGFaculty.objects.get_or_create(
            name='Default Faculty',
            defaults={'university_id': university.uid, 'short_name': 'DEFAULT'}
        )
    
    return {
        'university': university,
        'default_faculty': default_faculty,
        'departments': {d.code: d for d in UGDepartment.objects.all()},
        'degrees': {d.short_name: d for d in UGDegree.objects.all()},
        'programs': {(p.degree_id, p.department_id if p.department_id else None): p 
                     for p in UGProgram.objects.select_related('degree', 'department').all()},
        'colleges': {c.college_code: c for c in College.objects.all()}
    }


def get_or_create_dept(code, lookups):
    """Get or create department."""
    if not code or code in lookups['departments']:
        return lookups['departments'].get(code)
    
    if not lookups['default_faculty']:
        return None
    
    dept = UGDepartment.objects.create(
        name=f"Dept {code}",
        code=code,
        faculty=lookups['default_faculty']
    )
    lookups['departments'][code] = dept
    return dept


def get_or_create_deg(code, lookups):
    """Get or create degree."""
    if not code or code in lookups['degrees']:
        return lookups['degrees'].get(code)
    
    deg = UGDegree.objects.create(
        name=f"Degree {code}",
        short_name=code,
        total_semesters=8,
        total_years=4
    )
    lookups['degrees'][code] = deg
    return deg


def get_or_create_prog(degree, department, lookups):
    """Get or create program."""
    if not degree:
        return None
    
    key = (degree.uid, department.uid if department else None)
    if key in lookups['programs']:
        return lookups['programs'][key]
    
    prog = UGProgram.objects.create(
        name=f"{degree.short_name}" + (f" - {department.name}" if department else ""),
        short_name=degree.short_name,
        degree=degree,
        department=department
    )
    lookups['programs'][key] = prog
    return prog


def migrate():
    """Ultra-fast bulk migration."""
    print("\n" + "="*80)
    print("ULTRA-FAST UG STUDENT MIGRATION")
    print("="*80)
    print("Performance: Pre-hashed passwords + bulk inserts")
    print("="*80 + "\n")
    
    start = time.time()
    
    # Get unique reg numbers
    print("📊 Getting unique registration numbers...")
    all_reg_nos = set(UGSemResultCurrent.objects.filter(
        college_reg_no__isnull=False
    ).exclude(college_reg_no='').values_list('college_reg_no', flat=True).distinct())
    print(f"   Total: {len(all_reg_nos):,}\n")
    
    # Check existing
    print("📊 Checking existing students...")
    existing = set(UserAccount.objects.filter(
        username__in=all_reg_nos
    ).values_list('username', flat=True)) | set(UGStudentProfile.objects.filter(
        registration_no__in=all_reg_nos
    ).values_list('registration_no', flat=True))
    
    missing = all_reg_nos - existing
    print(f"   Existing: {len(existing):,}")
    print(f"   Missing:  {len(missing):,}\n")
    
    if not missing:
        print("✅ All students migrated!")
        return
    
    # Load applicant data
    print("📊 Loading applicant data...")
    applicants = {a.college_reg_no: a for a in RegisteredApplicantMaster.objects.filter(
        college_reg_no__in=missing
    )}
    print(f"   Loaded: {len(applicants):,}\n")
    
    # Load lookups
    print("📊 Loading lookups...")
    lookups = get_lookups()
    print("   ✅ Done\n")
    
    # Bulk create in batches
    print("📊 Creating students (batch size: 500)...")
    print("   Progress: ", end='', flush=True)
    
    batch_size = 500
    users_batch = []
    profiles_batch = []
    created_users = 0
    created_profiles = 0
    skipped_aadhar = 0
    
    missing_list = list(missing)
    for idx, reg_no in enumerate(missing_list, 1):
        if reg_no not in applicants:
            continue
        
        try:
            app = applicants[reg_no]
            name = (app.student_name or '').strip()
            
            # Create user with pre-hashed password
            users_batch.append(UserAccount(
                username=reg_no,
                first_name=name[:100],
                last_name='',
                email=None,
                phone=app.phone or None,
                user_type='student',
                is_active=True,
                is_verified=False,
                password=DEFAULT_PASSWORD_HASH  # Pre-computed!
            ))
            
        except Exception as e:
            print(f"\n   Error {reg_no}: {e}")
        
        # Insert batch
        if len(users_batch) >= batch_size or idx == len(missing_list):
            with transaction.atomic():
                # Bulk insert users
                UserAccount.objects.bulk_create(users_batch, ignore_conflicts=True)
                created_users += len(users_batch)
                
                # Get created users with their UIDs
                usernames = [u.username for u in users_batch]
                user_map = {u.username: u for u in UserAccount.objects.filter(
                    username__in=usernames
                )}
                
                # Build profiles
                profiles_batch = []
                for user_obj in users_batch:
                    reg = user_obj.username
                    if reg not in applicants or reg not in user_map:
                        continue
                    
                    app = applicants[reg]
                    dept = get_or_create_dept(app.discipline_code, lookups)
                    deg = get_or_create_deg(app.course_code, lookups)
                    prog = get_or_create_prog(deg, dept, lookups)
                    
                    aadhar = app.aadhar_card_no
                    if aadhar and len(str(aadhar)) > 12:
                        aadhar = None
                        skipped_aadhar += 1
                    
                    profiles_batch.append(UGStudentProfile(
                        user=user_map[reg],
                        first_name=(app.student_name or '').strip(),
                        last_name='',
                        registration_no=reg,
                        roll_no=app.roll_no or reg,
                        father_name=(app.fathers_name or '')[:255],
                        mother_name=(app.mothers_name or '')[:255],
                        date_of_birth=parse_date(app.dob),
                        gender=app.gender,
                        caste=app.category,
                        address=app.full_address,
                        aadhar_no=aadhar,
                        mobile_no=app.phone,
                        college=lookups['colleges'].get(app.institute_code),
                        department=dept,
                        degree=deg,
                        program=prog,
                        status='Active',
                        session=app.session_code,
                        batch=app.batch_code
                    ))
                
                # Bulk insert profiles
                UGStudentProfile.objects.bulk_create(profiles_batch, ignore_conflicts=True)
                created_profiles += len(profiles_batch)
            
            users_batch = []
            print(f"{idx:,}/{len(missing_list):,}... ", end='', flush=True)
    
    elapsed = time.time() - start
    
    # Summary
    print(f"\n\n" + "="*80)
    print("MIGRATION COMPLETE")
    print("="*80)
    print(f"⏱️  Time:             {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"📊 To migrate:       {len(missing_list):,}")
    print(f"✅ Users created:    {created_users:,}")
    print(f"✅ Profiles created: {created_profiles:,}")
    print(f"⚠️  Aadhar skipped:   {skipped_aadhar}")
    print("="*80)
    
    # Final state
    final_users = UserAccount.objects.filter(user_type='student').count()
    final_profiles = UGStudentProfile.objects.count()
    print(f"\n📊 FINAL STATE:")
    print(f"   Users:    {final_users:,}")
    print(f"   Profiles: {final_profiles:,}")
    print(f"   Expected: {len(all_reg_nos):,}")
    print(f"   Success:  {(final_profiles/len(all_reg_nos)*100):.1f}%")
    print("\n⚠️  NOTE: All passwords set to 'password123'")
    print("   You can update individual passwords later if needed.")
    print("="*80 + "\n")


if __name__ == '__main__':
    migrate()
