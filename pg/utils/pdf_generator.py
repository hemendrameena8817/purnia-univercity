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


def generate_pg_roll_sheet_pdf(exam, college):
    """
    Generates and returns Exam Roll Sheet PDF for PG.
    """
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from django.db import models
    from django.db.models import Q
    from pg.models import (
        PGExamRegistration,
        PGExamSchedule,
        PGCommonCourseStructure,
        PGExamCenterMapping,
        PGStudentCourseAssessment
    )
    from pup_umis_backend.utils.file_utils import image_to_base64
    import os
    import logging

    logger = logging.getLogger(__name__)

    # 1. Get all students registered for this exam in this college
    # Filter by session only — `sem` field in PGExamRegistration may be NULL or inconsistent.
    ey = str(exam.year) if exam.year else ""
    sem_variants_int = [int(ey)] if ey.isdigit() else []

    # Fetch base queryset
    registrations_qs = PGExamRegistration.objects.filter(
        student__college=college,
        status='REGISTERED'
    )

    # Strict filter: session + sem together (sem is IntegerField, e.g. 3 for Sem 3)
    # NO session-only fallback — that would mix students from different semesters.
    if sem_variants_int:
        registrations = registrations_qs.filter(
            session=exam.session,
            sem__in=sem_variants_int
        )
    else:
        registrations = registrations_qs.filter(session=exam.session)
    
    registrations = registrations.select_related('student', 'student__department', 'student__program').order_by('student__roll_no', 'student__registration_no')

    # Wait, PGExam might have 'name' like "PG 1ST SEMESTER" and 'year' as 1.
    # Let's adjust filters to be more robust or match MCA logic if it matches.
    # Actually, MCARollSheetPDFView passes the 'exam' object.
    
    if not registrations.exists():
        logger.warning(f"No registrations found for Exam: {exam.name}, College: {college.name}")
        return None

    # Get exam center mapping for this college
    center_name = "-"
    center_mapping = PGExamCenterMapping.objects.filter(
        exams=exam,
        attached_colleges=college
    ).first()
    if center_mapping and center_mapping.center:
        center_name = center_mapping.center.name

    # 2. Get the subjects (schedules) for this exam
    # We deduplicate by common_course_structure to avoid multiple columns for the same paper (e.g. if multiple groups share a paper)
    schedules = PGExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure').order_by('exam_date', 'exam_time')

    subjects = []
    all_subject_ids = []
    seen_subject_ids = set()
    # Mapping for Roman to Arabic subject codes (handles both directions via normalization)
    roman_to_arabic = {
        'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5',
        'VI': '6', 'VII': '7', 'VIII': '8', 'IX': '9', 'X': '10',
        'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15'
    }
    roman_map_inv = {v: k for k, v in roman_to_arabic.items()}
    
    def normalize_code(code):
        if not code: return ""
        # Handle spaces and hyphens e.g. "CC I" -> "CC-I"
        code = code.upper().strip().replace(" ", "-")
        
        # Handle cases like "CC1" -> "CC-1" (adding hyphen before number)
        import re
        m = re.match(r'^([A-Z]+)(\d+)$', code)
        if m:
            code = f"{m.group(1)}-{m.group(2)}"
            
        # Handle formats like "CC-I" or "CC-1"
        if "-" in code:
            parts = code.rsplit("-", 1)
            prefix = parts[0]
            suffix = parts[1]
            if suffix in roman_to_arabic:
                return f"{prefix}-{roman_to_arabic[suffix]}"
            return code
        if code in roman_to_arabic:
            return roman_to_arabic[code]
        return code

    # 2. Collect ALL subjects for this strictly matching semester
    from pg.models import PGCommonCourseStructure
    from django.db.models import Q
    
    # Define EXACT matches for the current exam year to ensure zero cross-semester contamination
    ey = str(exam.year) if exam.year else ""
    roman_ey = roman_map_inv.get(ey, "")
    sem_variants = [
        ey, f"{ey}ST", f"{ey}ND", f"{ey}RD", f"{ey}TH", 
        f"Semester-{roman_ey}", f"Semester {roman_ey}",
        f"Semester-{ey}", f"Semester {ey}",
        roman_ey
    ]
    sem_variants = list(set([v.upper() for v in sem_variants if v]))
    
    # We use exact match or case-insensitive exact match to avoid matching '2' with '12'
    all_css = PGCommonCourseStructure.objects.filter(semester__in=sem_variants)
    
    subjects = []
    all_subject_ids = []
    seen_subject_ids = set()
    encountered_norm_codes = set()
    code_to_id = {} 
    normalized_to_id = {}

    # First priority: Subjects in the explicit exam schedules
    for s in schedules:
        if s.common_course_structure:
            subj = s.common_course_structure
            nc = normalize_code(subj.course_code)
            if nc not in encountered_norm_codes:
                subjects.append({
                    'id': subj.id,
                    'code': subj.course_code or "-",
                    'course_name': subj.course_name or "-",
                    'norm_code': nc
                })
                all_subject_ids.append(subj.id)
                seen_subject_ids.add(subj.id)
                encountered_norm_codes.add(nc)
                if subj.course_code:
                    code_to_id[subj.course_code.upper()] = subj.id
                    normalized_to_id[nc] = subj.id

    # Second priority: All other subjects belonging to THIS exact semester curriculum
    for css in all_css:
        nc = normalize_code(css.course_code)
        if nc and nc not in encountered_norm_codes:
            subjects.append({
                'id': css.id,
                'code': css.course_code or "-",
                'course_name': css.course_name or "-",
                'norm_code': nc
            })
            all_subject_ids.append(css.id)
            seen_subject_ids.add(css.id)
            encountered_norm_codes.add(nc)
            if css.course_code:
                code_to_id[css.course_code.upper()] = css.id
                normalized_to_id[nc] = css.id

    # 3. Prepare student data rows
    # Pre-fetch assessments for these students to find descriptive names
    # We broaden this search to ensure we find names even if session/semester formats vary slightly
    all_student_ids = [reg.student.id for reg in registrations]
    assessments_qs = PGStudentCourseAssessment.objects.filter(
        student_id__in=all_student_ids,
        # session=exam.session, # Broaden: names are usually consistent across sessions
        # semester__in=sem_variants, 
        label__iregex=r'^(ESE|CIA)'
    ).values('student_id', 'course_code', 'course_name', 'label', 'semester', 'session')

    # Build map: (student_id, subj_id/dyn_id) -> best name
    student_subject_names = {}
    student_subject_names_is_target = {}
    found_names_for_subject = {} 
    
    # Helper for suffix-based fallback matching
    def get_suffix(code):
        nc = normalize_code(code)
        if "-" in nc:
            return nc.split("-")[-1]
        return nc

    # Cache suffixes for subjects to speed up matching
    subject_suffix_map = {get_suffix(s['code']): s['id'] for s in subjects}

    for a in assessments_qs:
        raw_code = a['course_code'] or ""
        code_upper = raw_code.upper()
        norm_code = normalize_code(raw_code)
        
        # 1. Exact Match (Code or Normalized)
        subj_id = code_to_id.get(code_upper) or normalized_to_id.get(norm_code)
        
        # 2. Fuzzy Match by Suffix (e.g., ECO-V matches CC-V in same semester)
        if not subj_id:
            suffix = get_suffix(raw_code)
            if suffix in subject_suffix_map:
                subj_id = subject_suffix_map[suffix]

        if subj_id:
            key = (a['student_id'], subj_id)
            cname = (a['course_name'] or "").strip()
            
            # Skip if name is just a dash or empty
            if not cname or cname == "-":
                continue
                
            # Check if this assessment is for the TARGET session/semester
            is_target = (a['session'] == exam.session and a['semester'] in sem_variants)
            
            # Prioritize: 
            # 1. Target session/semester assessments
            # 2. Anything that looks like a real name (not a code)
            # 3. ESE over CIA
            current_best = student_subject_names.get(key)
            is_better = not current_best
            
            if current_best:
                curr_target = student_subject_names_is_target.get(key, False)
                if is_target and not curr_target:
                    is_better = True
                elif is_target == curr_target:
                    # If both are target or both NOT target, pick the one that looks more like a name
                    curr_is_code = (normalize_code(current_best) == norm_code)
                    new_is_code = (normalize_code(cname) == norm_code)
                    if curr_is_code and not new_is_code:
                        is_better = True
                    elif curr_is_code == new_is_code:
                        # Fallback to ESE over CIA
                        if a['label'].upper().startswith('ESE'):
                            is_better = True

            if is_better:
                student_subject_names[key] = cname
                student_subject_names_is_target[key] = is_target
                found_names_for_subject[subj_id] = cname

    # Final name refinement: If a subject still doesn't have a descriptive name, look GLOBALLY.
    # This is useful when the current set of students/curriculum have bad data but other students have correct data.
    missing_name_subjects = [s for s in subjects if not s.get('has_name')]
    if missing_name_subjects:
        codes_to_check = [s['code'] for s in missing_name_subjects]
        norm_codes_to_check = [s['norm_code'] for s in missing_name_subjects]
        
        # Look for any assessment with a name that isn't just the code
        # We search by both raw code and normalized code
        global_names_qs = PGStudentCourseAssessment.objects.filter(
            Q(course_code__in=codes_to_check) | Q(course_code__in=norm_codes_to_check)
        ).exclude(
            course_name=models.F('course_code')
        ).exclude(
            course_name__isnull=True
        ).exclude(
            course_name='-'
        ).exclude(
            course_name=''
        ).values('course_code', 'course_name')
        
        global_name_map = {}
        for gn in global_names_qs:
            nc = normalize_code(gn['course_code'])
            gn_name = gn['course_name'].strip()
            # Double check it's not a code
            if normalize_code(gn_name) != nc:
                global_name_map[nc] = gn_name

        for subj in missing_name_subjects:
            nc = subj['norm_code']
            if nc in global_name_map:
                subj['course_name'] = global_name_map[nc]
                subj['has_name'] = True
                found_names_for_subject[subj['id']] = global_name_map[nc]

    # Sort subjects by code (numeric part if possible)
    import re
    def get_sort_key(s):
        m = re.search(r'(\d+)', s['norm_code'] or "")
        return (0, int(m.group(1))) if m else (1, s['code'])
    
    subjects.sort(key=get_sort_key)
    # Re-calculate all_subject_ids order after sort
    all_subject_ids = [s['id'] for s in subjects]

    student_data = []
    for reg in registrations:
        student = reg.student
        
        # Determine subjects student is registered for
        if reg.exam_type == 'REGULAR':
            student_subject_ids = all_subject_ids
        else:
            # For BACKLOG/IMPROVEMENT, get specific subjects from assessments
            # We look for assessments that match the SEMESTER of this exam (sem_variants)
            # This handles cases where a student is registered for Sem 3 but taking a Sem 2 BACK exam.
            student_assessments = PGStudentCourseAssessment.objects.filter(
                student=student,
                semester__in=sem_variants,
                label__icontains='ESE'
            )
            
            # If nothing found for EXAM_SEM, fall back to the registration's semester (just in case)
            if not student_assessments.exists():
                student_assessments = PGStudentCourseAssessment.objects.filter(
                    student=student,
                    semester=reg.sem,
                    label__icontains='ESE'
                )

            # Match assessments to subject IDs via fuzzy matching if exact code fails
            student_subject_ids = []
            for a in student_assessments:
                acode = (a.course_code or "").upper()
                sid = code_to_id.get(acode) or normalized_to_id.get(normalize_code(acode))
                if not sid:
                    suffix = get_suffix(acode)
                    if suffix in subject_suffix_map:
                        sid = subject_suffix_map[suffix]
                if sid:
                    student_subject_ids.append(sid)

        # Build a list of info for each subject column
        row_subjects = []
        for subj in subjects:
            subj_id = subj['id']
            is_registered = subj_id in student_subject_ids
            display_name = ""
            if is_registered:
                # Priority for display_name in cell:
                # 1. Assessment Name for this student (if it's a real name)
                # 2. Subject Name from curriculum/global search (if it's a real name)
                # 3. Code (last resort)
                
                assessment_name = student_subject_names.get((student.id, subj_id))
                subject_name = subj.get('course_name')
                subj_code = subj['code']
                subj_norm = subj['norm_code']
                
                # Helper: is it a real name or just a code?
                def is_real_name(name, norm_code):
                    if not name or name == "-" or name == "": return False
                    return normalize_code(name) != norm_code

                if is_real_name(assessment_name, subj_norm):
                    display_name = assessment_name
                elif is_real_name(subject_name, subj_norm):
                    display_name = subject_name
                else:
                    display_name = subj_code
            
            row_subjects.append({
                'id': subj_id,
                'is_registered': is_registered,
                'display_name': display_name
            })

        student_data.append({
            'name': student.get_full_name(),
            'roll_no': student.roll_no or "-",
            'registration_no': student.registration_no or "-",
            'row_subjects': row_subjects
        })

    # Load controller signature (using existing helper logic from generate_pg_admit_card_pdf if possible)
    # Since I'm inside the file, I can't easily call the inner helper, I'll just use the path.
    controller_sig_path = os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")
    if not os.path.exists(controller_sig_path):
        # try static fallback
        controller_sig_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'common', 'controller-of-examination-signature.png')

    # 4. Prepare Context
    # Try to resolve extra info from the first student's profile if available
    discipline_name = "-"
    degree_name = "Post Graduation"
    syllabus_year = "-"
    institute_name = college.name or "-"
    
    first_reg = registrations.first()
    if first_reg and first_reg.student:
        student = first_reg.student
        if student.program:
            discipline_name = student.program.name
        if student.degree:
            degree_name = student.degree.name
        if student.department:
            institute_name = student.department.name
        # Try to find syllabus from json_data or just use a default?
        # In the image it says Syllabus: 2020. I'll check if it's in registration or exam.
        if student.json_data and 'syllabus' in student.json_data:
            syllabus_year = student.json_data['syllabus']

    context = {
        "exam": exam,
        "college": college,
        "course_name": degree_name,
        "discipline_name": discipline_name,
        "syllabus_year": syllabus_year,
        "batch_name": exam.batch or "-",
        "session_name": exam.session or "-",
        "college_name": college.name or "-",
        "institute_name": institute_name,
        "center_name": center_name,
        "semester": f"{exam.year}" if exam.year else "-",
        "subjects": subjects,
        "student_data": student_data,
        "controller_signature": image_to_base64(controller_sig_path) if os.path.exists(controller_sig_path) else None,
    }

    # Render HTML template
    html_string = get_template("pg/roll_sheet.html").render(context)

    try:
        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        return pdf_file
    except Exception as e:
        logger.error(f"PG Roll Sheet PDF generation failed: {str(e)}")
        return None
