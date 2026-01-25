"""
Script to migrate UG students by matching UGSemResultCurrent with RegisteredApplicantMaster.

Flow:
1. Get unique college_reg_no from UGSemResultCurrent
2. Match with RegisteredApplicantMaster to get full student info
3. Create UserAccount and UGStudentProfile from applicant data
4. Track missing students (not found in RegisteredApplicantMaster)

Mappings:
- discipline_code → UGDepartment (department)
- course_code → UGDegree (degree)
- college_reg_no → registration_no (unique identifier)
"""

import os
import sys
import django
from collections import defaultdict

# Setup Django environment
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


def get_or_create_department(discipline_code, discipline_name=None):
    """
    Get or create UGDepartment from discipline_code.
    """
    if not discipline_code:
        return None
    
    # Try to find existing department by code
    department = UGDepartment.objects.filter(code=discipline_code).first()
    
    if department:
        return department
    
    # Create new department with a default faculty
    # First check if a university exists
    university = University.objects.first()
    if not university:
        print("  ⚠️  No university found, skipping department creation")
        return None
    
    default_faculty, _ = UGFaculty.objects.get_or_create(
        name='Default Faculty',
        defaults={
            'university_id': university.uid,
            'short_name': 'DEFAULT'
        }
    )
    
    department_name = discipline_name or f"Department {discipline_code}"
    department = UGDepartment.objects.create(
        name=department_name,
        code=discipline_code,
        faculty=default_faculty
    )
    
    print(f"  ✓ Created department: {department_name} ({discipline_code})")
    return department


def get_or_create_degree(course_code):
    """
    Get or create UGDegree from course_code.
    """
    if not course_code:
        return None
    
    # Try to find existing degree
    degree = UGDegree.objects.filter(short_name=course_code).first()
    
    if degree:
        return degree
    
    # Create new degree
    degree_name = f"Degree {course_code}"
    degree = UGDegree.objects.create(
        name=degree_name,
        short_name=course_code,
        total_semesters=8,
        total_years=4
    )
    
    print(f"  ✓ Created degree: {degree_name} ({course_code})")
    return degree


def get_or_create_program(degree, department):
    """
    Get or create UGProgram from degree and department.
    """
    if not degree:
        return None
    
    # Try to find existing program
    if department:
        program = UGProgram.objects.filter(degree=degree, department=department).first()
    else:
        program = UGProgram.objects.filter(degree=degree, department__isnull=True).first()
    
    if program:
        return program
    
    # Create new program
    program_name = f"{degree.short_name}"
    if department:
        program_name += f" - {department.name}"
    
    program = UGProgram.objects.create(
        name=program_name,
        short_name=degree.short_name,
        degree=degree,
        department=department
    )
    
    print(f"  ✓ Created program: {program_name}")
    return program


def get_college(institute_code):
    """
    Get college by institute code.
    """
    if not institute_code:
        return None
    
    return College.objects.filter(college_code=institute_code).first()


def parse_date(date_str):
    """
    Parse date string in various formats.
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    
    from datetime import datetime
    
    # Try different date formats
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d.%m.%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except:
            continue
    
    return None


def migrate_students():
    """
    Main migration function:
    1. Get unique college_reg_no from UGSemResultCurrent
    2. Match with RegisteredApplicantMaster
    3. Create users and profiles
    4. Track missing students
    """
    print("\n" + "="*80)
    print("Starting UG Student Migration")
    print("="*80 + "\n")
    
    # Step 1: Get unique college_reg_no from UGSemResultCurrent
    print("📊 Step 1: Getting unique college_reg_no from UGSemResultCurrent...")
    
    unique_reg_nos = UGSemResultCurrent.objects.filter(
        college_reg_no__isnull=False
    ).values_list('college_reg_no', flat=True).distinct()
    
    unique_reg_nos = set(unique_reg_nos)
    unique_reg_nos.discard('')  # Remove empty strings
    unique_reg_nos.discard(None)  # Remove None values
    
    print(f"   Found {len(unique_reg_nos)} unique college_reg_no values\n")
    
    # Step 2: Match with RegisteredApplicantMaster
    print("📊 Step 2: Matching with RegisteredApplicantMaster...")
    
    # Build a lookup dictionary for faster access
    applicant_lookup = {}
    for applicant in RegisteredApplicantMaster.objects.filter(college_reg_no__in=unique_reg_nos):
        applicant_lookup[applicant.college_reg_no] = applicant
    
    print(f"   Found {len(applicant_lookup)} matches in RegisteredApplicantMaster")
    
    # Track missing students
    missing_students = []
    for reg_no in unique_reg_nos:
        if reg_no not in applicant_lookup:
            missing_students.append(reg_no)
    
    print(f"   ⚠️  Missing {len(missing_students)} students in RegisteredApplicantMaster\n")
    
    # Statistics
    created_users = 0
    created_profiles = 0
    skipped_duplicates = 0
    errors = []
    
    # Step 3: Create users and profiles
    print("📊 Step 3: Creating users and profiles...\n")
    
    for reg_no, applicant in applicant_lookup.items():
        try:
            # Check if profile already exists
            existing_profile = UGStudentProfile.objects.filter(
                registration_no=reg_no
            ).first()
            
            if existing_profile:
                print(f"⏭️  Skipped: {applicant.student_name} ({reg_no}) - already exists")
                skipped_duplicates += 1
                continue
            
            with transaction.atomic():
                # Username is college_reg_no (no modifications)
                username = reg_no
                
                # Ensure username is unique
                if UserAccount.objects.filter(username=username).exists():
                    base_username = username
                    counter = 1
                    while UserAccount.objects.filter(username=username).exists():
                        username = f"{base_username}_{counter}"
                        counter += 1
                
                # Full student name goes into first_name, last_name is blank
                full_name = (applicant.student_name or '').strip()
                
                # Determine password: DOB in MM-DD-YY format, or first name if no DOB
                password = full_name  # Default to full name
                dob = parse_date(applicant.dob)
                if dob:
                    # Format as MM-DD-YY
                    password = dob.strftime('%m-%d-%y')
                
                # Create UserAccount
                user = UserAccount.objects.create(
                    username=username,
                    first_name=full_name[:100],  # Full name in first_name field
                    last_name='',  # Leave last_name blank
                    email=None,  # No email in applicant data
                    phone=applicant.phone or None,
                    user_type='student',
                    is_active=True,
                    is_verified=False,
                    password=make_password(password)
                )
                created_users += 1
                
                # Get or create related objects
                department = None
                if applicant.discipline_code:
                    department = get_or_create_department(applicant.discipline_code)
                
                degree = None
                if applicant.course_code:
                    degree = get_or_create_degree(applicant.course_code)
                
                program = None
                if degree:
                    program = get_or_create_program(degree, department)
                
                college = get_college(applicant.institute_code)
                
                # Create UGStudentProfile
                profile = UGStudentProfile.objects.create(
                    user=user,
                    first_name=full_name,  # Full name
                    last_name='',  # Blank last name
                    registration_no=reg_no,
                    roll_no=applicant.roll_no or reg_no,
                    father_name=applicant.fathers_name or '',
                    mother_name=applicant.mothers_name or '',
                    date_of_birth=dob,
                    gender=applicant.gender,
                    caste=applicant.category,
                    address=applicant.full_address,
                    aadhar_no=applicant.aadhar_card_no,
                    mobile_no=applicant.phone,
                    college=college,
                    department=department,
                    degree=degree,
                    program=program,
                    status='Active',
                    session=applicant.session_code,
                    batch=applicant.batch_code,
                )
                created_profiles += 1
                
                print(f"✅ Created: {full_name} ({reg_no}) -> {username}")
                
        except Exception as e:
            error_msg = f"{reg_no}: {str(e)}"
            errors.append(error_msg)
            print(f"❌ Error: {error_msg}")
            continue
    
    # Step 4: Save missing students list to file
    if missing_students:
        print("\n📝 Saving missing students list to file...")
        output_file = 'missing_students_report.txt'
        with open(output_file, 'w') as f:
            f.write("Missing Students Report\n")
            f.write("="*80 + "\n")
            f.write(f"Total missing: {len(missing_students)}\n")
            f.write("="*80 + "\n\n")
            f.write("college_reg_no values not found in RegisteredApplicantMaster:\n\n")
            for reg_no in sorted(missing_students):
                f.write(f"{reg_no}\n")
        print(f"   ✅ Saved to {output_file}\n")
    
    # Print summary
    print("\n" + "="*80)
    print("Migration Summary")
    print("="*80)
    print(f"📊 Total unique reg numbers:    {len(unique_reg_nos)}")
    print(f"✅ Found in applicant master:   {len(applicant_lookup)}")
    print(f"⚠️  Missing in applicant master: {len(missing_students)}")
    print(f"")
    print(f"✅ Users created:               {created_users}")
    print(f"✅ Profiles created:            {created_profiles}")
    print(f"⏭️  Skipped (duplicates):        {skipped_duplicates}")
    print(f"❌ Errors:                      {len(errors)}")
    print("="*80)
    
    if missing_students:
        print(f"\n📄 Missing students list saved to: missing_students_report.txt")
    
    if errors:
        print(f"\n⚠️  First 10 errors:")
        for error in errors[:10]:
            print(f"   - {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")
    
    print()


if __name__ == '__main__':
    migrate_students()
