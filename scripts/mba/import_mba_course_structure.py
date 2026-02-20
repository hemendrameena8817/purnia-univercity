"""
MBA Course Structure Import Script
=================================

Imports MBA Course Structure from Excel.

Creates:
1. MBACommonCourseStructure  (ONE per course + semester)
2. MBACourseStructure        (MULTIPLE per course: CIA / ESE / PRACTICAL)

Run (Shell):
-----------
poetry run python manage.py shell

>>> from scripts.mba.import_mba_course_structure import run_import
>>> run_import("old_data/mba/MBA_Course_Structure.xlsx")

"""

import os
import sys
import django
import pandas as pd
from django.db import transaction

# ----------------------------------
# Django setup
# ----------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")
django.setup()

from mba_sem.models import (
    MBACommonCourseStructure,
    MBACourseStructure,
)

# ----------------------------------
# Helpers
# ----------------------------------
def safe_str(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


def safe_num(val):
    if pd.isna(val):
        return 0
    try:
        return float(val)
    except Exception:
        return 0


# ----------------------------------
# Import Logic
# ----------------------------------
def run_import(file_path):
    if not os.path.exists(file_path):
        print("❌ File not found:", file_path)
        return

    df = pd.read_excel(file_path)

    print("\n📊 Columns found:", df.columns.tolist())
    print("📘 Total rows:", len(df))
    print("🚀 Import started...\n")

    stats = {
        "common_created": 0,
        "component_created": 0,
        "component_updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    # Ensures common course created only once
    common_created_cache = set()

    for idx, row in df.iterrows():
        print(f"\n➡️ ROW {idx + 2}")

        try:
            with transaction.atomic():

                course_code = safe_str(row.get("course_code"))
                semester = safe_str(row.get("semester"))
                label = safe_str(row.get("label"))

                if not course_code or not semester or not label:
                    print("  ❌ SKIP: course_code / semester / label missing")
                    stats["skipped"] += 1
                    continue

                course_name = safe_str(row.get("course_name"))
                short_name = safe_str(row.get("course_short_name"))
                course_type = safe_str(row.get("course_type")) or "Core"
                credit = safe_num(row.get("credit"))
                max_marks = safe_num(row.get("max_marks"))
                min_marks = safe_num(row.get("min_marks"))
                description = safe_str(row.get("description"))

                print(f"  📘 {course_code} | Sem {semester} | {label}")

                # ----------------------------------
                # 1. COMMON COURSE STRUCTURE
                # ----------------------------------
                common_key = (course_code, semester)

                if common_key not in common_created_cache:
                    MBACommonCourseStructure.objects.get_or_create(
                        code=course_code,
                        semester=semester,
                        defaults={
                            "course_name": course_name,
                            "course_type": course_type,
                            "marks": 100,
                        },
                    )
                    common_created_cache.add(common_key)
                    stats["common_created"] += 1
                    print("  ✅ COMMON COURSE CREATED")

                # ----------------------------------
                # 2. COMPONENT STRUCTURE
                # ----------------------------------
                obj, created = MBACourseStructure.objects.update_or_create(
                    course_code=course_code,
                    semester=semester,
                    label=label,
                    defaults={
                        "course_name": course_name,
                        "course_short_name": short_name,
                        "course_type": course_type,
                        "credit": credit,
                        "max_marks": max_marks,
                        "min_marks": min_marks,
                        "description": description,
                    },
                )

                if created:
                    stats["component_created"] += 1
                    print("  ✅ COMPONENT CREATED")
                else:
                    stats["component_updated"] += 1
                    print("  🔁 COMPONENT UPDATED")

        except Exception as e:
            stats["errors"] += 1
            print("  ❌ ERROR:", str(e))

    # ----------------------------------
    # Summary
    # ----------------------------------
    print("\n✅ IMPORT FINISHED")
    print("-" * 50)
    for k, v in stats.items():
        print(f"{k}: {v}")


# ----------------------------------
# Entry Point
# ----------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Please provide Excel file path")
        print("Usage:")
        print("  poetry run python scripts/mba/import_mba_course_structure.py file.xlsx")
        sys.exit(1)

    excel_path = sys.argv[1]
    run_import(excel_path)
