from io import BytesIO
import os
import base64
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from django.db.models import Q
from collections import OrderedDict
from ..models import (
    UGStudentProfile, ExamRegistration, StudentCourseAssessment, 
    UGExamCenterMapping, UGExamSchedule, CourseStructure
)

def wordwrap_br(text, words_per_line=4):
    """Split a long string into chunks of N words joined by <br>."""
    if not text: return ""
    words = text.split()
    lines = []
    for i in range(0, len(words), words_per_line):
        lines.append(" ".join(words[i:i + words_per_line]))
    return "<br>".join(lines)

def get_sem_integer(sem_str):
    """Helper to convert 'Semester-I', '1st', or '1' to integer 1."""
    if not sem_str: return None
    sem_str = str(sem_str).strip().upper()
    
    # 1. Check if it's already a digit
    if sem_str.isdigit(): return int(sem_str)
    
    # 2. Handle '1ST', '2ND', '3RD', '4TH' etc.
    import re
    digit_match = re.match(r'^(\d+)', sem_str)
    if digit_match:
        return int(digit_match.group(1))

    # 3. Simple Roman Numeral mapping
    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}
    for rom, val in roman_map.items():
        if sem_str.endswith(f"-{rom}") or sem_str.endswith(f" {rom}") or sem_str == rom:
            return val
    return None

def get_base64_image(image_field):
    if not image_field:
        return ""
    try:
        with open(image_field.path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception:
        return ""

def generate_ug_roll_sheet_pdf(exam, college, department_uid=None):
    """
    Generates Exam Roll Sheet PDF for UG.
    Filters students by college and exam (via semester & session).
    Header includes all papers scheduled for this exam.
    Optional: Filters by department_uid.
    """
    sem_int = get_sem_integer(exam.semester)
    print(f"{sem_int = }")
    session_str = str(exam.session or "").strip()
    print(f"{session_str = }")
    
    # 1. Fetch Exam Registrations
    filters = {
        'student__college': college,
        'sem': sem_int,
        'session__iexact': session_str,
    }
    if department_uid:
        filters['student__major_course__uid'] = department_uid

    registrations = ExamRegistration.objects.filter(
        **filters
    ).select_related(
        'student', 'student__batch', 'student__program', 'student__major_course'
    ).prefetch_related('assessment').order_by('student__roll_no', 'student__registration_no')
    print(f"{registrations = }")

    # All statuses (don't exclude pending/open etc. as requested)
    # the registrations queryset remains unchanged from the initial filter

    if not registrations.exists():
        return None

    # 2. Get Exam Center
    center_name = "-"
    center_mapping = UGExamCenterMapping.objects.filter(
        exam=exam,
        attached_colleges=college
    ).select_related('center').first()
    
    if center_mapping and center_mapping.center:
        center_name = center_mapping.center.name

    # 3. Define Header Categories (Priority Order)
    # This list defines which columns appear and in what order
    category_order = ['MJC', 'MIC', 'SEC', 'VAC', 'MDC', 'AEC']
    
    # IMPORTANT: To keep the table structure consistent, we find categories 
    # across ALL students registered for this exam in the college, 
    # even if we are currently filtering for one department.
    college_registrations = ExamRegistration.objects.filter(
        student__college=college,
        sem=sem_int,
        session__iexact=session_str,
    )
    
    found_types = StudentCourseAssessment.objects.filter(
        exam_registrations__in=college_registrations,
        label='ESE-Theory'
    ).values_list('course_type', flat=True).distinct()
    
    # Normalize and filter found types
    found_types = [t.strip().upper() for t in found_types if t]
    
    # Final sorted headers: use ordered list first, then any extra ones alphabetically
    active_headers = [cat for cat in category_order if cat in found_types]
    others = sorted([t for t in found_types if t not in category_order])
    active_headers.extend(others)

    # Convert to format expected by template
    subjects = [{"course_name_html": h, "course_type": h} for h in active_headers]

    # 4. Build Student Row Data
    student_data = []
    for reg in registrations:
        student = reg.student
        
        # Create a lookup: Category -> Subject Name (e.g., 'MJC' -> 'History of India')
        assessments = reg.assessment.filter(label='ESE-Theory')
        name_lookup = { (ass.course_type or "").strip().upper(): ass.course_name for ass in assessments }

        # For each column in the header, pick the student's course name or return "-"
        row_subjects = [name_lookup.get(h, "-") for h in active_headers]

        student_data.append({
            "name": f"{student.first_name} {student.last_name or ''}".strip().upper(),
            "roll_no": student.roll_no or "-",
            "registration_no": student.registration_no or "-",
            "department_name": student.major_course.name if student.major_course else "-",
            "subjects_marked": row_subjects,
        })
 
    # 5. Context
    base_static_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images')
    controller_sig_path = os.path.join(base_static_path, 'controller-of-examination-signature.png')
    controller_sig_b64 = ""
    if os.path.exists(controller_sig_path):
        with open(controller_sig_path, 'rb') as f:
            controller_sig_b64 = base64.b64encode(f.read()).decode('utf-8')

    first_student = registrations.first().student
    display_course = first_student.program.name if first_student.program else (first_student.degree.name if first_student.degree else "-")

    context = {
        "exam": exam,
        "college_name": college.name,
        "college_code": college.college_code or college.center_code or "-",
        "center_name": center_name,
        "course_name": display_course,
        # "branch_name": first_student.major_course.name if first_student.major_course else "-",
        "batch_name": first_student.batch.name if first_student.batch else "-",
        "year": exam.exam_month_year or "-",
        "session": exam.session or "-",
        "subjects": subjects,
        "student_data": student_data,
        "controller_signature": controller_sig_b64,
    }

    # 6. Render & Generate
    html_string = render_to_string('ug/roll_sheet.html', context)
    buffer = BytesIO()
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(target=buffer)
    
    return buffer.getvalue()
