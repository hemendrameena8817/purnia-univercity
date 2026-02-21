import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")
django.setup()

from django.db import transaction
from mba_sem.models import (
    MBAExamRegistration,
    MBAStudentCourseAssessment,
)


def run():

    print("Starting SCA import for 4nd Semester only...")

    registrations = (
        MBAExamRegistration.objects
        .filter(sem=4)  # 🔥 Only 4th Semester
        .select_related("student", "exam", "student__batch")
        .prefetch_related("exam_subjects")
    )

    create_list = []
    skipped = 0

    # for reg in registrations:

    #     student = reg.student
    #     exam = reg.exam
    #     semester = "4"  
    #     session = reg.session
    #     batch = student.batch
    #     exam_type = reg.exam_type

    #     for subject in reg.exam_subjects.all():

    #         for label in ["CIA-Theory", "ESE-Practical"]:

    #             exists = MBAStudentCourseAssessment.objects.filter(
    #                 student=student,
    #                 paper_code=subject.code,
    #                 semester=semester,
    #                 label=label,
    #                 exam_type=exam_type,
    #                 session=session
    #             ).exists()

    #             if exists:
    #                 skipped += 1
    #                 continue

    #             create_list.append(
    #                 MBAStudentCourseAssessment(
    #                     mba_exam=exam,
    #                     student=student,
    #                     course_name=subject.course_name,
    #                     course_short_name=subject.course_name,
    #                     course_type=subject.course_type,
    #                     course_code=subject.code,
    #                     paper_code=subject.code,
    #                     semester=semester,
    #                     label=label,
    #                     session=session,
    #                     batch=batch,
    #                     exam_type=exam_type,
    #                     college_code=student.college.college_code if student.college else None,
    #                 )
    #             )
        
    queryset = MBAStudentCourseAssessment.objects.filter(
        semester="4",
        label="ESE-Practical",
        paper_code="MB-403"
    )

    updated_count = queryset.update(ind_pass_marks="45")

    # print(updated_count)

    # print(f"Updated {updated_count} records successfully.")
    print("Update Completed.")

    with transaction.atomic():
        MBAStudentCourseAssessment.objects.bulk_create(
            create_list,
            batch_size=1000
        )

    print("Created:", len(create_list))
    print("Skipped duplicates:", skipped)
    print("4nd Semester Import Done.")


if __name__ == "__main__":
    run()
