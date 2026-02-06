"""
BTech Exam Schedule Import Script
=================================
Strict validation-first import of BTech Exam Schedule from Excel.

Command:
poetry run python -m scripts.betch.import_btech_exam_schedule old_data/btech/BTECH_EXAM_SCHEDULE.xlsx
"""

import os
import django
import pandas as pd
import re
from datetime import datetime, date, timedelta
from django.db import transaction

# -------------------------------------------------------------------
# Django setup
# -------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")
django.setup()

from btech.models import (
    BTechExam,
    BTechExamSchedule,
    BTechCommonCourseStructure,
)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def parse_exam_details(exam_str):
    """
    Extracts Year and Session from Exam name
    Example:
    "B. Tech. 4th Year Civil Engineering-Special Examination 2025"
    """
    if not isinstance(exam_str, str):
        return None, None

    year = None
    session = None

    year_match = re.search(r"(\d+)(?:st|nd|rd|th)\s+Year", exam_str, re.IGNORECASE)
    if year_match:
        year = int(year_match.group(1))

    session_match = re.search(r"Session\s+([\d-]+)", exam_str, re.IGNORECASE)
    if session_match:
        session = session_match.group(1).strip()

    if not session:
        year_end_match = re.search(r"(\d{4})$", exam_str.strip())
        if year_end_match:
            session = year_end_match.group(1)

    return year, session


def excel_serial_to_date(serial):
    """
    Convert Excel serial number to Python date
    Excel epoch starts at 1899-12-30
    """
    return date(1899, 12, 30) + timedelta(days=int(serial))


def parse_exam_date(exam_date_raw, row_num, validation_errors):
    """
    Robust Excel date parser:
    - Excel serial numbers (46297)
    - pandas Timestamp
    - datetime
    - string formats
    - blocks invalid / epoch dates
    """
    exam_date = None

    if pd.isna(exam_date_raw):
        exam_date = None

    elif isinstance(exam_date_raw, pd.Timestamp):
        exam_date = exam_date_raw.date()

    elif isinstance(exam_date_raw, datetime):
        exam_date = exam_date_raw.date()

    elif isinstance(exam_date_raw, (int, float)):
        # Excel serial number
        exam_date = excel_serial_to_date(exam_date_raw)

    elif isinstance(exam_date_raw, str) and exam_date_raw.strip():
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                exam_date = datetime.strptime(exam_date_raw.strip(), fmt).date()
                break
            except ValueError:
                continue

    # Final validation
    if not exam_date or exam_date.year < 2000:
        validation_errors.append(
            f"Row {row_num}: Invalid Exam Date '{exam_date_raw}'."
        )
        return None

    return exam_date


# -------------------------------------------------------------------
# Main Import
# -------------------------------------------------------------------
def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print(f"📄 Reading file: {file_path}")

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return

    print(f"📊 Total rows found: {len(df)}")

    # ----------------------------------------------------------------
    # PHASE 1 – VALIDATION
    # ----------------------------------------------------------------
    print("\n[PHASE 1] Validation started...")
    validation_errors = []
    processed_rows = []

    last_exam_name = None

    for index, row in df.iterrows():
        row_num = index + 2  # Excel row number

        # ---- Exam Name (forward fill) ----
        exam_name_val = str(row.get("Exam", "")).strip()
        if exam_name_val and exam_name_val.lower() != "nan":
            last_exam_name = exam_name_val

        if not last_exam_name:
            validation_errors.append(
                f"Row {row_num}: Exam name missing and cannot be forward-filled."
            )
            continue

        exam_name = last_exam_name

        # ---- Subject Code ----
        subject_code = str(row.get("Subject Code", "")).strip()
        if not subject_code or subject_code.lower() == "nan":
            validation_errors.append(f"Row {row_num}: Subject Code is missing.")
            continue

        # ---- Exam Date ----
        exam_date_raw = row.get("Exam date")
        exam_date = parse_exam_date(exam_date_raw, row_num, validation_errors)
        if not exam_date:
            continue

        # ---- Exam Time ----
        exam_time = str(row.get("Exam time", "")).strip()
        if exam_time.lower() == "nan":
            exam_time = ""

        # ---- Course Structure ----
        course_structure = BTechCommonCourseStructure.objects.filter(
            code=subject_code
        ).first()

        if not course_structure:
            validation_errors.append(
                f"Row {row_num}: Subject Code '{subject_code}' "
                "not found in BTechCommonCourseStructure."
            )
            continue

        processed_rows.append(
            {
                "exam_name": exam_name,
                "course_structure": course_structure,
                "date": exam_date,
                "time": exam_time,
            }
        )

    if validation_errors:
        print(f"\n❌ VALIDATION FAILED ({len(validation_errors)} errors)\n")
        for err in validation_errors:
            print(f"  - {err}")
        print("\nFix the Excel sheet and re-run import.")
        return

    print(f"✅ Validation successful ({len(processed_rows)} rows).")

    # ----------------------------------------------------------------
    # PHASE 2 – IMPORT
    # ----------------------------------------------------------------
    print("\n[PHASE 2] Import started...")
    stats = {
        "exams_created": 0,
        "schedules_created": 0,
        "schedules_updated": 0,
    }

    try:
        with transaction.atomic():
            exam_cache = {}

            for row in processed_rows:
                exam_name = row["exam_name"]

                if exam_name not in exam_cache:
                    year, session = parse_exam_details(exam_name)
                    exam_obj, created = BTechExam.objects.get_or_create(
                        name=exam_name,
                        defaults={"year": year, "session": session},
                    )
                    if created:
                        stats["exams_created"] += 1
                        print(f"🆕 Exam created: {exam_name}")
                    exam_cache[exam_name] = exam_obj

                exam_obj = exam_cache[exam_name]

                sitting = (
                    "1st Sitting"
                    if "10:00" in row["time"]
                    else "2nd Sitting"
                )

                _, created = BTechExamSchedule.objects.update_or_create(
                    exam=exam_obj,
                    common_course_structure=row["course_structure"],
                    defaults={
                        "exam_date": row["date"],
                        "exam_time": row["time"],
                        "sitting": sitting,
                    },
                )

                if created:
                    stats["schedules_created"] += 1
                else:
                    stats["schedules_updated"] += 1

        print("\n🎉 IMPORT COMPLETED SUCCESSFULLY")
        print(f"  Exams Created      : {stats['exams_created']}")
        print(f"  Schedules Created  : {stats['schedules_created']}")
        print(f"  Schedules Updated  : {stats['schedules_updated']}")

    except Exception as e:
        print(f"\n🔥 FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Import BTech Exam Schedule (Strict Validation)"
    )
    parser.add_argument("file", type=str, help="Path to Excel file")
    args = parser.parse_args()

    run_import(args.file)
