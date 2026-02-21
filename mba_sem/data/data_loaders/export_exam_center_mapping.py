import os
import sys
import json
from pathlib import Path


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
from mba_sem.models import MBAExamCenterMapping


# -----------------------------------
# 🚀 Export Function
# -----------------------------------
def export_exam_center_mapping(output_file="mba_exam_center_mapping.json"):

    print("🚀 Extracting MBA Exam Center Mapping...\n")

    queryset = MBAExamCenterMapping.objects.select_related(
        "exam",
        "center"
    ).prefetch_related("attached_colleges")

    data = []

    for obj in queryset:
        record = {
            "exam": obj.exam.name if obj.exam else None,
            "center": obj.center.college_code if obj.center else None,
            "attached_colleges": list(
                obj.attached_colleges.values_list("college_code", flat=True)
            )
        }

        data.append(record)

    output_path = BASE_DIR / output_file

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Export completed → {output_path}")
    print(f"📦 Total Records: {len(data)}")


if __name__ == "__main__":
    export_exam_center_mapping()
