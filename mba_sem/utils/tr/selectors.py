from collections import defaultdict
from mba_sem.models import (
    MBAStudentCourseAssessment,
    MBACommonCourseStructure,
)


def fetch_assessments(students, college, semester, batch_uid=None):
    print("SELECTORS.PY")

    students = list(students)
    if not students:
        return [], {}, {}, []

    course = students[0].course

    # -----------------------------------
    # 1️⃣ SUBJECTS FROM COMMON STRUCTURE
    # -----------------------------------
    subject_qs = MBACommonCourseStructure.objects.filter(
        semester=str(semester),
        mbaexamregistration__student__course=course
    ).distinct()

    subject_codes = list(
        subject_qs.values_list("code", flat=True)
    )

    subject_master = {
        obj.code: obj.course_name
        for obj in subject_qs
    }

    # -----------------------------------
    # 🔥 SWAP MB-403 WITH 3RD POSITION
    # -----------------------------------
    if "MB-403" in subject_codes and len(subject_codes) > 2:
        idx_403 = subject_codes.index("MB-403")
        subject_codes[2], subject_codes[idx_403] = (
            subject_codes[idx_403],
            subject_codes[2],
        )

    # -----------------------------------
    # 2️⃣ STUDENT ASSESSMENTS
    # -----------------------------------
    qs = MBAStudentCourseAssessment.objects.filter(
        student__in=students,
        semester=str(semester),
        college_code=college.college_code,
        paper_code__in=subject_codes
    )

    if batch_uid:
        qs = qs.filter(batch__uid=batch_uid)

    all_assessments = list(qs)

    student_map = defaultdict(list)
    for obj in all_assessments:
        student_map[obj.student.id].append(obj)

    print("FINAL SUBJECT_CODES =", subject_codes)

    return (
        all_assessments,
        subject_master,
        student_map,
        subject_codes
    )