import os
import sys
import json
from pathlib import Path
from django.db import transaction


# -----------------------------------
# 🔍 Auto Detect Django Project Root
# -----------------------------------
def get_project_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent
    raise Exception("❌ manage.py not found.")


BASE_DIR = get_project_root()
sys.path.append(str(BASE_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pup_umis_backend.settings"
)

import django
django.setup()


# -----------------------------------
# 📦 Import Models
# -----------------------------------
from mba_sem.models import MBAExamCenterMapping, MBAExam
from colleges.models import College


@transaction.atomic
def import_exam_center_mapping(file_name="mba_exam_center_mapping.json"):

    file_path = BASE_DIR / file_name

    print(f"📘 Importing Exam Center Mapping from {file_path}\n")

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    created_count = 0
    skipped_count = 0

    for record in records:

        exam_name = record.get("exam")
        center_code = record.get("center")
        attached_codes = record.get("attached_colleges", [])

        exam = MBAExam.objects.filter(name__exact=exam_name).first()
        if not exam:
            print(f"⚠️ Exam not found: {exam_name}")
            continue

        center = College.objects.filter(college_code=center_code).first()
        if not center:
            print(f"⚠️ Center not found: {center_code}")
            continue

        mapping, created = MBAExamCenterMapping.objects.get_or_create(
            exam=exam,
            center=center
        )

        if not created:
            skipped_count += 1
        else:
            created_count += 1

        # Clear old attached colleges
        mapping.attached_colleges.clear()

        # Attach new colleges
        colleges = College.objects.filter(
            college_code__in=attached_codes
        )

        mapping.attached_colleges.add(*colleges)

    print(f"✅ Created: {created_count}")
    print(f"⏭️ Skipped: {skipped_count}")
    print("🎯 Import Completed\n")


if __name__ == "__main__":
    import_exam_center_mapping()
