def generate_pg_admit_card_pdf(student, exam):
    from weasyprint import HTML
    import os
    import logging
    from django.conf import settings
    from django.template.loader import get_template
    from pg.models import PGExamCenterMapping, PGExamSchedule, PGExamRegistration
    from pup_umis_backend.utils.file_utils import image_to_base64

    logger = logging.getLogger(__name__)

    # ── Static images path ─────────────────────────────────────────────────────
    STATIC_IMAGES = os.path.join(settings.BASE_DIR, "static", "images", "common")

    # ── Exam Center ────────────────────────────────────────────────────────────
    exam_center = None
    mapping = None
    if student.college:
        mapping = PGExamCenterMapping.objects.filter(
            exams=exam,
            attached_colleges=student.college
        ).first()
        if mapping:
            exam_center = mapping.center

    # ── Exam Registration ──────────────────────────────────────────────────────
    registration = PGExamRegistration.objects.filter(
        student=student,
        session=getattr(exam, 'session', None),
    ).order_by('-created_at').first()

    # Fallback: latest registration for this student
    if not registration:
        registration = PGExamRegistration.objects.filter(
            student=student
        ).order_by('-created_at').first()

    # ── Exam Schedules ─────────────────────────────────────────────────────────
    schedules_query = PGExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure', 'group').order_by('exam_date', 'exam_time')

    # Filter by student's department group
    if student.department:
        dept_schedules = schedules_query.filter(group__department=student.department)
        if dept_schedules.exists():
            schedules_query = dept_schedules

    schedules = schedules_query

    # ── Context ────────────────────────────────────────────────────────────────
    context = {
        "student": student,
        "registration": registration,
        "exam_type": registration.exam_type if registration else "REGULAR",
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.center_code if exam_center else "-",
        "schedules": schedules,
        "university_logo": image_to_base64(os.path.join(STATIC_IMAGES, "purnea-logo.png")),
        "watermark_logo": image_to_base64(os.path.join(STATIC_IMAGES, "purnea-logo.png")),
        "student_photo": image_to_base64(student.profile_image.path if student.profile_image else None),
        "student_sig": image_to_base64(student.signature.path if student.signature else None),
        "controller_signature": image_to_base64(os.path.join(settings.BASE_DIR, "static", "images", "controller-of-examination-signature.png")),
    }

    html_string = get_template("pg/admit_card.html").render(context)

    try:
        pdf_file = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        logger.info(f"PG Admit Card PDF generated for {student.registration_no}, size: {len(pdf_file)} bytes")
        return pdf_file
    except Exception as e:
        logger.error(f"PG Admit Card PDF generation failed: {e}")
        return None
