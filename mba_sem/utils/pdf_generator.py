def generate_mba_admit_card_pdf(student, exam):
    from weasyprint import HTML, CSS
    import io, base64, os
    from django.conf import settings
    from django.template.loader import get_template
    from mba_sem.models import MBAExamCenterMapping, MBAExamSchedule
    from pup_umis_backend.utils.file_utils import image_to_base64
    import logging

    logger = logging.getLogger(__name__)

    # Get exam center mapping
    exam_center = None
    if student.college:
        mapping = MBAExamCenterMapping.objects.filter(
            exam=exam,
            attached_colleges=student.college
        ).first()
        print(f"{mapping = }")
        if mapping:
            exam_center = mapping.center
            print(f"{exam_center = }")
    
    # Get exam schedules
    # schedules = MBAExamSchedule.objects.filter(
    #     exam=exam
    # ).select_related('common_course_structure')

    # -----------------------------
    # Get exam schedules (discipline based + common)
    # -----------------------------
    discipline = ""

    if student.course and student.course.discipline_code:
        discipline = student.course.discipline_code.strip()

    print("FINAL DISCIPLINE =", discipline)

    # Get all schedules of exam
    schedules = MBAExamSchedule.objects.filter(exam=exam)

    filtered_schedules = []

    for schedule in schedules:
        code = schedule.common_course_structure.code or ""
        code = code.upper().strip()

        # COMMON SUBJECT → MB-101, MB-29, MB-90
        if code.startswith("MB-") and "-" not in code[3:]:
            filtered_schedules.append(schedule)

        # DISCIPLINE SUBJECT → MB-FC-120
        elif discipline and code.startswith(f"MB-{discipline}-"):
            filtered_schedules.append(schedule)

    print("TOTAL SUBJECTS =", len(filtered_schedules))

    for s in filtered_schedules:
        print("SUBJECT CODE =", s.common_course_structure.code)

    filtered_schedules.sort(
        key=lambda s: (s.exam_date is None, not s.exam_time, not s.sitting)
    )

    # use this in context
    schedules = filtered_schedules

    # Prepare context for template
    context = {
        'discipline_code': student.course,
        "exam": exam,
        "student": student,
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.center_code if exam_center else "-",
        "schedules": schedules,
        "university_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "watermark_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "student_photo": image_to_base64(student.profile_image.path if student.profile_image else None),
        "student_sig": image_to_base64(student.signature.path if student.signature else None),
        "controller_signature": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
    }

    # Render HTML template
    html_string = get_template("mba_sem/admit_card.html").render(context)

    try:
        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        
        logger.info(f"PDF generated successfully using WeasyPrint, size: {len(pdf_file)} bytes")
        return pdf_file
        
    except Exception as e:
        logger.error(f"PDF generation failed with WeasyPrint: {str(e)}")
        return None


def generate_mba_roll_sheet_pdf(exam, college, course):
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from collections import OrderedDict
    from mba_sem.models import (
        MBAExamRegistration,
        MBAExamSchedule,
        MBAExamCenterMapping,
    )
    from pup_umis_backend.utils.file_utils import image_to_base64
    import os
    import logging

    logger = logging.getLogger(__name__)

    print("\n==============================")
    print("START MBA ROLL SHEET DEBUG")
    print("==============================")
    print("EXAM   :", exam.name)
    print("COLLEGE:", college.name)
    print("COURSE :", course.name)
    print("==============================\n")

    # =====================================================
    # 1️⃣ FETCH EXAM REGISTRATIONS (SOURCE OF TRUTH)
    # =====================================================
    registrations = (
        MBAExamRegistration.objects
        .filter(
            exam=exam,
            student__college=college,
            student__course=course,
        )
        .select_related(
            "student",
            "student__batch",
            "student__course",
        )
        .prefetch_related("exam_subjects")
        .order_by(
            "student__roll_no",
            "student__registration_no"
        )
    )

    print("🔎 REGISTRATIONS COUNT =", registrations.count())

    if not registrations.exists():
        print("❌ NO REGISTRATIONS FOUND")
        return None

    # =====================================================
    # 2️⃣ EXAM CENTER
    # =====================================================
    center_name = "-"

    center_mapping = (
        MBAExamCenterMapping.objects
        .filter(
            exam=exam,
            attached_colleges=college
        )
        .select_related("center")
        .first()
    )

    if center_mapping and center_mapping.center:
        center_name = center_mapping.center.name

    print("🏫 EXAM CENTER =", center_name)

    # =====================================================
    # 3️⃣ SUBJECTS (ONLY FROM EXAM REGISTRATION ✅)
    # =====================================================
    subjects_map = OrderedDict()

    for reg in registrations:
        print(
            f"DEBUG REG {reg.id} | SUBJECT COUNT =",
            reg.exam_subjects.count()
        )

        for subj in reg.exam_subjects.all():
            code = (subj.code or "").strip().upper()
            if not code:
                continue

            subjects_map[code] = {
                "id": subj.id,
                "code": subj.code,
                "course_name": subj.course_name,
            }

    subjects = list(subjects_map.values())

    print("📚 SUBJECTS FOUND =", len(subjects))

    if not subjects:
        print("❌ NO SUBJECTS FOUND FROM REGISTRATION")
        print("👉 FIX REQUIRED: exam_subjects M2M is empty")
        return None

    # =====================================================
    # 4️⃣ OPTIONAL: SCHEDULE MAP (DATE / TIME ONLY)
    # =====================================================
    schedule_map = {
        s.common_course_structure.code: s
        for s in MBAExamSchedule.objects.filter(
            exam=exam,
            common_course_structure__isnull=False
        )
    }

    # =====================================================
    # 5️⃣ STUDENT ROW DATA
    # =====================================================
    student_data = []

    for reg in registrations:
        student = reg.student

        subject_codes = list(
            reg.exam_subjects.values_list("code", flat=True)
        )

        print(
            f"👤 {student.roll_no} | SUBJECTS = {len(subject_codes)}"
        )

        student_data.append({
            "name": student.get_full_name(),
            "roll_no": student.roll_no or "-",
            "registration_no": student.registration_no or "-",
            "subject_codes": subject_codes,
        })

    print("👥 TOTAL STUDENTS =", len(student_data))

    # =====================================================
    # 6️⃣ TEMPLATE CONTEXT
    # =====================================================
    first_student = registrations.first().student

    context = {
        "exam": exam,
        "college": college,
        "course": course,
        "course_name": course.name,
        "discipline_code": course.discipline_code,
        "batch_name": first_student.batch.name if first_student.batch else "-",
        "semester": exam.semester or "-",
        "session": exam.session or "-",
        "exam_month_year": exam.exam_month_year or "-",
        "college_name": college.name,
        "center_name": center_name,
        "subjects": subjects,
        "year": f"{exam.exam_month_year}" if exam.exam_month_year else "-", 
        "student_data": student_data,
        "controller_signature": image_to_base64(
            os.path.join(
                settings.MEDIA_ROOT,
                "common/controller-of-examination-signature.png"
            )
        ),
    }

    print("🧾 CONTEXT READY — RENDERING PDF")

    # =====================================================
    # 7️⃣ RENDER PDF
    # =====================================================
    html_string = get_template(
        "mba_sem/roll_sheet.html"
    ).render(context)

    try:
        pdf_file = HTML(
            string=html_string,
            base_url=settings.MEDIA_ROOT
        ).write_pdf()

        print("✅ PDF GENERATED SUCCESSFULLY\n")
        return pdf_file

    except Exception as e:
        print("❌ PDF GENERATION FAILED:", str(e))
        logger.exception("MBA Roll Sheet PDF failed")
        return None


from mba_sem.models import *

def generate_mba_attendance_sheet_pdf(exam, college):
    """
    Generate student-wise attendance sheets for MBA students.
    """
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from pup_umis_backend.utils.file_utils import image_to_base64, generate_barcode_base64
    import os, logging

    logger = logging.getLogger(__name__)

    # 1️⃣ Eligible students
    semester_regs = MBAExamRegistration.objects.filter(
        sem=exam.semester,
        student__college=college
    ).select_related(
        'student', 'student__course'
    ).order_by('student__roll_no')

    if not semester_regs.exists():
        logger.warning("No eligible MBA students found")
        return None

    # 2️⃣ Exam center
    mapping = MBAExamCenterMapping.objects.filter(
        exam=exam,
        attached_colleges=college
    ).select_related('center').first()

    exam_center = mapping.center if mapping else None

    # 3️⃣ University logo
    logo_path = os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")
    university_logo = image_to_base64(logo_path) if os.path.exists(logo_path) else None

    # 4️⃣ All exam schedules (once)
    all_schedules = MBAExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure').order_by(
        'exam_date', 'exam_time'
    )

    # 5️⃣ Build attendance data
    attendance_data = []

    for reg in semester_regs:
        student = reg.student

        # 🔹 Discipline (SHORT)
        discipline = (student.course.discipline_code or "").strip().upper() \
            if student.course else ""

        # 🔹 Filter schedules
        filtered_schedules = [
            s for s in all_schedules
            if s.common_course_structure
            and s.common_course_structure.code
            and (
                (
                    s.common_course_structure.code.upper().startswith("MB-")
                    and "-" not in s.common_course_structure.code[3:]
                ) or (
                    discipline
                    and s.common_course_structure.code.upper().startswith(f"MB-{discipline}-")
                )
            )
        ]

        # 🔹 Barcode
        barcode_text = (
            f"Roll:{student.roll_no or ''}, "
            f"Reg:{student.registration_no or ''}, "
            f"Name:{student.get_full_name()}, "
            f"Sem:{exam.semester}"
        )
        barcode_base64 = generate_barcode_base64(barcode_text)

        # 🔹 Photo
        photo_base64 = None
        if student.profile_image:
            try:
                photo_base64 = image_to_base64(student.profile_image.path)
            except Exception as e:
                logger.error(f"Photo error {student.registration_no}: {e}")

        # 🔹 Student schedules
        student_schedules = [
            {
                'date': s.exam_date.strftime('%d-%m-%Y') if s.exam_date else '-',
                'exam_time': s.exam_time or '',
                'sitting': s.sitting or '',
                'subject_name': s.common_course_structure.course_name,
                'subject_code': s.common_course_structure.code,
            }
            for s in filtered_schedules
        ]

        attendance_data.append({
            'name': student.get_full_name(),
            'roll_no': student.roll_no or 'N/A',
            'registration_no': student.registration_no or 'N/A',
            'photo': photo_base64,
            'college_name': college.name,
            'barcode': barcode_base64,
            'schedules': student_schedules,
        })

    # 6️⃣ Template context
    context = {
        'attendance_data': attendance_data,
        'university_logo': university_logo,
        'exam_header': f"{exam.name} (Semester {exam.semester})",
        'center_name': (
            f"{exam_center.center_code} - {exam_center.name}"
            if exam_center else "Not Assigned"
        ),
    }

    html_string = get_template('mba_sem/attendance_sheet.html').render(context)

    try:
        return HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
    except Exception as e:
        logger.error(f"MBA Attendance Sheet PDF error: {e}")
        return None
