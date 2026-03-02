def generate_pg_admit_card_pdf(student, exam):
    from weasyprint import HTML
    import os
    import logging
    from django.conf import settings
    from django.template.loader import get_template
    from pg.models import PGExamCenterMapping, PGExamSchedule, PGExamRegistration, PGStudentCourseAssessment
    from pup_umis_backend.utils.file_utils import image_to_base64
    import qrcode
    import base64
    from io import BytesIO
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

    # Build THREE lookups for matching assessment subjects to exam schedules:
    # 1. schedule_by_course_code: 'CC-1' → schedule  ← most accurate (exact match)
    # 2. schedule_by_course_type: 'CC' → schedule    ← fallback (only if course_type is unique)
    # 3. schedule_by_prefix: 'CC' → schedule         ← last prefix fallback
    schedule_by_course_code = {}   # exact: 'CC-1', 'EC-2', etc.
    schedule_by_course_type = {}   # broad: 'CC', 'EC', etc. (may overwrite if multiple groups)
    schedule_by_prefix = {}        # prefix fallback
    schedule_default = schedules_query.first()  # last resort fallback
    for s in schedules_query:
        ccs = s.common_course_structure
        if ccs:
            # Exact course_code match — most reliable (unique per paper)
            if ccs.course_code:
                schedule_by_course_code[ccs.course_code.upper()] = s
                # Prefix fallback (e.g. 'CC-1' → key 'CC')
                prefix = ccs.course_code.split('-')[0].upper()
                schedule_by_prefix[prefix] = s
            # course_type fallback (may be overwritten for same-type schedules)
            if ccs.course_type:
                schedule_by_course_type[ccs.course_type.upper()] = s

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
        # 1. Exact course_code match (most accurate: 'CC-1', 'EC-2', etc.)
        if a.course_code:
            sched = schedule_by_course_code.get(a.course_code.upper())
        # 2. Exact paper_code match
        if not sched and a.paper_code:
            sched = schedule_by_course_code.get(a.paper_code.upper())
        # 3. course_type match (broad: 'CC', 'EC', 'AECC', 'SEC')
        if not sched and a.course_type:
            sched = schedule_by_course_type.get(a.course_type.upper())
        # 4. Prefix from course_code
        if not sched and a.course_code:
            sched = schedule_by_prefix.get(a.course_code.split('-')[0].upper())
        # 5. Prefix from paper_code
        if not sched and a.paper_code:
            sched = schedule_by_prefix.get(a.paper_code.split('-')[0].upper())
        # 6. Last resort
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

    # ── QR Code ─────────────────────────────────────────────────────────────────
    qr_code_image = None
    try:
        qr_data = (
            f"Session: {registration.student.batch if registration else '-'}\n"
            f"Candidate Name: {student.first_name}\n"
            f"Registration No: {student.registration_no}\n"
            f"Exam Center: {exam_center.center_code if exam_center else '-'} - {exam_center.name if exam_center else '-'}\n"
            f"College: {student.college.name if student.college else '-'}\n"
            f"Exam Type: {exam_type}"
        )

        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        qr_code_image = f"data:image/png;base64,{qr_b64}"
    except Exception as e:
        logger.warning(f"QR code generation failed: {e}")
    # ── Context ────────────────────────────────────────────────────────────────
    context = {
        "exam": exam.name,
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
        "qr_code_image": qr_code_image,
    }

    html_string = get_template("pg/admit_card.html").render(context)

    try:
        pdf_file = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        logger.info(f"PG Admit Card PDF generated for {student.registration_no}, size: {len(pdf_file)} bytes")
        return pdf_file
    except Exception as e:
        logger.error(f"PG Admit Card PDF generation failed: {e}")
        return None



def generate_pg_roll_sheet_pdf(exam, college, department=None):
    """
    Generates and returns Exam Roll Sheet PDF for PG.

    When `department` is provided, only that department's roll sheet is produced.
    When `department` is None, ONE PDF is produced containing a page/section
    for EVERY department that has registered students for this exam in this college.
    """
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from pg.models import (
        PGExamRegistration,
        PGExamSchedule,
        PGCommonCourseStructure,
        PGExamCenterMapping,
        PGStudentCourseAssessment,
        PGDepartment,
    )
    from pup_umis_backend.utils.file_utils import image_to_base64
    import os
    import re as _re
    import logging

    logger = logging.getLogger(__name__)

    # ── Semester number variants ─────────────────────────────────────────────
    _roman_str_to_int = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    }
    roman_to_arabic = {k: str(v) for k, v in _roman_str_to_int.items()}
    roman_to_arabic.update({'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15'})
    roman_map_inv = {v: k for k, v in roman_to_arabic.items()}

    ey = str(exam.year) if exam.year else ""
    sem_variants_int = set()

    # 1. From exam.year directly
    if ey.isdigit():
        sem_variants_int.add(int(ey))

    if exam.name:
        # 2. Roman numeral in name: "SEM-III", "SEM III", "SEMESTER-III" → 3
        roman_m = _re.search(
            r'\b(?:SEM|SEMESTER)[-\s]*(I{1,3}|IV|VI{0,3}|IX|X)\b',
            exam.name, _re.IGNORECASE
        )
        if roman_m:
            rn = roman_m.group(1).upper()
            if rn in _roman_str_to_int:
                sem_variants_int.add(_roman_str_to_int[rn])

        # 3. Small digit (1-8) only — avoids picking up years like 2025
        digit_m = _re.search(r'(?<!\d)([1-8])(?!\d)', exam.name)
        if digit_m:
            sem_variants_int.add(int(digit_m.group(1)))

    sem_variants_int = list(sem_variants_int)
    logger.info(f"Roll sheet sem filter: exam.year={exam.year}, name={exam.name}, sem_variants_int={sem_variants_int}")

    # sem_variants: string forms used to filter PGStudentCourseAssessment.semester
    ey_for_str = str(list(sem_variants_int)[0]) if sem_variants_int else ey
    roman_ey = roman_map_inv.get(ey_for_str, "")
    sem_variants = [
        ey_for_str,
        f"{ey_for_str}ST", f"{ey_for_str}ND", f"{ey_for_str}RD", f"{ey_for_str}TH",
        f"Semester-{roman_ey}", f"Semester {roman_ey}",
        f"Semester-{ey_for_str}", f"Semester {ey_for_str}",
        roman_ey,
    ]
    sem_variants = list(set(v.upper() for v in sem_variants if v))

    # Whether exam.session is a real session year-range like "2025-26"
    _is_year_range = bool(_re.match(r'^\d{4}-\d{2,4}$', exam.session or ''))

    def normalize_code(code):
        if not code:
            return ""
        code = code.upper().strip().replace(" ", "-")
        m = _re.match(r'^([A-Z]+)(\d+)$', code)
        if m:
            code = f"{m.group(1)}-{m.group(2)}"
        if "-" in code:
            parts = code.rsplit("-", 1)
            prefix, suffix = parts[0], parts[1]
            if suffix in roman_to_arabic:
                return f"{prefix}-{roman_to_arabic[suffix]}"
            return code
        if code in roman_to_arabic:
            return roman_to_arabic[code]
        return code

    def get_suffix(code):
        nc = normalize_code(code)
        return nc.split("-")[-1] if "-" in nc else nc

    # ── Base registrations ───────────────────────────────────────────────────
    regs_qs = PGExamRegistration.objects.filter(
        student__college=college,
        status='REGISTERED',
    )
    if sem_variants_int:
        if _is_year_range:
            # Exact match: session + sem
            regs_qs = regs_qs.filter(session=exam.session, sem__in=sem_variants_int)
        else:
            # exam.session is not a year-range (e.g. '3RD') — filter only by sem
            regs_qs = regs_qs.filter(sem__in=sem_variants_int)
    else:
        if _is_year_range:
            regs_qs = regs_qs.filter(session=exam.session)
        # else: no reliable filter, return all registered for this college

    if department:
        regs_qs = regs_qs.filter(student__department=department)

    regs_qs = regs_qs.select_related(
        'student', 'student__department', 'student__program', 'student__degree'
    ).order_by('student__roll_no', 'student__registration_no')

    if not regs_qs.exists():
        logger.warning(
            f"[ROLLSHEET] No registrations for exam='{exam.name}' "
            f"session={exam.session} (is_year_range={_is_year_range}), "
            f"sem={sem_variants_int}, college='{college.name}'"
        )
        return None

    # ── Exam center ──────────────────────────────────────────────────────────
    center_name = "-"
    cm = PGExamCenterMapping.objects.filter(exams=exam, attached_colleges=college).first()
    if cm and cm.center:
        center_name = cm.center.name

    # ── All schedules for this exam ──────────────────────────────────────────
    schedules_all = PGExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure', 'group').order_by('exam_date', 'exam_time')

    # ── Controller signature (same path logic as admit card) ─────────────────
    def _find_static_image(filename):
        """Finds a static image the same way generate_pg_admit_card_pdf does."""
        # 1. static/images/common/ (local dev)
        p = os.path.join(settings.BASE_DIR, 'static', 'images', 'common', filename)
        if os.path.exists(p):
            return p
        # 2. static/images/ directly (live server)
        p = os.path.join(settings.BASE_DIR, 'static', 'images', filename)
        if os.path.exists(p):
            return p
        # 3. MEDIA_ROOT/common/
        p = os.path.join(settings.MEDIA_ROOT, 'common', filename)
        if os.path.exists(p):
            return p
        # 4. STATIC_ROOT
        for base in [getattr(settings, 'STATIC_ROOT', '')] + list(getattr(settings, 'STATICFILES_DIRS', [])):
            if base:
                for sub in ['images/common', 'images', 'common', '']:
                    p = os.path.join(base, sub, filename) if sub else os.path.join(base, filename)
                    if os.path.exists(p):
                        return p
        return None

    ctrl_sig_path = _find_static_image("controller-of-examination-signature.png")
    ctrl_sig_b64 = image_to_base64(ctrl_sig_path) if ctrl_sig_path else None
    if not ctrl_sig_b64:
        logger.warning(f"[ROLLSHEET] Signature not found for: controller-of-examination-signature.png")

    # ─────────────────────────────────────────────────────────────────────────
    # Helper: build one roll-sheet section for the given list of registrations
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section(dept_regs, dept_obj):
        """Returns (subjects, student_data, meta_dict) for one department."""
        stu_ids = [r.student_id for r in dept_regs]

        code_to_id = {}
        norm_to_id = {}
        subjects = []
        seen_norms = set()

        if dept_obj is not None:
            # Derive columns from actual ESE assessments of this dept's students.
            # NOTE: do NOT filter by session here — PGExam.session and
            # PGStudentCourseAssessment.session can differ (e.g. 2025-26 vs 2024-25).
            ese_rows = PGStudentCourseAssessment.objects.filter(
                student_id__in=stu_ids,
                label__iregex=r'^ESE',
                semester__in=sem_variants,
            ).values('course_code', 'course_name').distinct()

            for row in ese_rows:
                nc = normalize_code(row['course_code'])
                if nc and nc not in seen_norms:
                    seen_norms.add(nc)
                    subjects.append({'id': nc, 'code': row['course_code'] or '-',
                                     'course_name': row['course_name'] or '-', 'norm_code': nc})
                    code_to_id[(row['course_code'] or '').upper()] = nc
                    norm_to_id[nc] = nc

            # Supplement with dept-specific schedule subjects
            for s in schedules_all.filter(group__department=dept_obj):
                if s.common_course_structure:
                    subj = s.common_course_structure
                    nc = normalize_code(subj.course_code)
                    if nc and nc not in seen_norms:
                        seen_norms.add(nc)
                        subjects.append({'id': nc, 'code': subj.course_code or '-',
                                         'course_name': subj.course_name or '-', 'norm_code': nc})
                        code_to_id[(subj.course_code or '').upper()] = nc
                        norm_to_id[nc] = nc
        else:
            # No specific department: use schedules + common course structure
            for s in schedules_all:
                if s.common_course_structure:
                    subj = s.common_course_structure
                    nc = normalize_code(subj.course_code)
                    if nc not in seen_norms:
                        seen_norms.add(nc)
                        subjects.append({'id': subj.id, 'code': subj.course_code or '-',
                                         'course_name': subj.course_name or '-', 'norm_code': nc})
                        code_to_id[(subj.course_code or '').upper()] = subj.id
                        norm_to_id[nc] = subj.id

            for css in PGCommonCourseStructure.objects.filter(semester__in=sem_variants):
                nc = normalize_code(css.course_code)
                if nc and nc not in seen_norms:
                    seen_norms.add(nc)
                    subjects.append({'id': css.id, 'code': css.course_code or '-',
                                     'course_name': css.course_name or '-', 'norm_code': nc})
                    code_to_id[(css.course_code or '').upper()] = css.id
                    norm_to_id[nc] = css.id

        suffix_map = {get_suffix(s['code']): s['id'] for s in subjects}

        # ── Look up best course name from assessments ─────────────────────
        asmts = PGStudentCourseAssessment.objects.filter(
            student_id__in=stu_ids,
            label__iregex=r'^(ESE|CIA)',
        ).values('student_id', 'course_code', 'course_name', 'label', 'semester', 'session')

        sn = {}   # (student_id, subj_id) -> best display name
        sn_tgt = {}  # same key -> was it from target session/sem?

        for a in asmts:
            raw = a['course_code'] or ""
            nc = normalize_code(raw)
            sid = code_to_id.get(raw.upper()) or norm_to_id.get(nc)
            if not sid:
                sid = suffix_map.get(get_suffix(raw))
            if not sid:
                continue

            cname = (a['course_name'] or "").strip()
            if not cname or cname == "-":
                continue

            key = (a['student_id'], sid)
            is_tgt = (a['semester'] in sem_variants)  # session may differ; use semester only
            cur = sn.get(key)
            better = not cur
            if cur:
                cur_tgt = sn_tgt.get(key, False)
                if is_tgt and not cur_tgt:
                    better = True
                elif is_tgt == cur_tgt:
                    cur_code = normalize_code(cur) == nc
                    new_code = normalize_code(cname) == nc
                    if cur_code and not new_code:
                        better = True
                    elif cur_code == new_code and a['label'].upper().startswith('ESE'):
                        better = True
            if better:
                sn[key] = cname
                sn_tgt[key] = is_tgt

        # ── Sort subjects: normal subjects first, AECC/AEC last ──────────────
        def _sort(s):
            nc = s['norm_code'] or ""
            prefix = nc.split('-')[0] if '-' in nc else nc
            is_aecc = 1 if prefix in ('AECC', 'AEC') else 0
            m = _re.search(r'(\d+)', nc)
            return (is_aecc, int(m.group(1))) if m else (is_aecc, s['code'])
        subjects.sort(key=_sort)

        # ── Student rows ──────────────────────────────────────────────────
        def real_name(name, snorm):
            return bool(name) and name != "-" and normalize_code(name) != snorm

        rows = []
        for reg in dept_regs:
            stu = reg.student
            if reg.exam_type == 'REGULAR':
                stu_sids = [s['id'] for s in subjects]
            else:
                sa = PGStudentCourseAssessment.objects.filter(
                    student=stu, semester__in=sem_variants, label__icontains='ESE'
                )
                if not sa.exists():
                    sa = PGStudentCourseAssessment.objects.filter(
                        student=stu, semester=reg.sem, label__icontains='ESE'
                    )
                stu_sids = []
                for a in sa:
                    ac = (a.course_code or "").upper()
                    sid = code_to_id.get(ac) or norm_to_id.get(normalize_code(ac))
                    if not sid:
                        sid = suffix_map.get(get_suffix(ac))
                    if sid:
                        stu_sids.append(sid)

            row_subjects = []
            for subj in subjects:
                sid = subj['id']
                registered = sid in stu_sids
                display = ""
                if registered:
                    aname = sn.get((stu.id, sid))
                    sname = subj.get('course_name')
                    snorm = subj['norm_code']
                    if real_name(aname, snorm):
                        display = aname
                    elif real_name(sname, snorm):
                        display = sname
                    else:
                        display = subj['code']
                row_subjects.append({'id': sid, 'is_registered': registered, 'display_name': display})

            rows.append({
                'name': stu.get_full_name(),
                'roll_no': stu.roll_no or "-",
                'registration_no': stu.registration_no or "-",
                'row_subjects': row_subjects,
            })

        # ── Meta from first student ───────────────────────────────────────
        disc, degree, syllabus = "-", "Post Graduation", "-"
        inst = dept_obj.name if dept_obj else (college.name or "-")
        first = dept_regs[0] if hasattr(dept_regs, '__getitem__') else next(iter(dept_regs), None)
        if first is None and hasattr(dept_regs, 'first'):
            first = dept_regs.first()
        if first and first.student:
            st = first.student
            if st.program:
                disc = st.program.name
            if st.degree:
                degree = st.degree.name
            if st.json_data and 'syllabus' in st.json_data:
                syllabus = st.json_data['syllabus']

        return subjects, rows, {
            'discipline_name': disc,
            'degree_name': degree,
            'syllabus_year': syllabus,
            'institute_name': inst,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Build per-department sections
    # ─────────────────────────────────────────────────────────────────────────
    dept_sections = []

    if department:
        subjs, rows, meta = _build_section(regs_qs, department)
        if rows:
            dept_sections.append({'department_name': department.name,
                                   'subjects': subjs, 'student_data': rows, **meta})
    else:
        dept_ids = (regs_qs.exclude(student__department__isnull=True)
                    .values_list('student__department_id', flat=True).distinct())
        for dept in PGDepartment.objects.filter(id__in=dept_ids).order_by('name'):
            d_regs = regs_qs.filter(student__department=dept)
            subjs, rows, meta = _build_section(d_regs, dept)
            if rows:
                dept_sections.append({'department_name': dept.name,
                                       'subjects': subjs, 'student_data': rows, **meta})

        no_dept = regs_qs.filter(student__department__isnull=True)
        if no_dept.exists():
            subjs, rows, meta = _build_section(no_dept, None)
            if rows:
                dept_sections.append({'department_name': 'General',
                                       'subjects': subjs, 'student_data': rows, **meta})

    if not dept_sections:
        logger.warning(f"No sections built for Exam: {exam.name}, College: {college.name}")
        return None

    # ── Render & generate PDF ────────────────────────────────────────────────
    context = {
        "exam": exam,
        "college": college,
        "batch_name": exam.batch or "-",
        "session_name": exam.session or "-",
        "college_name": college.name or "-",
        "center_name": center_name,
        "semester": str(exam.year) if exam.year else "-",
        "department_sections": dept_sections,
        "controller_signature": ctrl_sig_b64,
    }

    html_string = get_template("pg/roll_sheet.html").render(context)

    try:
        pdf_file = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        logger.info(f"PG Roll Sheet OK: {college.name}, {len(dept_sections)} dept(s), {len(pdf_file)} bytes")
        return pdf_file
    except Exception as e:
        logger.error(f"PG Roll Sheet PDF generation failed: {e}")
        return None


def generate_pg_attendance_sheet_pdf(exam, college, department=None):
    """
    Generates student-wise PG Attendance Sheet PDF.
    One page per student with: photo, barcode, exam schedule table.
    department: optional PGDepartment — if given, only that dept's students.
    """
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from pg.models import (
        PGExamRegistration,
        PGExamSchedule,
        PGExamCenterMapping,
        PGStudentCourseAssessment,
    )
    from pup_umis_backend.utils.file_utils import image_to_base64, generate_barcode_base64
    import os, re as _re, logging

    logger = logging.getLogger(__name__)

    # ── Semester variants (same logic as roll sheet) ─────────────────────────
    _roman_str_to_int = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    }
    roman_to_arabic = {k: str(v) for k, v in _roman_str_to_int.items()}
    roman_to_arabic.update({'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15'})
    roman_map_inv = {v: k for k, v in roman_to_arabic.items()}

    ey = str(exam.year) if exam.year else ""
    sem_variants_int = set()
    if ey.isdigit():
        sem_variants_int.add(int(ey))
    if exam.name:
        roman_m = _re.search(r'\b(?:SEM|SEMESTER)[-\s]*(I{1,3}|IV|VI{0,3}|IX|X)\b', exam.name, _re.IGNORECASE)
        if roman_m:
            rn = roman_m.group(1).upper()
            if rn in _roman_str_to_int:
                sem_variants_int.add(_roman_str_to_int[rn])
        digit_m = _re.search(r'(?<!\d)([1-8])(?!\d)', exam.name)
        if digit_m:
            sem_variants_int.add(int(digit_m.group(1)))
    sem_variants_int = list(sem_variants_int)

    # sem_variants: text forms used to filter PGStudentCourseAssessment.semester
    ey_for_str = str(sem_variants_int[0]) if sem_variants_int else ey
    roman_ey = roman_map_inv.get(ey_for_str, "")
    sem_variants = [
        ey_for_str,
        f"{ey_for_str}ST", f"{ey_for_str}ND", f"{ey_for_str}RD", f"{ey_for_str}TH",
        f"Semester-{roman_ey}", f"Semester {roman_ey}",
        f"Semester-{ey_for_str}", f"Semester {ey_for_str}",
        roman_ey,
    ]
    sem_variants = list(set(v.upper() for v in sem_variants if v))
    logger.info(f"[ATTENDANCE] sem_variants_int={sem_variants_int}, sem_variants={sem_variants}")

    _is_year_range = bool(_re.match(r'^\d{4}-\d{2,4}$', exam.session or ''))

    # ── Fetch registrations ──────────────────────────────────────────────────
    regs_qs = PGExamRegistration.objects.filter(
        student__college=college,
        status='REGISTERED',
    )
    if sem_variants_int:
        if _is_year_range:
            regs_qs = regs_qs.filter(session=exam.session, sem__in=sem_variants_int)
        else:
            regs_qs = regs_qs.filter(sem__in=sem_variants_int)
    else:
        if _is_year_range:
            regs_qs = regs_qs.filter(session=exam.session)

    if department:
        regs_qs = regs_qs.filter(student__department=department)

    regs_qs = regs_qs.select_related(
        'student', 'student__department', 'student__program'
    ).order_by('student__roll_no', 'student__registration_no')

    regs_list = list(regs_qs)
    if not regs_list:
        dept_info = f" ({department.name})" if department else ""
        logger.warning(f"[ATTENDANCE] No registrations for exam='{exam.name}', college='{college.name}'{dept_info}")
        return None

    # ── Center mapping ───────────────────────────────────────────────────────
    center_name = "-"
    cm = PGExamCenterMapping.objects.filter(exams=exam, attached_colleges=college).first()
    if cm and cm.center:
        center_name = cm.center.name

    # ── All schedules ────────────────────────────────────────────────────────
    all_schedules = PGExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure').order_by('exam_date', 'exam_time')

    # ── Pre-fetch ESE codes for all students in one query (Avoid N+1) ────────
    student_ids = [r.student_id for r in regs_list]
    # Use sem_variants (text list like ['3RD', '3TH', ...]) NOT sem_variants_int (integers)
    # because PGStudentCourseAssessment.semester stores text values like '3RD'
    ese_filter = dict(
        student_id__in=student_ids,
        label__iregex=r'^ESE',
    )
    if sem_variants:
        ese_filter['semester__in'] = sem_variants
    assessments = PGStudentCourseAssessment.objects.filter(**ese_filter).values('student_id', 'course_code')

    student_ese_map = {}
    for a in assessments:
        sid = a['student_id']
        code = (a['course_code'] or "").upper().strip()
        if sid not in student_ese_map:
            student_ese_map[sid] = set()
        if code:
            student_ese_map[sid].add(code)

    # ── University logo ──────────────────────────────────────────────────────
    logo_path = os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")
    university_logo = image_to_base64(logo_path) if os.path.exists(logo_path) else None

    # ── Build per-student attendance data ────────────────────────────────────
    total_regs = len(regs_list)
    logger.info(f"[ATTENDANCE] Processing {total_regs} registrations for {college.name} in batches of 50.")

    # ── Context (Global) ─────────────────────────────────────────────────────
    sem_display = str(sem_variants_int[0]) if sem_variants_int else (exam.session or '-')
    global_context = {
        'university_logo': university_logo,
        'exam_header': f"{exam.name} (Semester {sem_display})",
        'center_name': center_name,
        'batch': exam.batch or '-',
        'session': exam.session or '-',
        'course_name': 'Post Graduation',
        'semester': sem_display,
        'syllabus': exam.batch.split('-')[0] if exam.batch and '-' in exam.batch else '-',
        'college_name': college.name,
    }

    # ── Batch Processing ─────────────────────────────────────────────────────
    BATCH_SIZE = 50
    all_pages = []
    template = get_template('pg/attendance_sheet.html')

    for i in range(0, total_regs, BATCH_SIZE):
        batch_regs = regs_list[i : i + BATCH_SIZE]
        batch_attendance_data = []

        logger.info(f"[ATTENDANCE] Generating batch {i//BATCH_SIZE + 1} ({i} to {min(i+BATCH_SIZE, total_regs)})")

        for reg in batch_regs:
            student = reg.student
            ese_codes_upper = student_ese_map.get(student.id, set())

            # Filter schedules relevant to this student
            student_schedules_raw = []
            for s in all_schedules:
                if not s.common_course_structure:
                    continue
                code = (s.common_course_structure.course_code or "").upper().strip()
                if not code:
                    continue
                # Include if student has this ESE, OR if exam_type is REGULAR (show all)
                if reg.exam_type == 'REGULAR' or code in ese_codes_upper:
                    student_schedules_raw.append(s)

            student_schedules = [
                {
                    'date': s.exam_date.strftime('%d-%m-%Y') if s.exam_date else '-',
                    'exam_time': s.exam_time or '',
                    'sitting': s.sitting or '',
                    'subject_name': s.common_course_structure.course_name or '-',
                    'subject_code': s.common_course_structure.course_code or '-',
                }
                for s in student_schedules_raw
            ]

            # Barcode
            barcode_text = (
                f"Roll:{student.roll_no or ''} "
                f"Reg:{student.registration_no or ''} "
                f"Name:{student.get_full_name()}"
            )
            try:
                barcode_base64 = generate_barcode_base64(barcode_text)
            except Exception:
                barcode_base64 = None

            # Photo
            photo_base64 = None
            if student.profile_image:
                try:
                    photo_base64 = image_to_base64(student.profile_image.path)
                except Exception as e:
                    logger.error(f"Photo error {student.registration_no}: {e}")

            dept_name = student.department.name if student.department else "-"

            batch_attendance_data.append({
                'name': student.get_full_name(),
                'roll_no': student.roll_no or 'N/A',
                'registration_no': student.registration_no or 'N/A',
                'department_name': dept_name,
                'college_name': college.name,
                'photo': photo_base64,
                'barcode': barcode_base64,
                'schedules': student_schedules,
            })

        # Render this batch
        batch_context = global_context.copy()
        batch_context['attendance_data'] = batch_attendance_data
        
        html_string = template.render(batch_context)
        
        try:
            # Render batch to a list of pages
            batch_doc = HTML(string=html_string, base_url=settings.BASE_DIR).render()
            all_pages.extend(batch_doc.pages)
        except Exception as e:
            logger.error(f"[ATTENDANCE] Rendering batch starting at {i} failed: {e}")
            # Continue to next batch or return what we have? 
            # Usually better to fail fast or try to recover?
            # For now, let's keep going if one batch fails, though it's rare.
            continue
        
        # Explicitly clear memory
        del batch_attendance_data
        del html_string
        del batch_doc

    if not all_pages:
        logger.warning(f"[ATTENDANCE] No pages generated for exam='{exam.name}'")
        return None

    try:
        # Merge all pages into final PDF
        # We pick the metadata from the first page's document or a dummy one
        final_doc = all_pages[0]._page_maker.set_metadata(all_pages) if hasattr(all_pages[0], '_page_maker') else None
        
        # WeasyPrint document creation from pages
        # Actually, the standard way is using the first batch's document as a base if possible,
        # but creating a new one from collected pages is safer.
        from weasyprint import Document
        # In newer WeasyPrint versions, you can just do Document(all_pages, doc.metadata, doc.url_fetcher)
        # But we don't have the original doc easily. 
        # Safer: use one doc as a container.
        
        # Re-rendering a small empty doc to get a container
        base_doc = HTML(string="<html></html>").render()
        base_doc.pages = all_pages
        
        pdf_file = base_doc.write_pdf()
        logger.info(f"[ATTENDANCE] Optimized PDF generated: {college.name}, {total_regs} students, {len(pdf_file)} bytes")
        return pdf_file
        
    except Exception as e:
        logger.error(f"[ATTENDANCE] Final PDF assembly failed: {e}")
        return None

