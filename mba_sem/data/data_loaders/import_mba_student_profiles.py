# File: mba_sem/data/data_loaders/import_mba_student_profiles.py

import os
import sys
import json
import uuid
from pathlib import Path
from django.db import transaction
from django.utils.dateparse import parse_date


def get_project_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent
    raise Exception("manage.py not found")


BASE_DIR = get_project_root()
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")

import django
django.setup()

from mba_sem.models import MBAStudentProfile, MBACourse, MBABatch
from accounts.models import UserAccount
from colleges.models import College


@transaction.atomic
def import_mba_student_profiles(file_name="mba_student_profiles_export.json"):

    file_path = Path(__file__).resolve().parent / file_name

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    created_count = 0
    skipped_count = 0

    for record in records:

        reg_no = record.get("registration_no")

        if not reg_no:
            skipped_count += 1
            continue

        # -----------------------------
        # Resolve relations
        # -----------------------------
        college = College.objects.filter(
            college_code=record.get("college_code")
        ).first()

        course = MBACourse.objects.filter(
            name=record.get("course_name")
        ).first()

        batch = MBABatch.objects.filter(
            name=record.get("batch_name")
        ).first()

        # -----------------------------
        # STEP 1: User resolve / create
        # -----------------------------
        username = record.get("username") or reg_no

        user, _ = UserAccount.objects.get_or_create(
            username=username,
            defaults={
                "uid": uuid.uuid4(),
                "first_name": record.get("first_name"),
                "last_name": record.get("last_name"),
                "user_type": "student",
                "current_profile": "mba",
                "college": college,
                "is_active": True,
            }
        )

        # -----------------------------
        # STEP 2: Student Profile create
        # -----------------------------
        student, created = MBAStudentProfile.objects.get_or_create(
            registration_no=reg_no,
            defaults={
                "uid": uuid.UUID(record["uid"]),
                "user": user,
                "roll_no": record.get("roll_no"),
                "first_name": record.get("first_name"),
                "last_name": record.get("last_name"),
                "hindi_name": record.get("hindi_name"),
                "father_name": record.get("father_name"),
                "mother_name": record.get("mother_name"),
                "date_of_birth": parse_date(record.get("date_of_birth")) if record.get("date_of_birth") else None,
                "gender": record.get("gender"),
                "mobile_no": record.get("mobile_no"),
                "address": record.get("address"),
                "aadhar_no": record.get("aadhar_no"),
                "college": college,
                "course": course,
                "batch": batch,
                "current_semester": record.get("current_semester"),
                "session_str": record.get("session_str"),
                "status": record.get("status"),
                "profile_image": record.get("profile_image"),
                "signature": record.get("signature"),
                "is_active": record.get("is_active", True),
                "json_data": record.get("json_data"),
            }
        )

        if created:
            created_count += 1
        else:
            skipped_count += 1

    print(f"✅ Created: {created_count}")
    print(f"⏭️ Skipped (Already Exists): {skipped_count}")
    print("🎯 Import Completed")


if __name__ == "__main__":
    import_mba_student_profiles()