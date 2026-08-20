import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from colleges.models import College
from mba_sem.models import (
    MBAStudentProfile,
    MBACourse,
    MBABatch,
    MBASession,
    MBAExam,
    MBACommonCourseStructure,
    MBAExamRegistration,
    MBAStudentCourseAssessment,
    MBAExamResult,
)
from mba_sem.utils.tr.grading import (
    calculate_numeric_grade,
    calculate_credit_obtained,
    calculate_grade_point,
    get_letter_and_description,
)


class Command(BaseCommand):
    help = "Generate dummy CIA and ESE marks, exam registrations, and exam results for MBA students"

    def add_arguments(self, parser):
        parser.add_argument(
            '--semester',
            type=str,
            default='1',
            help='Semester number to generate marks for (default: 1)'
        )
        parser.add_argument(
            '--session',
            type=str,
            default='2024-26',
            help='Session string (default: 2024-26)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Number of students to generate marks for (default: 20)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        semester = str(options['semester'])
        session_str = options['session']
        limit = options['limit']

        self.stdout.write(self.style.NOTICE(f"[*] Generating dummy CIA & ESE marks for MBA Sem {semester} (Session: {session_str})...\n"))

        # 1. Ensure / Get College
        college = College.objects.first()
        if not college:
            college = College.objects.create(
                college_code="01",
                name="University MBA Department",
                is_active=True
            )

        # 2. Ensure / Get Session & Batch
        session_obj, _ = MBASession.objects.get_or_create(
            name=session_str,
            defaults={"start_year": 2024, "end_year": 2026, "is_active": True}
        )
        batch_obj, _ = MBABatch.objects.get_or_create(
            name=session_str.replace("-", "-20"),
            defaults={"session": session_obj, "is_active": True}
        )

        # 3. Ensure MBA Exam
        exam_name = f"MBA {semester}st Semester Examination 2024" if semester == '1' else f"MBA {semester}th Semester Examination 2024"
        exam, _ = MBAExam.objects.get_or_create(
            name=exam_name,
            semester=int(semester),
            session=session_str,
            defaults={
                "exam_month_year": "December 2024",
            }
        )
        self.stdout.write(self.style.SUCCESS(f"[+] Exam ready: {exam.name}"))

        # 4. Define Standard Subjects for Semester
        if semester == '1':
            subjects_data = [
                {"code": "MB-101", "name": "Management Principles & Practices", "type": "Theory", "has_cia": True},
                {"code": "MB-102", "name": "Organizational Behaviour", "type": "Theory", "has_cia": True},
                {"code": "MB-103", "name": "Managerial Economics", "type": "Theory", "has_cia": True},
                {"code": "MB-104", "name": "Accounting for Managers", "type": "Theory", "has_cia": True},
                {"code": "MB-105", "name": "Business Environment", "type": "Theory", "has_cia": True},
                {"code": "MB-106", "name": "Comprehensive Viva-Voce", "type": "Viva", "has_cia": False},
            ]
        elif semester == '4':
            subjects_data = [
                {"code": "MB-401", "name": "Corporate Governance & Business Ethics", "type": "Theory", "has_cia": True},
                {"code": "MB-402", "name": "Computer Application & MIS", "type": "Theory", "has_cia": True},
                {"code": "MB-403", "name": "Comprehensive Viva-Voce", "type": "Viva", "has_cia": False},
                {"code": "MB-404", "name": "Business Communication", "type": "Theory", "has_cia": True},
                {"code": "MB-405", "name": "Management of Change", "type": "Theory", "has_cia": True},
                {"code": "MB-406", "name": "Group Dynamics", "type": "Theory", "has_cia": True},
            ]
        else:
            subjects_data = [
                {"code": f"MB-{semester}01", "name": f"Core Subject {semester}-1", "type": "Theory", "has_cia": True},
                {"code": f"MB-{semester}02", "name": f"Core Subject {semester}-2", "type": "Theory", "has_cia": True},
                {"code": f"MB-{semester}03", "name": f"Core Subject {semester}-3", "type": "Theory", "has_cia": True},
                {"code": f"MB-{semester}04", "name": f"Elective Subject {semester}-4", "type": "Theory", "has_cia": True},
                {"code": f"MB-{semester}05", "name": f"Comprehensive Viva-Voce", "type": "Viva", "has_cia": False},
            ]

        common_subjects = []
        for s in subjects_data:
            subj_obj, _ = MBACommonCourseStructure.objects.get_or_create(
                code=s["code"],
                semester=semester,
                defaults={
                    "course_name": s["name"],
                    "course_type": s["type"],
                    "marks": 100,
                }
            )
            common_subjects.append((subj_obj, s))

        self.stdout.write(self.style.SUCCESS(f"[+] Loaded {len(common_subjects)} course subjects."))

        # 5. Fetch Students
        students = list(MBAStudentProfile.objects.filter(is_active=True)[:limit])
        if not students:
            self.stdout.write(self.style.ERROR("[!] No students found. Please run 'python manage.py create_dummy_mba_students' first."))
            return

        self.stdout.write(self.style.NOTICE(f"[*] Processing {len(students)} students...\n"))

        assessment_count = 0
        results_created = 0

        for student in students:
            # 6. Ensure Exam Registration
            exam_reg, _ = MBAExamRegistration.objects.get_or_create(
                student=student,
                exam=exam,
                defaults={
                    "exam_type": "REGULAR",
                    "sem": int(semester),
                    "session": session_str,
                    "status": "APPROVED",
                }
            )
            exam_reg.exam_subjects.set([subj for subj, _ in common_subjects])

            student_total_marks = Decimal("0.0")
            student_max_marks = Decimal("0.0")
            student_total_credits_earned = Decimal("0.0")
            student_total_grade_points = Decimal("0.0")
            all_subjects_passed = True
            cia_all_passed = True
            ese_all_passed = True

            for subj_obj, meta in common_subjects:
                has_cia = meta["has_cia"]

                # Marks Ranges
                if has_cia:
                    # CIA: Max 30, Pass 13.5
                    cia_max = 30
                    cia_pass = Decimal("13.5")
                    cia_obtained = Decimal(str(random.randint(16, 28))) # realistic pass mark
                    cia_is_absent = False
                    cia_is_pass = cia_obtained >= cia_pass

                    # ESE: Max 70, Pass 31.5
                    ese_max = 70
                    ese_pass = Decimal("31.5")
                    ese_obtained = Decimal(str(random.randint(35, 65))) # realistic pass mark
                    ese_is_absent = False
                    ese_is_pass = ese_obtained >= ese_pass

                    comb_marks = cia_obtained + ese_obtained
                    comb_max = 100
                    comb_pass = Decimal("45.0")
                else:
                    # Viva only (ESE only): Max 100, Pass 45
                    cia_max = 0
                    cia_pass = Decimal("0.0")
                    cia_obtained = None
                    cia_is_absent = False
                    cia_is_pass = True

                    ese_max = 100
                    ese_pass = Decimal("45.0")
                    ese_obtained = Decimal(str(random.randint(55, 92)))
                    ese_is_absent = False
                    ese_is_pass = ese_obtained >= ese_pass

                    comb_marks = ese_obtained
                    comb_max = 100
                    comb_pass = Decimal("45.0")

                numeric_grade = calculate_numeric_grade(float(comb_marks))
                credit_obtained = 4 if (ese_is_pass and (cia_is_pass if has_cia else True)) else 0
                gp = calculate_grade_point(numeric_grade, credit_obtained)
                letter_grade, _ = get_letter_and_description(numeric_grade)

                student_total_marks += comb_marks
                student_max_marks += Decimal(str(comb_max))
                student_total_credits_earned += Decimal(str(credit_obtained))
                student_total_grade_points += Decimal(str(gp))

                if not (ese_is_pass and (cia_is_pass if has_cia else True)):
                    all_subjects_passed = False
                if has_cia and not cia_is_pass:
                    cia_all_passed = False
                if not ese_is_pass:
                    ese_all_passed = False

                # Save CIA Assessment Record
                if has_cia:
                    MBAStudentCourseAssessment.objects.update_or_create(
                        student=student,
                        paper_code=subj_obj.code,
                        semester=semester,
                        label="CIA",
                        defaults={
                            "mba_exam": exam,
                            "course_name": subj_obj.course_name,
                            "course_type": subj_obj.course_type,
                            "course_code": subj_obj.code,
                            "degree": "MBA",
                            "session": session_str,
                            "batch": student.batch or batch_obj,
                            "college_code": student.college.college_code if student.college else "01",
                            "exam_type": "REGULAR",
                            "attendance": "Present",
                            "ind_max_marks": cia_max,
                            "ind_pass_marks": cia_pass,
                            "ind_marks_obtained": cia_obtained,
                            "ind_final_marks_obtained": cia_obtained,
                            "ind_is_absent": cia_is_absent,
                            "ind_is_pass": cia_is_pass,
                            "comb_max_marks": comb_max,
                            "comb_pass_marks": comb_pass,
                            "comb_max_credits": 4,
                            "comb_marks_obtained": comb_marks,
                            "comb_final_marks_obtained": comb_marks,
                            "comb_credit_obtained": Decimal(str(credit_obtained)),
                            "comb_numeric_grade": Decimal(str(numeric_grade)),
                            "comb_letter_grade": letter_grade,
                            "comb_grade_point": Decimal(str(gp)),
                        }
                    )
                    assessment_count += 1

                # Save ESE Assessment Record
                MBAStudentCourseAssessment.objects.update_or_create(
                    student=student,
                    paper_code=subj_obj.code,
                    semester=semester,
                    label="ESE",
                    defaults={
                        "mba_exam": exam,
                        "course_name": subj_obj.course_name,
                        "course_type": subj_obj.course_type,
                        "course_code": subj_obj.code,
                        "degree": "MBA",
                        "session": session_str,
                        "batch": student.batch or batch_obj,
                        "college_code": student.college.college_code if student.college else "01",
                        "exam_type": "REGULAR",
                        "attendance": "Present",
                        "ind_max_marks": ese_max,
                        "ind_pass_marks": ese_pass,
                        "ind_marks_obtained": ese_obtained,
                        "ind_final_marks_obtained": ese_obtained,
                        "ind_is_absent": ese_is_absent,
                        "ind_is_pass": ese_is_pass,
                        "comb_max_marks": comb_max,
                        "comb_pass_marks": comb_pass,
                        "comb_max_credits": 4,
                        "comb_marks_obtained": comb_marks,
                        "comb_final_marks_obtained": comb_marks,
                        "comb_credit_obtained": Decimal(str(credit_obtained)),
                        "comb_numeric_grade": Decimal(str(numeric_grade)),
                        "comb_letter_grade": letter_grade,
                        "comb_grade_point": Decimal(str(gp)),
                    }
                )
                assessment_count += 1

            # 7. Create/Update Final Exam Result Summary
            percentage = (student_total_marks / student_max_marks * 100) if student_max_marks > 0 else Decimal("0.0")
            sem_result_status = "PASS" if all_subjects_passed else "PROMOTED"
            next_sem = int(semester) + 1 if int(semester) < 4 else None

            MBAExamResult.objects.update_or_create(
                student=student,
                semester=semester,
                session=session_str,
                defaults={
                    "cia_pass": cia_all_passed,
                    "ese_pass": ese_all_passed,
                    "semester_result": sem_result_status,
                    "total_marks_obtained": student_total_marks,
                    "percentage": Decimal(f"{percentage:.2f}"),
                    "next_semester": next_sem,
                    "next_sem_status": "ELIGIBLE" if sem_result_status in ["PASS", "PROMOTED"] else "NOT_ELIGIBLE",
                }
            )
            results_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] Dummy Data Generation Complete!\n"
            f"  - Students Processed: {len(students)}\n"
            f"  - Assessment Records (CIA + ESE): {assessment_count}\n"
            f"  - Final Semester Exam Results: {results_created}\n"
        ))
