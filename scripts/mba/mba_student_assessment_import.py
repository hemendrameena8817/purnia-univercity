import os
import sys
import django
import csv
from decimal import Decimal, InvalidOperation
from django.db import transaction

# ---------------- DJANGO SETUP ----------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")
django.setup()

from mba_sem.models import (
    MBAStudentProfile,
    MBASession,
    MBABatch,
    MBACourseStructure,
    StudentCourseAssessment,
)

from colleges.models import College


# ---------------- GLOBAL COUNTERS ----------------

student_created = 0
student_updated = 0
assessment_created = 0
assessment_updated = 0


# ---------------- CLEANERS ----------------

def clean(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in ["", "\\N", "NULL", "null", "NA", "--"]:
        return None
    return value


def d(value):
    value = clean(value)
    try:
        return Decimal(value) if value else None
    except (InvalidOperation, ValueError):
        return None


def i(value):
    value = clean(value)
    try:
        return int(float(value)) if value else None
    except:
        return None


# ---------------- LABEL MAPPING ----------------

def map_label(status_value):
    status_value = clean(status_value)

    if status_value == "MID_TERM":
        return "CIA-Theory"

    if status_value == "END_TERM":
        return "ESE-Theory"

    return None


# ---------------- IMPORT ----------------

@transaction.atomic
def import_row(row):
    global student_created, student_updated
    global assessment_created, assessment_updated

    session_name = clean(row.get("session_code"))
    batch_name = clean(row.get("batch_code"))

    session_obj, _ = MBASession.objects.get_or_create(
        name=session_name,
        defaults={
            "start_year": int(session_name.split("-")[0]) if session_name else None,
            "end_year": int(session_name.split("-")[1]) if session_name else None,
        },
    )

    batch_obj, _ = MBABatch.objects.get_or_create(
        name=batch_name,
        defaults={"session": session_obj},
    )

    college_code = clean(row.get("institute_code"))
    college_obj = College.objects.filter(college_code=college_code).first()

    # ---------------- STUDENT ----------------

    full_name = clean(row.get("student_name")) or ""
    parts = full_name.split()
    first = parts[0] if parts else ""
    last = " ".join(parts[1:]) if len(parts) > 1 else ""

    student_obj, created_student = MBAStudentProfile.objects.update_or_create(
        registration_no=clean(row.get("college_reg_no")),
        defaults={
            "first_name": first,
            "last_name": last,
            "roll_no": clean(row.get("college_roll_no")),
            "father_name": clean(row.get("fathers_name")),
            "mother_name": clean(row.get("mothers_name")),
            "session_str": session_name,
            "batch": batch_obj,
            "college": college_obj,
        },
    )

    if created_student:
        student_created += 1
    else:
        student_updated += 1

    # ---------------- LABEL + EXAM TYPE ----------------

    raw_status = clean(row.get("status"))
    label = map_label(raw_status)
    exam_type_value = clean(row.get("exam_type")) or "REGULAR"

    # ---------------- MARKS ----------------

    ind_max = i(row.get("maximum_mark"))
    ind_pass = d(row.get("pass_mark"))
    obtained = d(row.get("mark_secured"))

    is_absent = False
    if clean(row.get("mark_secured")) == "AB" or obtained is None:
        is_absent = True
        obtained = None

    ind_grace = d(row.get("sub_grace_chk")) or Decimal("0")

    course_struct = MBACourseStructure.objects.filter(
        course_code=clean(row.get("paper_code")),
        semester=clean(row.get("semester_code")),
        label=label,
    ).first()

    credit = course_struct.credit if course_struct else 4

    comb_marks = d(row.get("subject_total_mark")) or Decimal("0")
    comb_grace = d(row.get("total_grace_chk")) or Decimal("0")
    comb_final = comb_marks + comb_grace

    course_max = i(row.get("grand_total_mark"))
    course_total = d(row.get("total_secured_mark")) or Decimal("0")
    course_pass = (course_max * Decimal("0.4")) if course_max else None

    if obtained and ind_pass and obtained >= ind_pass:
        credit_obtained = Decimal(credit)
    else:
        credit_obtained = Decimal("0")

    course_type = None
    if label and "CIA" in label:
        course_type = "CIA"
    elif label and "ESE" in label:
        course_type = "ESE"

    # ---------------- ASSESSMENT ----------------

    obj, created_assessment = StudentCourseAssessment.objects.update_or_create(
        student=student_obj,
        semester=clean(row.get("semester_code")),
        session=session_name,
        paper_code=clean(row.get("paper_code")),
        label=label,
        exam_type=exam_type_value,
        defaults={

            "degree": "MBA",
            "course_name": clean(row.get("subject_name")),
            "course_short_name": clean(row.get("subject_code")),
            "course_type": course_type,
            "course_code": clean(row.get("subject_code")),
            "batch": batch_obj,
            "college_code": college_code,

            "ind_max_marks": ind_max,
            "ind_pass_marks": ind_pass,
            "ind_is_absent": is_absent,
            "ind_marks_obtained": obtained,
            "ind_grace_obtained": ind_grace,
            "ind_final_marks_obtained": obtained,

            "comb_max_marks": i(row.get("subject_total_mark")),
            "comb_max_credits": credit,
            "comb_pass_marks": ind_pass,
            "comb_marks_obtained": comb_marks,
            "comb_grace_obtained": comb_grace,
            "comb_final_marks_obtained": comb_final,
            "comb_credit_obtained": credit_obtained,
            "comb_numeric_grade": d(row.get("gpa")),
            "comb_letter_grade": clean(row.get("let_grad")),
            "comb_grade_point": d(row.get("subject_gp")),

            "course_max_marks": course_max,
            "course_max_credits": credit,
            "course_pass_marks": course_pass,
            "course_marks_obtained": course_total,
            "course_grace_obtained": comb_grace,
            "course_final_marks_obtained": course_total,
            "course_credit_obtained": credit_obtained,
            "course_grade_point": d(row.get("subject_gp")),

            "sem_max_credit": credit * 6,
            "sem_credit_obtained": d(row.get("total_ce")),
            "sgpa": d(row.get("cgpa")),
            "sem_result": clean(row.get("final_result")),
            "next_sem_status": clean(row.get("dsc_grad")),
            "sem_grace_obtained": comb_grace,

            "temp_total_gp": d(row.get("subject_gp")),
            "json_data": row,
        },
    )

    if created_assessment:
        assessment_created += 1
    else:
        assessment_updated += 1


# ---------------- RUN ----------------

def run_import(path):
    success = 0
    fail = 0

    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                import_row(row)
                success += 1
            except Exception as e:
                fail += 1
                print("Error:", row.get("student_name"), "-", e)

    print("\n================ IMPORT SUMMARY ================")
    print("Total Success Rows     :", success)
    print("Total Failed Rows      :", fail)
    print("Students Created       :", student_created)
    print("Students Updated       :", student_updated)
    print("Assessments Created    :", assessment_created)
    print("Assessments Updated    :", assessment_updated)
    print("================================================\n")


if __name__ == "__main__":
    file_path = os.path.join(BASE_DIR, "old_data", "mba", "mba_1st_sem_export.csv")
    run_import(file_path)
