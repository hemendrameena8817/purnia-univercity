from io import BytesIO
import os
import base64
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from collections import OrderedDict
from ..models import (
    UGStudentProfile, ExamRegistration, StudentCourseAssessment, 
    UGExamCenterMapping, UGExamSchedule
)

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

def generate_ug_roll_sheet_pdf(exam, college):
    """
    Generates Exam Roll Sheet PDF for UG.
    Filters students by college and exam (via semester & session).
    Header includes all papers scheduled for this exam.
    """
    sem_int = get_sem_integer(exam.semester)
    session_str = str(exam.session or "").strip()
    
    # 1. Fetch Exam Registrations
    registrations = ExamRegistration.objects.filter(
        student__college=college,
        sem=sem_int,
        session__iexact=session_str,
    ).select_related(
        'student', 'student__batch', 'student__program', 'student__major_course'
    ).prefetch_related('assessment').order_by('student__roll_no', 'student__registration_no')

    # Status check (prefer REGISTERED, but take others if needed)
    reg_filtered = registrations.filter(status='REGISTERED')
    if reg_filtered.exists():
        registrations = reg_filtered

    if not registrations.exists():
        # Even more fallback: Try without strict session if session seems potentially different
        # Sometimes session is stored as '2023-27' but requested as '2023-2027'
        registrations = ExamRegistration.objects.filter(
            student__college=college,
            sem=sem_int
        ).select_related(
            'student', 'student__batch'
        ).prefetch_related('assessment').order_by('student__roll_no')
        
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

    # 3. Collect ALL scheduled papers for this exam (Header Subjects)
    # Using UGExamSchedule to get official subjects for this exam
    subjects_map = OrderedDict()
    schedules = UGExamSchedule.objects.filter(exam=exam).select_related('exam_subject').order_by('exam_date', 'sitting')
    
    for sch in schedules:
        if sch.exam_subject:
            code = (sch.exam_subject.paper_code or "").strip().upper()
            if code and code not in subjects_map:
                subjects_map[code] = {
                    "code": code,
                    "course_name": sch.exam_subject.course_name or code,
                    "course_type": sch.exam_type or ""
                }
    
    # Fallback/Addition: Check if students have subjects NOT in schedule (rare but possible)
    for reg in registrations:
        for ass in reg.assessment.all():
            code = (ass.paper_code or "").strip().upper()
            if code and code not in subjects_map:
                subjects_map[code] = {
                    "code": code,
                    "course_name": ass.course_name or code,
                    "course_type": ass.course_type or ""
                }
                
    # Final sorted subject list for header
    subjects = list(subjects_map.values())

    # 4. Prepare Student Row Data
    student_data = []
    for reg in registrations:
        student = reg.student
        # Get all paper codes this student is registered for in THIS registration
        student_paper_codes = set(ass.paper_code.strip().upper() for ass in reg.assessment.all() if ass.paper_code)

        # Map to header subjects: if student has it, keep code; else "-"
        marked_subjects = []
        for header_subj in subjects:
            if header_subj['code'] in student_paper_codes:
                marked_subjects.append(header_subj['code'])
            else:
                marked_subjects.append("-")

        student_data.append({
            "name": f"{student.first_name} {student.last_name or ''}".strip(),
            "roll_no": student.roll_no or "-",
            "registration_no": student.registration_no or "-",
            "subjects_marked": marked_subjects,
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
        "branch_name": first_student.major_course.name if first_student.major_course else "-",
        "batch_name": first_student.batch.name if first_student.batch else "-",
        "year": exam.exam_month_year or "-",
        "subjects": subjects,
        "student_data": student_data,
        "controller_signature": controller_sig_b64,
    }

    # 6. Render & Generate
    html_string = render_to_string('ug/roll_sheet.html', context)
    buffer = BytesIO()
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(target=buffer)
    
    return buffer.getvalue()
