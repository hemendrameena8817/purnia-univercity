# data_loaders/exam_schedule.py

import json
from datetime import datetime
from django.db import transaction
from mba_sem.models import (
    MBAExamSchedule,
    MBAExam,
    MBACommonCourseStructure
)


def parse_date(date_str):
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()


@transaction.atomic
def import_exam_schedule(file_path):

    print(f"📘 Importing Exam Schedule from {file_path.name}")

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    created_count = 0
    skipped_count = 0

    for record in records:

        exam = MBAExam.objects.filter(name=record.get("exam")).first()
        if not exam:
            print(f"⚠️ Exam not found: {record.get('exam')}")
            continue

        course = None
        if record.get("common_course_structure"):
            course = MBACommonCourseStructure.objects.filter(
                code=record.get("common_course_structure")
            ).first()

            if not course:
                print(f"⚠️ Course not found: {record.get('common_course_structure')}")
                continue

        exists = MBAExamSchedule.objects.filter(
            exam=exam,
            common_course_structure=course
        ).exists()

        if exists:
            skipped_count += 1
            continue

        MBAExamSchedule.objects.create(
            exam=exam,
            common_course_structure=course,
            exam_date=parse_date(record.get("exam_date")),
            exam_time=record.get("exam_time"),
            sitting=record.get("sitting"),
        )

        created_count += 1

    print(f"✅ Created: {created_count}")
    print(f"⏭️ Skipped: {skipped_count}\n")
