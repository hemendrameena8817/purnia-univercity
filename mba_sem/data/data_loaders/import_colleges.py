# File: scripts/import_colleges.py

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

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pup_umis_backend.settings"
)

import django
django.setup()

from colleges.models import College
from university.models import University
from academics.models import Degree


@transaction.atomic
def import_colleges(file_name):

    file_path = BASE_DIR / file_name
    print(f"📘 Importing Colleges from {file_path}\n")

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    created_count = 0
    skipped_count = 0

    for record in records:

        college_code = record.get("college_code")

        if not college_code:
            print("⚠️ Skipped (No College Code)")
            skipped_count += 1
            continue

        # 👇 FK resolve
        university = None
        if record.get("university"):
            university = University.objects.filter(
                name__exact=record["university"]
            ).first()

        # 👇 CREATE ONLY (NO UPDATE)
        college, created = College.objects.get_or_create(
            college_code=college_code,
            defaults={
                "uid": uuid.UUID(record["uid"]),
                "name": record.get("name"),
                "short_name": record.get("short_name"),
                "center_code": record.get("center_code"),
                "address": record.get("address"),
                "principal": record.get("principal"),
                "contact_no": record.get("contact_no"),
                "email": record.get("email"),
                "founded": parse_date(record.get("founded")) if record.get("founded") else None,
                "website": record.get("website"),
                "logo": record.get("logo"),
                "college_name_hindi": record.get("college_name_hindi"),
                "college_name_krutidev": record.get("college_name_krutidev"),
                "university": university,
                "is_active": record.get("is_active", True),
                "json_data": record.get("json_data"),
            }
        )

        if created:
            # M2M sirf new create pe
            degrees = Degree.objects.filter(
                name__in=record.get("degrees", [])
            )
            college.degree_offered.set(degrees)

            created_count += 1
        else:
            skipped_count += 1

    print(f"✅ Created: {created_count}")
    print(f"⏭️ Skipped (Already Exists): {skipped_count}")
    print("🎯 Import Completed\n")


if __name__ == "__main__":
    import_colleges()