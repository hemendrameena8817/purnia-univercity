import os
import sys
import json
from pathlib import Path
from django.db import transaction


# -----------------------------------
# 🔍 Auto Detect Project Root
# -----------------------------------
def get_project_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent
    raise Exception("❌ manage.py not found.")


BASE_DIR = get_project_root()
sys.path.append(str(BASE_DIR))


# -----------------------------------
# ⚙️ Setup Django
# -----------------------------------
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


# -----------------------------------
# 📥 Import Function
# -----------------------------------
@transaction.atomic
def import_exam_center_mapping(file_path):

    print(f"🚀 Importing Exam Center Mapping from {file_path.name}\n")

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    created_count = 0
    updated_count = 0

    for record in records:

        exam = MBAExam.objects.filter(name=record.get("exam")).first()
        if not exam:
            print(f"⚠️ Exam not found: {record.get('exam')}")
            continue

        center = College.objects.filter(
            college_code=record.get("center")
        ).first()

        if not center:
            print(f"⚠️ Center not found: {record.get('center')}")
            continue

        # Create or get mapping (unique_together: exam + center)
        mapping, created = MBAExamCenterMapping.objects.get_or_create(
            exam=exam,
            center=center
        )

        # Clear old attached colleges (optional safety)
        mapping.attached_colleges.clear()

        for code in record.get("attached_colleges", []):
            college = College.objects.filter(college_code=code).first()
            if college:
                mapping.attached_colleges.add(college)
            else:
                print(f"⚠️ Attached college not found: {code}")

        if created:
            created_count += 1
        else:
            updated_count += 1

    print("\n✅ Import Completed")
    print(f"🆕 Created: {created_count}")
    print(f"♻ Updated: {updated_count}")


# -----------------------------------
# ▶️ Run Script
# -----------------------------------
if __name__ == "__main__":
    input_file = BASE_DIR / "mba_exam_center_mapping.json"
    import_exam_center_mapping(input_file)
