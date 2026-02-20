import os
import sys
import json
from pathlib import Path


# -----------------------------------
# 🔍 Auto Detect Django Project Root
# -----------------------------------
def get_project_root():
    """
    Automatically find project root by locating manage.py
    """
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent

    raise Exception("❌ manage.py not found. Project root not detected.")


# Get BASE_DIR dynamically
BASE_DIR = get_project_root()

# Add project root to Python path
sys.path.append(str(BASE_DIR))

# -----------------------------------
# ⚙️ Setup Django Environment
# -----------------------------------
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pup_umis_backend.settings"
)

import django
django.setup()


# -----------------------------------
# 📦 Import Models (After setup)
# -----------------------------------
from mba_sem.models import MBAExamSchedule


# -----------------------------------
# 🚀 Export Function
# -----------------------------------
def export_exam_schedule(output_file="mba_exam_schedule.json"):

    print("🚀 Extracting MBA Exam Schedule...\n")
    print("📂 Project Root:", BASE_DIR, "\n")

    queryset = MBAExamSchedule.objects.select_related(
        "exam",
        "common_course_structure"
    )

    data = []

    for obj in queryset:
        record = {
            "exam": obj.exam.name if obj.exam else None,
            "common_course_structure": (
                obj.common_course_structure.code
                if obj.common_course_structure else None
            ),
            "exam_date": obj.exam_date.isoformat() if obj.exam_date else None,
            "exam_time": obj.exam_time,
            "sitting": obj.sitting,
        }

        data.append(record)

    # Write JSON file
    output_path = BASE_DIR / output_file

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Export completed → {output_path}")
    print(f"📦 Total Records: {len(data)}")


# -----------------------------------
# ▶️ Run Script
# -----------------------------------
if __name__ == "__main__":
    export_exam_schedule()
