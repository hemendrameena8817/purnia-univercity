import os
import sys
import django
from datetime import date

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from university.models import University
from colleges.models import College
from students.models import Student
from accounts.models import CollegeUserProfile

User = get_user_model()
PASSWORD = "Test@123"

def create_university():
    uni, created = University.objects.get_or_create(
        short_name="PU",
        defaults={
            "name": "Purnea University",
            "address": "Purnea, Bihar",
            "vice_chancellor": "Dr. VC Name",
            "email": "vc@purneauniversity.ac.in",
            "established_date": date(2018, 3, 18),
            "website": "https://purneauniversity.ac.in"
        }
    )
    if created:
        print(f"Created University: {uni.name}")
    return uni

def create_college(uni):
    college, created = College.objects.get_or_create(
        college_code="PC001",
        defaults={
            "name": "Purnea College",
            "short_name": "PC",
            "address": "Purnea",
            "university": uni,
            "principal": "Dr. Principal",
            "email": "principal@purneacollege.in"
        }
    )
    if created:
        print(f"Created College: {college.name}")
    return college

def create_user(username, email, user_type, first_name, last_name, is_staff=False, is_superuser=False):
    if User.objects.filter(username=username).exists():
        print(f"User {username} already exists")
        return User.objects.get(username=username)
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
        user_type=user_type,
        first_name=first_name,
        last_name=last_name,
        is_staff=is_staff,
        is_superuser=is_superuser,
        is_active=True,
        is_verified=True
    )
    print(f"Created User: {username} ({user_type})")
    return user

def main():
    print("Seeding test users...")
    uni = create_university()
    college = create_college(uni)

    # 1. University Admins
    print("\n--- University Admins ---")
    create_user("uni_admin_1", "admin1@pu.ac.in", "university_admin", "Uni", "Admin1", is_staff=True, is_superuser=True)
    create_user("uni_admin_2", "admin2@pu.ac.in", "university_admin", "Uni", "Admin2", is_staff=True, is_superuser=False)

    # 2. College Users
    print("\n--- College Users ---")
    # Principal
    c_user1 = create_user("college_principal", "principal@pc.in", "college_user", "College", "Principal")
    CollegeUserProfile.objects.get_or_create(
        user=c_user1,
        college=college,
        defaults={"designation": "Principal Dr."}
    )
    
    # Clerk
    c_user2 = create_user("college_clerk", "clerk@pc.in", "college_user", "College", "Clerk")
    CollegeUserProfile.objects.get_or_create(
        user=c_user2,
        college=college,
        defaults={"designation": "Office Clerk"}
    )

    # 3. Students
    print("\n--- Students ---")
    # Student 1
    s_user1 = create_user("student_001", "student1@gmail.com", "student", "Student", "One")
    if not hasattr(s_user1, 'student_profile'):
        Student.objects.create(
            user=s_user1,
            registration_no="REG2024001",
            roll_no="ROLL001",
            college=college,
            first_name="Student",
            last_name="One",
            father_name="Father One",
            mother_name="Mother One",
            current_semester=1,
            session="2024-2027",
            status="Active",
            gender="Male",
            date_of_birth=date(2000, 1, 1),
            admission_date=date(2024, 6, 1),
            enrollment_date=date(2024, 6, 1),
            address="Address 1",
            batch="2024"
        )
        print(f"Created Profile for {s_user1.username}")

    # Student 2
    s_user2 = create_user("student_002", "student2@gmail.com", "student", "Student", "Two")
    if not hasattr(s_user2, 'student_profile'):
        Student.objects.create(
            user=s_user2,
            registration_no="REG2024002",
            roll_no="ROLL002",
            college=college,
            first_name="Student",
            last_name="Two",
            father_name="Father Two",
            mother_name="Mother Two",
            current_semester=1,
            session="2024-2027",
            status="Active",
            gender="Female",
            date_of_birth=date(2001, 2, 2),
            admission_date=date(2024, 6, 1),
            enrollment_date=date(2024, 6, 1),
            address="Address 2",
            batch="2024"
        )
        print(f"Created Profile for {s_user2.username}")

    print("\n-------------------------------------------")
    print(f"Seeding Complete! Password for all users: {PASSWORD}")
    print("-------------------------------------------")

if __name__ == "__main__":
    main()
