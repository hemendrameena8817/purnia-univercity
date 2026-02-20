"""
MBA Student Import Script (DATA FIXED VERSION)
=============================================

✔ MBA course ALWAYS saved
✔ Specialization handled safely
✔ Numeric / blank discipline handled
✔ No course NULL issue

Run:
poetry run python manage.py shell
>>> from scripts.mba.import_mba_student_profiles import run_import
>>> run_import("old_data/mba/MBA_SEM_STUDENT_DETAILS_NEW_1.xlsx")
"""

import os
import pandas as pd
from django.db import transaction
from django.contrib.auth import get_user_model

from colleges.models import College
from mba_sem.models import MBAStudentProfile, MBABatch, MBACourse

User = get_user_model()


# --------------------------------------------------
# Discipline Mapping (FINAL)
# --------------------------------------------------
DISCIPLINE_MAP = {
    "MC": "Marketing",
    "FC": "Finance",
    "HC": "Human Resource",
}


def safe_str(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


def split_name(name):
    name = safe_str(name)
    if not name:
        return "", ""
    parts = name.split()
    return parts[0], " ".join(parts[1:])


def normalize_gender(g):
    g = safe_str(g).upper()
    if g in ["M", "MALE"]:
        return "Male"
    if g in ["F", "FEMALE"]:
        return "Female"
    return None


def get_or_create_course(discipline_code):
    """
    ALWAYS returns a valid MBA course
    """
    discipline_code = safe_str(discipline_code).upper()

    # Default = General MBA
    course_name = "MBA (Master of Business Administration)"
    specialization = None

    if discipline_code in DISCIPLINE_MAP:
        specialization = DISCIPLINE_MAP[discipline_code]
        course_name = f"MBA ({specialization})"

    course, _ = MBACourse.objects.get_or_create(
        name=course_name,
        defaults={
            "discipline_code": discipline_code if discipline_code in DISCIPLINE_MAP else None,
            "duration_years": 2,
        },
    )
    return course


# --------------------------------------------------
@transaction.atomic
def run_import(file_path):

    if not os.path.exists(file_path):
        print("❌ File not found")
        return

    df = pd.read_excel(file_path)

    for _, row in df.iterrows():

        registration_no = safe_str(row.get("Registration No"))
        if not registration_no:
            continue

        roll_no = safe_str(row.get("Roll No"))
        first_name, last_name = split_name(row.get("Student Name"))

        father_name = safe_str(row.get("Father Name"))
        mother_name = safe_str(row.get("Mother Name"))
        gender = normalize_gender(row.get("Gender"))

        batch_name = safe_str(row.get("Batch"))
        session = safe_str(row.get("Session"))
        semester = row.get("Semester")

        institute_code = safe_str(row.get("Institute code"))
        discipline_code = row.get("Discipline Code")

        # ---------------- College ----------------
        college = None
        if institute_code:
            college = College.objects.filter(college_code=institute_code).first()

        # ---------------- Course (FIXED) ----------------
        course = get_or_create_course(discipline_code)

        # ---------------- Batch ----------------
        batch = None
        if batch_name:
            batch, _ = MBABatch.objects.get_or_create(
                name=batch_name,
                defaults={"json_data": {"session": session}},
            )

        # ---------------- User ----------------
        user, _ = User.objects.get_or_create(
            username=registration_no,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        # ---------------- Student Profile ----------------
        student, created = MBAStudentProfile.objects.update_or_create(
            registration_no=registration_no,
            defaults={
                "user": user,
                "first_name": first_name,
                "last_name": last_name,
                "roll_no": roll_no or None,
                "father_name": father_name or None,
                "mother_name": mother_name or None,
                "gender": gender,
                "college": college,
                "course": course,
                "batch": batch,
                "current_semester": int(semester) if not pd.isna(semester) else None,
                "session_str": session,
                "is_active": True,
            },
        )

        print(
            "CREATED" if created else "UPDATED",
            registration_no,
            "| COURSE:", course.name
        )

    print("\n✅ IMPORT COMPLETED — MBA COURSE ISSUE FIXED")
