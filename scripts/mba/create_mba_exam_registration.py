import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")
django.setup()

from mba_sem.models import (
    MBAStudentProfile,
    MBAExam,
    MBAExamSchedule,
    MBAExamRegistration,
)

# ==============================
# CONFIG
# ==============================
EXAM_UID = "51f63d0d-ad5a-4ab9-b698-cd134d3e2598"
DEFAULT_FEES = 250
DEFAULT_STATUS = "Verified"


def create_exam_registration_for_exam():
    exam = MBAExam.objects.get(uid=EXAM_UID)

    print("\n==============================")
    print("EXAM:", exam.name)
    print("SEM:", exam.semester, "| SESSION:", exam.session)
    print("==============================\n")

    students = (
        MBAStudentProfile.objects
        .select_related("course")
        .filter(is_active=True)
    )

    for student in students:
        # ----------------------------
        # DISCIPLINE
        # ----------------------------
        discipline = None
        if student.course and student.course.discipline_code:
            discipline = student.course.discipline_code.upper().strip()

        print("\nSTUDENT:", student.registration_no)
        print("DISCIPLINE:", discipline)

        # ----------------------------
        # FETCH SCHEDULES
        # ----------------------------
        schedules = MBAExamSchedule.objects.filter(exam=exam)

        filtered_schedules = []

        for schedule in schedules:
            ccs = schedule.common_course_structure
            if not ccs or not ccs.code:
                continue

            code = ccs.code.upper().strip()

            # 1️⃣ COMMON SUBJECTS → MB-101, MB-29
            if code.startswith("MB-") and "-" not in code[3:]:
                filtered_schedules.append(schedule)

            # 2️⃣ DISCIPLINE SUBJECTS → MB-FC-120
            elif discipline and code.startswith(f"MB-{discipline}-"):
                filtered_schedules.append(schedule)

        # ----------------------------
        # SORT SUBJECTS
        # ----------------------------
        filtered_schedules.sort(
            key=lambda s: (
                s.exam_date is None,
                not s.exam_time,
                not s.sitting
            )
        )

        print("TOTAL SUBJECTS =", len(filtered_schedules))
        for s in filtered_schedules:
            print("  SUBJECT:", s.common_course_structure.code)

        if not filtered_schedules:
            print("⚠ No subjects found, skipping")
            continue

        # ----------------------------
        # CREATE / UPDATE REGISTRATION
        # ----------------------------
        exam_reg, created = MBAExamRegistration.objects.get_or_create(
            student=student,
            exam=exam,
            defaults={
                "fees": DEFAULT_FEES,
                "status": DEFAULT_STATUS,
                "sem": exam.semester,
                "session": exam.session,
                "exam_type": "REGULAR",
            }
        )

        if not created:
            exam_reg.fees = DEFAULT_FEES
            exam_reg.status = DEFAULT_STATUS
            exam_reg.sem = exam.semester
            exam_reg.session = exam.session
            exam_reg.save()

        # ----------------------------
        # ADD SUBJECTS (M2M)
        # ----------------------------
        exam_reg.exam_subjects.clear()
        exam_reg.exam_subjects.add(
            *[s.common_course_structure for s in filtered_schedules]
        )

        print("✔ Exam registration saved")

    print("\n✅ ALL STUDENTS PROCESSED SUCCESSFULLY\n")


if __name__ == "__main__":
    create_exam_registration_for_exam()
