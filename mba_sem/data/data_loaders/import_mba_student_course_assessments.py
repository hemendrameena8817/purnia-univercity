# File: mba_sem/data/data_loaders/import_mba_student_course_assessments.py

import os
import sys
import json
import uuid
from pathlib import Path
from django.db import transaction


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

from mba_sem.models import *


@transaction.atomic
def import_mba_student_course_assessments(
    file_name="mba_student_course_assessments_export.json"
):

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

        batch = MBABatch.objects.filter(
            name=record.get("batch_name")
        ).first()

        if not student:
            print(f"⚠️ Student not found: {record.get('registration_no')}")
            continue

        obj, created = MBAStudentCourseAssessment.objects.get_or_create(
            student=student,
            paper_code=record.get("paper_code"),
            semester=record.get("semester"),
            label=record.get("label"),
            exam_type=record.get("exam_type"),
            session=record.get("session"),
            defaults={
                "mba_exam": exam,
                "course_name": record.get("course_name"),
                "course_short_name": record.get("course_short_name"),
                "course_type": record.get("course_type"),
                "course_code": record.get("course_code"),
                "degree": record.get("degree"),
                "batch": batch,
                "college_code": record.get("college_code"),
                "attendance": record.get("attendance"),
                "ind_max_marks": record.get("ind_max_marks"),
                "ind_pass_marks": record.get("ind_pass_marks"),
                "ind_is_absent": record.get("ind_is_absent", False),
                "ind_marks_obtained": record.get("ind_marks_obtained"),
                "ind_grace_obtained": record.get("ind_grace_obtained"),
                "ind_final_marks_obtained": record.get("ind_final_marks_obtained"),
                "comb_marks_obtained": record.get("comb_marks_obtained"),
                "comb_final_marks_obtained": record.get("comb_final_marks_obtained"),
                "sgpa": record.get("sgpa"),
                "sem_result": record.get("sem_result"),
                "next_sem_status": record.get("next_sem_status"),
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
    import_mba_student_course_assessments()