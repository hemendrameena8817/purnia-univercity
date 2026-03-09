import base64
import os
from io import BytesIO

from django.conf import settings
from django.template.loader import render_to_string

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _get_base64_image(image_field_or_path):
    """
    Convert a Django ImageField, filesystem path, or HTTP URL to a base64
    data-URI suitable for embedding directly in HTML.
    """
    if not image_field_or_path:
        return None

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
            # Best-effort without Pillow
            mime = 'image/png'

        b64 = base64.b64encode(raw).decode('utf-8')
        return f"data:{mime};base64,{b64}"

    except Exception as e:
        print(f"[UG Exam RegCard] Image encode error: {e}")
        return None


def _load_static_image(relative_path):
    """
    Load an image from static/images/common (shared across UG/PG).
    Falls back to ug/static/ug/images/ for official signatures.
    """
    # 1. Try common static path
    common_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'common', relative_path)
    if os.path.exists(common_path):
        return _get_base64_image(common_path)

    # 2. Try UG static (for shared signatures)
    ug_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images', relative_path)
    if os.path.exists(ug_path):
        return _get_base64_image(ug_path)

    return None


def _semester_text(sem_value):
    """Return e.g. '3RD' → '3rd', or int 3 → '3RD'."""
    if isinstance(sem_value, int):
        suffixes = {1: 'ST', 2: 'ND', 3: 'RD'}
        suffix = suffixes.get(sem_value, 'TH')
        return f"{sem_value}{suffix}"
    # Already a string like '3RD', '1ST'
    return str(sem_value).upper()


def generate_ug_exam_registration_card_pdf(student, registration):
    """
    Generate a UG Exam Registration Card PDF.

    Args:
        student    : UGStudentProfile instance
        registration: ExamRegistration instance

    Returns:
        BytesIO buffer containing the PDF bytes.
    """
    from weasyprint import HTML

    # ── Logo ─────────────────────────────────────────────────────────────────
    logo_src = _load_static_image('purnea-logo.png')

    # ── Student photo + signature ─────────────────────────────────────────────
    profile_image_src = _get_base64_image(student.profile_image) if student.profile_image else None
    signature_src = _get_base64_image(student.signature) if student.signature else None

    # ── Semester text ─────────────────────────────────────────────────────────
    sem_val = registration.sem
    if isinstance(sem_val, str):
        semester_text = sem_val.upper()
    else:
        semester_text = _semester_text(sem_val)

    # ── Session ───────────────────────────────────────────────────────────────
    session = registration.session or ''

    # ── Exam type ─────────────────────────────────────────────────────────────
    exam_type = (registration.exam_type or 'REGULAR').upper()

    # ── College & Department ──────────────────────────────────────────────────
    college_name    = student.college.name    if hasattr(student, 'college') and student.college else (student.user.college.name if student.user.college else '-')
    department_name = student.department.name if student.department else '-'

    # ── Papers enrolled ────────────────
    from ug.models import StudentCourseAssessment

    assessments = (
        StudentCourseAssessment.objects
        .filter(
            student=student,
            semester=semester_text,
            session=session,
            exam_type=exam_type,
        )
        .select_related('department')
        .order_by('course_type', 'paper_code')
    )

    # Deduplicate by paper_code
    seen = set()
    papers = []
    for a in assessments:
        key = a.paper_code or a.course_code or ''
        if key and key not in seen:
            seen.add(key)
            papers.append({
                'code': a.paper_code or '-',
                'course': a.course_code or a.course_type or '-', 
                'name': a.course_name or '-',
            })

    # ── Context ───────────────────────────────────────────────────────────────
    context = {
        'student': {
            'registration_no':  student.registration_no,
            'full_name':        (student.first_name if student.first_name else f"{student.first_name or ''} {student.last_name or ''}".strip()) or "Unknown",
            'father_name':      student.father_name or '-',
            'mother_name':      student.mother_name or '-',
            'gender':           (student.gender or '-').capitalize(),
            'profile_image_url': profile_image_src,
            'signature_url':     signature_src,
            'roll_no': student.roll_no,
            'batch': student.batch.name if hasattr(student, 'batch') and student.batch else '-',
            'caste': student.caste,
            'religion': student.religion,
        },
        'logo_url':        logo_src,
        'college_name':    college_name,
        'department_name': department_name,
        'semester_text':   semester_text,
        'session':         session,
        'batch':           student.batch.name if hasattr(student, 'batch') and student.batch else '-',
        'exam_type':       exam_type,
        'papers':          papers,
    }

    # ── Render + PDF ──────────────────────────────────────────────────────────
    html_string = render_to_string('ug/exam_registration_card.html', context)
    buffer = BytesIO()
    HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf(target=buffer)
    buffer.seek(0)
    return buffer
