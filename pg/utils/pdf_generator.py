def generate_pg_admit_card_pdf(student, exam):
    from weasyprint import HTML
    import os
    import logging
    from django.conf import settings
    from django.template.loader import get_template
    from pg.models import PGExamCenterMapping, PGExamSchedule, PGExamRegistration, PGStudentCourseAssessment
    from pup_umis_backend.utils.file_utils import image_to_base64

    logger = logging.getLogger(__name__)

    def _get_base64_image(image_field_or_path):
        """
        Robustly convert a Django FieldFile, filesystem path, or static path to base64.
        Handles S3 (.open()) and local paths/URLs.
        """
        import base64
        if not image_field_or_path:
            return ""
        try:
            # 1. Django FieldFile (S3/Storage friendly)
            if hasattr(image_field_or_path, 'open'):
                try:
                    with image_field_or_path.open('rb') as f:
                        return base64.b64encode(f.read()).decode()
                except Exception:
                    pass
            # 2. Local path fallback
            if isinstance(image_field_or_path, str) and os.path.exists(image_field_or_path):
                with open(image_field_or_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
        except Exception as e:
            logger.error(f"Image encode error: {e}")
        return ""

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
    # Prefer registration matching the exam's session, then fall back to the
    # most recent REGISTERED record (view already guarantees one exists).
    registration = PGExamRegistration.objects.filter(
        student=student,
        status='REGISTERED',
        session=getattr(exam, 'session', None),
    ).order_by('-created_at').first()

    if not registration:
        registration = PGExamRegistration.objects.filter(
            student=student,
            status='REGISTERED',
        ).order_by('-created_at').first()

    exam_type = registration.exam_type if registration else "REGULAR"

    # ── Exam Schedules ─────────────────────────────────────────────────────────
    schedules_query = PGExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure', 'group').order_by('exam_date', 'exam_time')

    # Filter by student's department group
    if student.department:
        dept_schedules = schedules_query.filter(group__department=student.department)
        if dept_schedules.exists():
            schedules_query = dept_schedules

    # ── Get course codes from the schedule, then look up names from assessments ─
    # Step 1: get all course codes offered in this exam for the student's dept
    schedule_codes = list(
        schedules_query.values_list('common_course_structure__course_code', flat=True).distinct()
    )

    # Step 2: find the student's assessment entries for those codes (single query)
    assessment_map = {}   # { paper_code: course_name }
    if schedule_codes:
        assess_qs = PGStudentCourseAssessment.objects.filter(
            student=student,
            label__icontains='ESE',
            exam_type__iexact=exam_type,
            paper_code__in=schedule_codes,
        )
        
        # If registration exists, we can be more specific about session/semester
        if registration:
            # Note: registration.sem is int, assessment.semester is typically '1ST', '2ND' etc.
            # We already have semester_text or similar from registration logic if needed, 
            # but usually paper_code + exam_type + student is enough.
            assess_qs = assess_qs.filter(session=registration.session)

        for a in assess_qs.values('paper_code', 'course_name'):
            if a['paper_code'] and a['paper_code'] not in assessment_map:
                assessment_map[a['paper_code']] = a['course_name'] or a['paper_code']

    # Step 3: For BACK/IMPROVEMENT, further filter schedules to only the
    # student's specific back papers (codes found in their assessments)
    if exam_type in ['BACK', 'IMPROVEMENT']:
        schedules_query = schedules_query.filter(
            common_course_structure__course_code__in=assessment_map.keys()
        )

    schedules = list(schedules_query)

    # ── Attach subject name from assessment to each schedule ───────────────────
    for s in schedules:
        if s.common_course_structure:
            code = s.common_course_structure.course_code
            s.assessment_course_name = assessment_map.get(code)

    # ── Context ────────────────────────────────────────────────────────────────
    context = {
        "student": student,
        "registration": registration,
        "exam_type": exam_type,
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.center_code if exam_center else "-",
        "schedules": schedules,
        "university_logo": _get_base64_image(os.path.join(STATIC_IMAGES, "purnea-logo.png")),
        "watermark_logo": _get_base64_image(os.path.join(STATIC_IMAGES, "purnea-logo.png")),
        "student_photo": _get_base64_image(student.profile_image),
        "student_sig": _get_base64_image(student.signature),
        "controller_signature": _get_base64_image(os.path.join(settings.BASE_DIR, "static", "images", "controller-of-examination-signature.png")),
    }

    html_string = get_template("pg/admit_card.html").render(context)

    try:
        pdf_file = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        logger.info(f"PG Admit Card PDF generated for {student.registration_no}, size: {len(pdf_file)} bytes")
        return pdf_file
    except Exception as e:
        logger.error(f"PG Admit Card PDF generation failed: {e}")
        return None
