import uuid
import random
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import UserAccount
from colleges.models import College
from mba_sem.models import MBAStudentProfile, MBACourse, MBABatch, MBASession


class Command(BaseCommand):
    help = "Create dummy MBA User Accounts and Student Profiles for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of dummy students to create (default: 5)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='Password@123',
            help='Default password for all dummy student accounts (default: Password@123)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options['count']
        default_password = options['password']

        self.stdout.write(self.style.NOTICE(f"[*] Creating {count} dummy MBA student profiles...\n"))

        # 1. Ensure / Get College
        college = College.objects.first()
        if not college:
            college = College.objects.create(
                college_code="01",
                name="University MBA Department",
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f"[+] Created default College: {college.name}"))

        # 2. Ensure / Get Session & Batch
        session, _ = MBASession.objects.get_or_create(
            name="2024-26",
            defaults={"start_year": 2024, "end_year": 2026, "is_active": True}
        )
        batch, _ = MBABatch.objects.get_or_create(
            name="2024-2026",
            defaults={"session": session, "is_active": True}
        )

        # 3. Ensure / Get Course
        courses = list(MBACourse.objects.all())
        if not courses:
            c1 = MBACourse.objects.create(name="MBA (Finance)", discipline_code="FC", duration_years=2)
            c2 = MBACourse.objects.create(name="MBA (Marketing)", discipline_code="MC", duration_years=2)
            c3 = MBACourse.objects.create(name="MBA (Human Resource)", discipline_code="HC", duration_years=2)
            courses = [c1, c2, c3]
            self.stdout.write(self.style.SUCCESS(f"[+] Created default MBA Courses"))

        # Sample Indian names for dummy data
        first_names_male = ["Aarav", "Rahul", "Rohan", "Amit", "Vikas", "Deepak", "Sanjay", "Ankit"]
        first_names_female = ["Priya", "Ananya", "Sneha", "Pooja", "Neha", "Ritu", "Kavita", "Shalini"]
        last_names = ["Kumar", "Sharma", "Singh", "Verma", "Gupta", "Mishra", "Yadav", "Patel"]

        created_students = []

        base_num = random.randint(1000, 8000)

        for i in range(1, count + 1):
            is_female = (i % 2 == 0)
            first_name = random.choice(first_names_female) if is_female else random.choice(first_names_male)
            last_name = random.choice(last_names)
            gender = "Female" if is_female else "Male"

            reg_no = f"2411M{base_num + i:04d}"
            roll_no = f"{9000 + base_num + i}"
            username = reg_no

            # 4. Create UserAccount
            user, u_created = UserAccount.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username.lower()}@example.com",
                    "phone": f"98{random.randint(10000000, 99999999)}",
                    "user_type": "student",
                    "current_profile": "mba",
                    "college": college,
                    "is_active": True,
                    "is_verified": True,
                }
            )
            user.set_password(default_password)
            user.save()

            # 5. Create MBAStudentProfile
            course = random.choice(courses)
            profile, p_created = MBAStudentProfile.objects.get_or_create(
                registration_no=reg_no,
                defaults={
                    "user": user,
                    "roll_no": roll_no,
                    "first_name": first_name,
                    "last_name": last_name,
                    "father_name": f"{random.choice(first_names_male)} {last_name}",
                    "mother_name": f"{random.choice(first_names_female)} {last_name}",
                    "date_of_birth": date(2001, random.randint(1, 12), random.randint(1, 28)),
                    "gender": gender,
                    "mobile_no": user.phone,
                    "address": "Patna, Bihar",
                    "aadhar_no": f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}",
                    "college": college,
                    "course": course,
                    "batch": batch,
                    "current_semester": 1,
                    "session_str": "2024-26",
                    "status": "Regular",
                    "is_active": True,
                }
            )

            created_students.append({
                "username": username,
                "password": default_password,
                "name": f"{first_name} {last_name}",
                "reg_no": reg_no,
                "roll_no": roll_no,
                "course": course.name,
            })

        self.stdout.write(self.style.SUCCESS(f"[OK] Successfully created {len(created_students)} dummy MBA students!\n"))
        self.stdout.write(f"{'Username / Reg No':<20} | {'Password':<15} | {'Name':<20} | {'Course':<25}")
        self.stdout.write("-" * 85)
        for s in created_students:
            self.stdout.write(f"{s['username']:<20} | {s['password']:<15} | {s['name']:<20} | {s['course']:<25}")
