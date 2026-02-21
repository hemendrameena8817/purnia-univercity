# File: mba_sem/data/data_loaders/import_mba_exam_registrations.py

import os
import sys
import json
import uuid
from pathlib import Path
from django.db import transaction
from django.utils.dateparse import parse_datetime


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

from mba_sem.models import (
    MBAExamRegistration,
    MBAStudentProfile,
    MBAExam,
    MBACommonCourseStructure,
)


@transaction.atomic
def import_mba_exam_registrations(file_name="mba_exam_registrations_export.json"):

    file_path = Path(__file__).resolve().parent / file_name

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    created_count = 0
    skipped_count = 0

    for record in records:

        student = MBAStudentProfile.objects.filter(
            registration_no=record.get("registration_no")
        ).first()

        exam = MBAExam.objects.filter(
            name=record.get("exam_name")
        ).first()

        if not student:
            print(f"⚠️ Student not found: {record.get('registration_no')}")
            continue

        if not exam:
            print(f"⚠️ Exam not found: {record.get('exam_name')}")
            continue

        registration, created = MBAExamRegistration.objects.get_or_create(
            student=student,
            exam=exam,
            exam_type=record.get("exam_type"),
            sem=record.get("sem"),
            session=record.get("session"),
            defaults={
                "start_date": parse_datetime(record.get("start_date")) if record.get("start_date") else None,
                "end_date": parse_datetime(record.get("end_date")) if record.get("end_date") else None,
                "is_open": record.get("is_open", False),
                "fees": record.get("fees"),
                "status": record.get("status"),
                "json_data": record.get("json_data"),
            }
        )

        if created:
            subjects = MBACommonCourseStructure.objects.filter(
                code__in=record.get("subjects_codes", [])
            )
            registration.exam_subjects.set(subjects)
            created_count += 1
        else:
            skipped_count += 1

    print(f"✅ Created: {created_count}")
    print(f"⏭️ Skipped (Already Exists): {skipped_count}")
    print("🎯 Import Completed")


if __name__ == "__main__":
    import_mba_exam_registrations()