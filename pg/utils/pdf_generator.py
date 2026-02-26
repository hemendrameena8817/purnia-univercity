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
        Convert a Django ImageField, filesystem path, or HTTP URL to a base64
        data-URI suitable for embedding directly in HTML.
        """
        if not image_field_or_path:
            return None

        import base64
        from io import BytesIO
        try:
            from PIL import Image, ImageOps
            PIL_AVAILABLE = True
        except ImportError:
            PIL_AVAILABLE = False

        try:
            import requests
            raw = None

            # 1. Django FileField / ImageField — try .open() first (works for S3 + local)
            if hasattr(image_field_or_path, 'open'):
                try:
                    with image_field_or_path.open('rb') as f:
                        raw = f.read()
                except Exception:
                    pass

            # 2. Local path fallback
            if raw is None and hasattr(image_field_or_path, 'path'):
                try:
                    if os.path.exists(image_field_or_path.path):
                        with open(image_field_or_path.path, 'rb') as f:
                            raw = f.read()
                except Exception:
                    pass

            # 3. Plain filesystem path string
            if raw is None and isinstance(image_field_or_path, str) and os.path.exists(image_field_or_path):
                with open(image_field_or_path, 'rb') as f:
                    raw = f.read()

            # 4. HTTP URL (string or .url attribute)
            if raw is None:
                url = None
                if isinstance(image_field_or_path, str) and image_field_or_path.startswith('http'):
                    url = image_field_or_path
                elif hasattr(image_field_or_path, 'url'):
                    try:
                        url = image_field_or_path.url
                        if not url.startswith('http'):
                            url = None
                    except Exception:
                        url = None
                if url:
                    try:
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            raw = resp.content
                    except Exception:
                        pass

            if raw is None:
                return None

            if PIL_AVAILABLE:
                img = Image.open(BytesIO(raw))
                try:
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass
                
                # Transparency handling: RGBA -> RGB (white background)
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                buf = BytesIO()
                img.save(buf, format='JPEG', quality=85)
                raw = buf.getvalue()
                mime = 'image/jpeg'
            else:
                mime = 'image/png'

            b64 = base64.b64encode(raw).decode('utf-8')
            return f"data:{mime};base64,{b64}"

        except Exception as e:
            logger.error(f"Image encode error: {e}")
            return None

    def _load_static_image(relative_path):
        # 1. Try common static path (local dev)
        common_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'common', relative_path)
        if os.path.exists(common_path):
            return _get_base64_image(common_path)

        # 2. Try static/images/ directly (live server often serves from here)
        direct_path = os.path.join(settings.BASE_DIR, 'static', 'images', relative_path)
        if os.path.exists(direct_path):
            return _get_base64_image(direct_path)

        # 3. Try UG static (for shared signatures)
        ug_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images', relative_path)
        if os.path.exists(ug_path):
            return _get_base64_image(ug_path)

        return None

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
    # Schedules hold ONE generic row per group (e.g. CC-X for all CC papers).
    # They give us date/time/sitting only; actual subjects come from assessments.
    schedules_query = PGExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure', 'group').order_by('exam_date', 'exam_time')

    # Filter by student's department group if possible
    if student.department:
        dept_schedules = schedules_query.filter(group__department=student.department)
        if dept_schedules.exists():
            schedules_query = dept_schedules

    # Build TWO lookups for matching assessment subjects to exam schedules:
    # 1. schedule_by_course_type: 'CC' → schedule (from ccs.course_type)  ← most reliable
    # 2. schedule_by_prefix: 'CC' → schedule (from ccs.course_code prefix) ← fallback
    schedule_by_prefix = {}
    schedule_by_course_type = {}
    schedule_default = schedules_query.first()  # last resort fallback
    for s in schedules_query:
        ccs = s.common_course_structure
        if ccs:
            # By course_type (most reliable: 'CC', 'EC', 'AECC', 'SEC')
            if ccs.course_type:
                schedule_by_course_type[ccs.course_type.upper()] = s
            # By course_code prefix (fallback: 'CC-X' → 'CC')
            if ccs.course_code:
                prefix = ccs.course_code.split('-')[0].upper()
                schedule_by_prefix[prefix] = s

    # ── Get subjects from student's ESE assessments ────────────────────────────
    # Convert registration semester (int) to text like '3RD'
    _SUFFIXES = {1: 'ST', 2: 'ND', 3: 'RD'}
    sem_text = None
    if registration and registration.sem:
        sv = registration.sem
        sem_text = f"{sv}{_SUFFIXES.get(sv, 'TH')}" if isinstance(sv, int) else str(sv).upper()

    assessment_filter = dict(
        student=student,
        label__icontains='ESE',
        session=registration.session if registration else exam.session,
    )
    if sem_text:
        assessment_filter['semester'] = sem_text
    if exam_type in ['BACK', 'IMPROVEMENT']:
        assessment_filter['exam_type__iexact'] = exam_type

    # Build subject rows (deduplicated by paper_code)
    from types import SimpleNamespace
    seen_papers = set()
    schedules = []
    for a in PGStudentCourseAssessment.objects.filter(**assessment_filter).order_by('paper_code'):
        key = a.paper_code or a.course_code or ''
        if not key or key in seen_papers:
            continue
        seen_papers.add(key)

        # Find correct schedule for this subject's date/time:
        # Priority: course_type match → course_code prefix → paper_code prefix → fallback
        sched = None
        # 1. Direct course_type match (most accurate: 'CC', 'EC', 'AECC', 'SEC')
        if a.course_type:
            sched = schedule_by_course_type.get(a.course_type.upper())
        # 2. Prefix from course_code
        if not sched and a.course_code:
            sched = schedule_by_prefix.get(a.course_code.split('-')[0].upper())
        # 3. Prefix from paper_code
        if not sched and a.paper_code:
            sched = schedule_by_prefix.get(a.paper_code.split('-')[0].upper())
        # 4. Last resort
        if not sched:
            sched = schedule_default

        schedules.append(SimpleNamespace(
            common_course_structure=SimpleNamespace(
                course_code=a.course_code or '-',
                course_name=a.course_name or '-',
            ),
            assessment_course_name=a.course_name or '-',
            exam_date=sched.exam_date if sched else None,
            exam_time=sched.exam_time if sched else '-',
            sitting=sched.sitting if sched else '-',
        ))


    # ── Context ────────────────────────────────────────────────────────────────
    context = {
        "student": student,
        "registration": registration,
        "exam_type": exam_type,
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.center_code if exam_center else "-",
        "schedules": schedules,
        "university_logo": _load_static_image("purnea-logo.png"),
        "watermark_logo": _load_static_image("purnea-logo.png"),
        "student_photo": _get_base64_image(student.profile_image),
        "student_sig": _get_base64_image(student.signature),
        "controller_signature": _load_static_image("controller-of-examination-signature.png"),
    }

    html_string = get_template("pg/admit_card.html").render(context)

    try:
        pdf_file = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        logger.info(f"PG Admit Card PDF generated for {student.registration_no}, size: {len(pdf_file)} bytes")
        return pdf_file
    except Exception as e:
        logger.error(f"PG Admit Card PDF generation failed: {e}")
        return None
