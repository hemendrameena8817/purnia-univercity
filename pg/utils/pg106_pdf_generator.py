"""
PG106 specific PDF generators (attendance sheet + roll sheet).

These are dedicated versions of the generic generators that:
 - Accept `allowed_student_ids`  → only those students are included.
 - Accept `allowed_css_ids`      → only those PGCommonCourseStructure IDs
                                   are shown in the schedule / columns.

Same templates as the generic ones:
  pg/attendance_sheet.html
  pg/roll_sheet.html
"""
import re as _re
import logging

logger = logging.getLogger(__name__)

_roman_str_to_int = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
}
roman_to_arabic = {k: str(v) for k, v in _roman_str_to_int.items()}
roman_to_arabic.update({'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15'})
roman_map_inv = {v: k for k, v in roman_to_arabic.items()}


def _sem_variants_from_exam(exam):
    ey = str(exam.year) if exam.year else ""
    sem_ints = set()
    if ey.isdigit():
        sem_ints.add(int(ey))
    if exam.name:
        m = _re.search(r'\b(?:SEM|SEMESTER)[-\s]*(I{1,3}|IV|VI{0,3}|IX|X)\b', exam.name, _re.IGNORECASE)
        if m:
            rn = m.group(1).upper()
            if rn in _roman_str_to_int:
                sem_ints.add(_roman_str_to_int[rn])
        d = _re.search(r'(?<!\d)([1-8])(?!\d)', exam.name)
        if d:
            sem_ints.add(int(d.group(1)))
    variants = set()
    for s_int in sem_ints:
        s_str = str(s_int)
        roman_s = roman_map_inv.get(s_str, "")
        for v in [s_str, roman_s,
                  f"SEM-{s_str}", f"SEM {s_str}",
                  f"SEMESTER-{s_str}", f"SEMESTER {s_str}",
                  f"SEM-{roman_s}", f"SEM {roman_s}",
                  f"SEMESTER-{roman_s}", f"SEMESTER {roman_s}"]:
            if v:
                variants.add(v.upper())
        if s_str == '3':
            for suffix in ['3RD', 'THIRD']:
                variants.update([suffix, f"SEM-{suffix}", f"SEM {suffix}",
                                  f"SEMESTER-{suffix}", f"SEMESTER {suffix}"])
    return list(sem_ints), list(variants)


def _roman_to_int(roman):
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    res = 0
    for i in range(len(roman)):
        if i > 0 and roman_map.get(roman[i], 0) > roman_map.get(roman[i - 1], 0):
            res += roman_map.get(roman[i], 0) - 2 * roman_map.get(roman[i - 1], 0)
        else:
            res += roman_map.get(roman[i], 0)
    return res


# ─────────────────────────────────────────────────────────────────────────────
# Attendance Sheet
# ─────────────────────────────────────────────────────────────────────────────

def generate_pg106_attendance_sheet_pdf(
    exam, college, department=None, registration_no=None,
    allowed_student_ids=None, allowed_css_ids=None
):
    """
    PG106 Attendance Sheet — same template as generate_pg_attendance_sheet_pdf
    but schedules are restricted to `allowed_css_ids` (null-date subjects only).
    """
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from django.utils import timezone
    from pg.models import (
        PGExamRegistration, PGExamSchedule,
        PGExamCenterMapping, PGStudentCourseAssessment,
    )
    from pup_umis_backend.utils.file_utils import image_to_base64, generate_barcode_base64
    import os, gc, time

    sem_ints, sem_variants = _sem_variants_from_exam(exam)
    _is_year_range = bool(_re.match(r'^\d{4}-\d{2,4}$', exam.session or ''))

    # ── Registrations ────────────────────────────────────────────────────────
    regs_qs = PGExamRegistration.objects.filter(
        exam=exam, student__college=college, status='REGISTERED',
    )
    if sem_ints:
        regs_qs = regs_qs.filter(sem__in=sem_ints)
    elif _is_year_range:
        regs_qs = regs_qs.filter(session=exam.session)
    if department:
        regs_qs = regs_qs.filter(student__department=department)
    if registration_no:
        regs_qs = regs_qs.filter(student__registration_no=registration_no)
    if allowed_student_ids is not None:
        regs_qs = regs_qs.filter(student_id__in=allowed_student_ids)

    regs_qs = regs_qs.select_related(
        'student', 'student__department', 'student__program'
    ).order_by('student__roll_no', 'student__registration_no')
    regs_list = list(regs_qs)

    if not regs_list:
        logger.warning(f"[PG106-ATT] No registrations: exam={exam.name}, college={college.name}")
        return None

    # ── Center ───────────────────────────────────────────────────────────────
    center_name = "-"
    cm = PGExamCenterMapping.objects.filter(exams=exam, attached_colleges=college).first()
    if cm and cm.center:
        center_name = cm.center.name

    # ── Schedules (null-date only, restricted to allowed_css_ids) ─────────────
    sched_qs = PGExamSchedule.objects.filter(exam=exam, exam_date__isnull=True)
    if allowed_css_ids is not None:
        sched_qs = sched_qs.filter(common_course_structure_id__in=allowed_css_ids)
    all_schedules = list(
        sched_qs.select_related('common_course_structure', 'group')
        .prefetch_related('group__department')
        .order_by('exam_time')
    )

    # ── Pre-build schedule lookup ────────────────────────────────────────────
    code_to_schedules = {}
    schedule_id_to_dept_ids = {}
    for s in all_schedules:
        if s.common_course_structure:
            code = (s.common_course_structure.course_code or "").upper().strip()
            if code:
                code_to_schedules.setdefault(code, []).append(s)
        schedule_id_to_dept_ids[s.id] = (
            set(s.group.department.values_list('id', flat=True)) if s.group else set()
        )

    # ── ESE assessment map ───────────────────────────────────────────────────
    student_ids = [r.student_id for r in regs_list]
    distinct_sessions = list(set(r.session for r in regs_list if r.session)) or (
        [exam.session] if exam.session else []
    )
    distinct_sems = list(set(r.sem for r in regs_list if r.sem is not None))
    d_sem_variants = set()
    for s_int in distinct_sems:
        s_str = str(s_int)
        roman_s = roman_map_inv.get(s_str, "")
        for v in [s_str, roman_s,
                  f"SEM-{s_str}", f"SEM {s_str}",
                  f"SEMESTER-{s_str}", f"SEMESTER {s_str}",
                  f"SEM-{roman_s}", f"SEM {roman_s}",
                  f"SEMESTER-{roman_s}", f"SEMESTER {roman_s}"]:
            if v:
                d_sem_variants.add(v.upper())

    ese_filter = dict(
        student_id__in=student_ids,
        label__iregex=r'^ESE',
        session__in=distinct_sessions,
    )
    if d_sem_variants:
        ese_filter['semester__in'] = list(d_sem_variants)
    elif sem_variants:
        ese_filter['semester__in'] = sem_variants

    assessments = PGStudentCourseAssessment.objects.filter(**ese_filter).values(
        'student_id', 'course_code', 'course_name'
    )
    student_ese_map = {}
    for a in assessments:
        sid = a['student_id']
        code = (a['course_code'] or "").upper().strip()
        name = a['course_name'] or ""
        if sid not in student_ese_map:
            student_ese_map[sid] = {}
        if code:
            student_ese_map[sid][code] = name

    # ── Logo ─────────────────────────────────────────────────────────────────
    def _find_logo():
        for p in [
            os.path.join(settings.BASE_DIR, "static", "images", "common", "purnea-logo.png"),
            os.path.join(settings.BASE_DIR, "static", "images", "purnea-logo.png"),
            os.path.join(settings.MEDIA_ROOT, "common", "purnea-logo.png"),
        ]:
            if os.path.exists(p):
                return image_to_base64(p)
        return None

    university_logo = _find_logo()
    sem_display = str(sem_ints[0]) if sem_ints else (exam.session or '-')

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

    # ── Photo helper ─────────────────────────────────────────────────────────
    def _photo_b64(image_field):
        if not image_field:
            return None
        try:
            from PIL import Image
            import io, base64
            with image_field.open('rb') as f:
                img = Image.open(f)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if img.width > 150:
                    ratio = 150 / float(img.width)
                    img = img.resize((150, int(img.height * ratio)), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=75)
                return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception:
            try:
                return image_to_base64(image_field.path)
            except Exception:
                return None

    # ── Batch render ─────────────────────────────────────────────────────────
    BATCH_SIZE = 20
    all_pages = []
    template = get_template('pg/attendance_sheet.html')
    total_regs = len(regs_list)

    for i in range(0, total_regs, BATCH_SIZE):
        batch_regs = regs_list[i: i + BATCH_SIZE]
        batch_data = []

        for reg in batch_regs:
            student = reg.student
            paper_names = student_ese_map.get(student.id, {})
            ese_codes = set(paper_names.keys())
            dept_id = student.department_id

            # Filter schedules relevant to this student
            raw_schedules = []
            for code in ese_codes:
                for s in code_to_schedules.get(code, []):
                    dept_ids = schedule_id_to_dept_ids.get(s.id, set())
                    if (not dept_ids or dept_id in dept_ids) and s not in raw_schedules:
                        raw_schedules.append(s)

            # If no match via ESE codes, show all allowed schedules for the dept
            if not raw_schedules:
                for s in all_schedules:
                    dept_ids = schedule_id_to_dept_ids.get(s.id, set())
                    if not dept_ids or dept_id in dept_ids:
                        raw_schedules.append(s)

            def _sort_key(s):
                code = (s.common_course_structure.course_code or "").upper()
                is_aecc = 1 if "AECC" in code else 0
                roman_part = code.split('-')[-1] if '-' in code else ""
                roman_val = _roman_to_int(roman_part) if roman_part else 0
                return (is_aecc, roman_val, s.exam_date or timezone.now().date())

            raw_schedules.sort(key=_sort_key)

            student_schedules = []
            for s in raw_schedules:
                code_upper = (s.common_course_structure.course_code or "").upper().strip()
                name = paper_names.get(code_upper) or s.common_course_structure.course_name or '-'
                student_schedules.append({
                    'date': s.exam_date.strftime('%d-%m-%Y') if s.exam_date else '-',
                    'exam_time': s.exam_time or '',
                    'sitting': s.sitting or '',
                    'subject_name': name,
                    'subject_code': s.common_course_structure.course_code or '-',
                })

            barcode_text = (
                f"Roll:{student.roll_no or ''} "
                f"Reg:{student.registration_no or ''} "
                f"Name:{student.get_full_name()}"
            )
            try:
                barcode_b64 = generate_barcode_base64(barcode_text)
            except Exception:
                barcode_b64 = None

            batch_data.append({
                'name': student.get_full_name(),
                'roll_no': student.roll_no or 'N/A',
                'registration_no': student.registration_no or 'N/A',
                'department_name': student.department.name if student.department else '-',
                'college_name': college.name,
                'photo': _photo_b64(student.profile_image),
                'barcode': barcode_b64,
                'schedules': student_schedules,
            })

        ctx = global_context.copy()
        ctx['attendance_data'] = batch_data
        html_string = template.render(ctx)

        try:
            batch_doc = HTML(string=html_string, base_url=settings.BASE_DIR).render()
            all_pages.extend(batch_doc.pages)
        except Exception as e:
            logger.error(f"[PG106-ATT] Batch {i} render failed: {e}")
            continue

        del batch_data, html_string, batch_doc
        gc.collect()

    if not all_pages:
        logger.warning(f"[PG106-ATT] No pages generated for {exam.name}, {college.name}")
        return None

    try:
        base_doc = HTML(string="<html></html>").render()
        base_doc.pages = all_pages
        pdf = base_doc.write_pdf()
        logger.info(f"[PG106-ATT] PDF OK: {college.name}, {total_regs} students, {len(pdf)} bytes")
        return pdf
    except Exception as e:
        logger.error(f"[PG106-ATT] Final PDF assembly failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Roll Sheet
# ─────────────────────────────────────────────────────────────────────────────

def generate_pg106_roll_sheet_pdf(
    exam, college, department=None, registration_no=None,
    allowed_student_ids=None, allowed_css_ids=None
):
    """
    PG106 Roll Sheet — same template as generate_pg_roll_sheet_pdf
    but schedules/subjects are restricted to `allowed_css_ids`.
    """
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from pg.models import (
        PGExamRegistration, PGExamSchedule,
        PGExamCenterMapping, PGStudentCourseAssessment,
        PGCommonCourseStructure, PGDepartment,
    )
    from pup_umis_backend.utils.file_utils import image_to_base64
    import os

    sem_ints, sem_variants = _sem_variants_from_exam(exam)
    _is_year_range = bool(_re.match(r'^\d{4}-\d{2,4}$', exam.session or ''))

    def normalize_code(c):
        return _re.sub(r'[\s\-]', '', (c or "")).upper()

    def get_suffix(c):
        parts = (c or "").upper().split('-')
        return parts[-1] if len(parts) > 1 else ""

    # ── Registrations ────────────────────────────────────────────────────────
    regs_qs = PGExamRegistration.objects.filter(
        exam=exam, student__college=college, status='REGISTERED',
    )
    if sem_ints:
        regs_qs = regs_qs.filter(sem__in=sem_ints)
    elif _is_year_range:
        regs_qs = regs_qs.filter(session=exam.session)
    if department:
        regs_qs = regs_qs.filter(student__department=department)
    if registration_no:
        regs_qs = regs_qs.filter(student__registration_no=registration_no)
    if allowed_student_ids is not None:
        regs_qs = regs_qs.filter(student_id__in=allowed_student_ids)

    regs_qs = regs_qs.select_related(
        'student', 'student__department', 'student__program', 'student__degree'
    ).order_by('student__roll_no', 'student__registration_no')

    if not regs_qs.exists():
        logger.warning(f"[PG106-ROLL] No registrations: exam={exam.name}, college={college.name}")
        return None

    # ── Center ───────────────────────────────────────────────────────────────
    center_name = "-"
    cm = PGExamCenterMapping.objects.filter(exams=exam, attached_colleges=college).first()
    if cm and cm.center:
        center_name = cm.center.name

    # ── Schedules (null-date only, restricted to allowed_css_ids) ─────────────
    sched_qs = PGExamSchedule.objects.filter(exam=exam, exam_date__isnull=True)
    if allowed_css_ids is not None:
        sched_qs = sched_qs.filter(common_course_structure_id__in=allowed_css_ids)
    schedules_all = sched_qs.select_related('common_course_structure', 'group').order_by('exam_time')

    # ── Controller signature ─────────────────────────────────────────────────
    def _find_static(filename):
        for base in [
            os.path.join(settings.BASE_DIR, 'static', 'images', 'common'),
            os.path.join(settings.BASE_DIR, 'static', 'images'),
            os.path.join(getattr(settings, 'STATIC_ROOT', ''), 'images', 'common'),
        ]:
            p = os.path.join(base, filename)
            if os.path.exists(p):
                return p
        return None

    ctrl_sig_path = _find_static("controller-of-examination-signature.png")
    ctrl_sig_b64 = image_to_base64(ctrl_sig_path) if ctrl_sig_path else None

    # ── Build section per department ─────────────────────────────────────────
    def _build_section(dept_regs, dept_obj):
        stu_ids = [r.student_id for r in dept_regs]
        dept_sessions = list(set(r.session for r in dept_regs if r.session)) or (
            [exam.session] if exam.session else []
        )
        dept_sems = list(set(r.sem for r in dept_regs if r.sem is not None))
        dept_sem_variants = set()
        for s_int in dept_sems:
            s_str = str(s_int)
            roman_s = roman_map_inv.get(s_str, "")
            for v in [s_str, roman_s,
                      f"SEM-{s_str}", f"SEM {s_str}",
                      f"SEMESTER-{s_str}", f"SEMESTER {s_str}",
                      f"SEM-{roman_s}", f"SEM {roman_s}",
                      f"SEMESTER-{roman_s}", f"SEMESTER {roman_s}"]:
                if v:
                    dept_sem_variants.add(v.upper())

        code_to_id = {}
        norm_to_id = {}
        subjects = []
        seen_norms = set()

        # Columns from ESE assessments
        ese_rows = PGStudentCourseAssessment.objects.filter(
            student_id__in=stu_ids,
            label__iregex=r'^ESE',
            semester__in=list(dept_sem_variants) if dept_sem_variants else sem_variants,
            session__in=dept_sessions,
        ).values('course_code', 'course_name').distinct()

        for row in ese_rows:
            nc = normalize_code(row['course_code'])
            if nc and nc not in seen_norms:
                seen_norms.add(nc)
                subjects.append({'id': nc, 'code': row['course_code'] or '-',
                                  'course_name': row['course_name'] or '-', 'norm_code': nc})
                code_to_id[(row['course_code'] or '').upper()] = nc
                norm_to_id[nc] = nc

        # Supplement from schedules (restricted to allowed_css_ids already)
        sched_filter = schedules_all.filter(group__department=dept_obj) if dept_obj else schedules_all
        for s in sched_filter:
            if s.common_course_structure:
                subj = s.common_course_structure
                nc = normalize_code(subj.course_code)
                if nc and nc not in seen_norms:
                    seen_norms.add(nc)
                    subjects.append({'id': nc, 'code': subj.course_code or '-',
                                     'course_name': subj.course_name or '-', 'norm_code': nc})
                    code_to_id[(subj.course_code or '').upper()] = nc
                    norm_to_id[nc] = nc

        # Sort: normal first, AECC last
        def _sort(s):
            nc = s['norm_code'] or ""
            prefix = nc.split('-')[0] if '-' in nc else nc
            is_aecc = 1 if prefix in ('AECC', 'AEC') else 0
            m = _re.search(r'(\d+)', nc)
            return (is_aecc, int(m.group(1))) if m else (is_aecc, s['code'])
        subjects.sort(key=_sort)

        suffix_map = {get_suffix(s['code']): s['id'] for s in subjects}

        # Assessment name lookup
        asmts = PGStudentCourseAssessment.objects.filter(
            student_id__in=stu_ids,
            label__iregex=r'^(ESE|CIA)',
            session__in=dept_sessions,
            semester__in=list(dept_sem_variants) if dept_sem_variants else sem_variants,
        ).values('student_id', 'course_code', 'course_name', 'label', 'semester')

        sn = {}
        for a in asmts:
            raw = a['course_code'] or ""
            nc = normalize_code(raw)
            sid = code_to_id.get(raw.upper()) or norm_to_id.get(nc) or suffix_map.get(get_suffix(raw))
            if not sid:
                continue
            cname = (a['course_name'] or "").strip()
            if not cname or cname == "-":
                continue
            key = (a['student_id'], sid)
            if key not in sn or a['label'].upper().startswith('ESE'):
                sn[key] = cname

        # Student rows
        rows = []
        for reg in dept_regs:
            stu = reg.student
            stu_sem_variants = set()
            if reg.sem:
                s_int = reg.sem
                s_str = str(s_int)
                roman_s = roman_map_inv.get(s_str, "")
                for v in [s_str, roman_s,
                           f"SEM-{s_str}", f"SEM {s_str}",
                           f"SEMESTER-{s_str}", f"SEMESTER {s_str}",
                           f"SEM-{roman_s}", f"SEM {roman_s}",
                           f"SEMESTER-{roman_s}", f"SEMESTER {roman_s}"]:
                    if v:
                        stu_sem_variants.add(v.upper())

            sa = PGStudentCourseAssessment.objects.filter(
                student=stu,
                semester__in=list(stu_sem_variants) if stu_sem_variants else sem_variants,
                label__icontains='ESE',
                session=reg.session if reg.session else exam.session,
            )
            stu_sids = []
            for a in sa:
                ac = (a.course_code or "").upper()
                sid = code_to_id.get(ac) or norm_to_id.get(normalize_code(ac)) or suffix_map.get(get_suffix(ac))
                if sid:
                    stu_sids.append(sid)

            row_subjects = []
            for subj in subjects:
                registered = subj['id'] in stu_sids
                display = ""
                if registered:
                    aname = sn.get((stu.id, subj['id']))
                    sname = subj.get('course_name')
                    snorm = subj['norm_code']
                    if aname and aname != "-" and normalize_code(aname) != snorm:
                        display = aname
                    elif sname and sname != "-" and normalize_code(sname) != snorm:
                        display = sname
                    else:
                        display = subj['code']
                row_subjects.append({'id': subj['id'], 'is_registered': registered, 'display_name': display})

            rows.append({
                'name': stu.get_full_name(),
                'roll_no': stu.roll_no or "-",
                'registration_no': stu.registration_no or "-",
                'row_subjects': row_subjects,
            })

        disc, degree, syllabus = "-", "Post Graduation", "-"
        inst = dept_obj.name if dept_obj else (college.name or "-")
        first = dept_regs[0] if dept_regs else None
        if first and first.student:
            st = first.student
            if st.program:
                disc = st.program.name
            if st.degree:
                degree = st.degree.name

        return subjects, rows, {
            'discipline_name': disc,
            'degree_name': degree,
            'syllabus_year': syllabus,
            'institute_name': inst,
        }

    # ── Build sections ────────────────────────────────────────────────────────
    dept_sections = []

    if department:
        subjs, rows, meta = _build_section(list(regs_qs), department)
        if rows:
            dept_sections.append({'department_name': department.name,
                                   'subjects': subjs, 'student_data': rows, **meta})
    else:
        dept_ids = (regs_qs.exclude(student__department__isnull=True)
                    .values_list('student__department_id', flat=True).distinct())
        for dept in PGDepartment.objects.filter(id__in=dept_ids).order_by('name'):
            d_regs = list(regs_qs.filter(student__department=dept))
            subjs, rows, meta = _build_section(d_regs, dept)
            if rows:
                dept_sections.append({'department_name': dept.name,
                                       'subjects': subjs, 'student_data': rows, **meta})
        no_dept = list(regs_qs.filter(student__department__isnull=True))
        if no_dept:
            subjs, rows, meta = _build_section(no_dept, None)
            if rows:
                dept_sections.append({'department_name': 'General',
                                       'subjects': subjs, 'student_data': rows, **meta})

    if not dept_sections:
        logger.warning(f"[PG106-ROLL] No sections: exam={exam.name}, college={college.name}")
        return None

    context = {
        "exam": exam,
        "college": college,
        "batch_name": exam.batch or "-",
        "session_name": exam.session or "-",
        "college_name": college.name or "-",
        "center_name": center_name,
        "semester": str(sem_ints[0]) if sem_ints else "-",
        "department_sections": dept_sections,
        "controller_signature": ctrl_sig_b64,
    }

    html_string = get_template("pg/roll_sheet.html").render(context)

    try:
        pdf = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        logger.info(f"[PG106-ROLL] PDF OK: {college.name}, {len(dept_sections)} dept(s), {len(pdf)} bytes")
        return pdf
    except Exception as e:
        logger.error(f"[PG106-ROLL] PDF generation failed: {e}")
        return None
