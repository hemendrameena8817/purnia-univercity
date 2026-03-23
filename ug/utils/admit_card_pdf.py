from io import BytesIO
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from ..models import (
    UGStudentProfile, ExamRegistration, StudentCourseAssessment, 
    UGExamCenterMapping, UGExamSchedule
)
from .registration_card_pdf import get_base64_image
import os
import base64

def generate_ug_admit_card_pdf(student, exam):
    """
    Utility to generate Admit Card PDF for a UG student.
    Matches MCA's template context structure.
    """
    # 1. Get Subjects from Course Assessment
    subjects = StudentCourseAssessment.objects.filter(
        student=student,
        semester=exam.semester,
        session=exam.session
    )

    # 2. Get Center Information
    center_mapping = UGExamCenterMapping.objects.filter(
        attached_colleges=student.college
    ).select_related('center').first()

    # 3. Get Exam Schedules
    schedules_qs = UGExamSchedule.objects.filter(
        department=student.department
    ).order_by('exam_date', 'exam_time')

    # 4. Prepare Context - MIRROR MCA STRUCTURE
    university_logo_b64 = ""
    base_static_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images')
    logo_path = os.path.join(base_static_path, 'purnea-logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            university_logo_b64 = base64.b64encode(f.read()).decode('utf-8')

    # Signature of controller
    controller_sig_path = os.path.join(base_static_path, 'controller-of-examination-signature.png') 
    if os.path.exists(controller_sig_path):
        with open(controller_sig_path, 'rb') as f:
            controller_sig_b64 = base64.b64encode(f.read()).decode('utf-8')

    # Photo & Sig Base64
    def get_b64_only(image_field):
        b64 = get_base64_image(image_field)
        if b64 and "," in b64:
            return b64.split(",")[1]
        return ""

    context = {
        'exam': {'name': exam.name},
        'student': {
            'roll_no': student.roll_no or "-",
            'registration_no': student.registration_no or "-",
            'full_name': f"{student.first_name} {student.last_name or ''}".strip(),
            'father_name': student.father_name or "-",
            'mother_name': student.mother_name or "-",
            'gender': student.gender or "-",
            'college_name': student.college.name if student.college else "-",
        },
        'status': 'REGULAR', # Standard for admit card
        'center_code': center_mapping.center.code if center_mapping and center_mapping.center else "-",
        'center_name': center_mapping.center.name if center_mapping and center_mapping.center else "NOT ALLOTTED",
        'student_photo': get_b64_only(student.profile_image),
        'student_sig': get_b64_only(student.signature),
        'university_logo': university_logo_b64,
        'watermark_logo': university_logo_b64, # Using same logo as watermark
        'controller_signature': controller_sig_b64,
        'schedules': []
    }

    # Populate schedules like MCA
    for sch in schedules_qs:
        context['schedules'].append({
            'code': student.department.name[:4].upper(), # Fallback code
            'name': f"{student.department.name} Paper",
            'exam_time': sch.exam_time,
            'exam_date': sch.exam_date,
            'sitting': sch.sitting_text or "General", # Ensure sitting is passed
        })

    # 5. Render & Generate
    html_string = render_to_string('ug/admit_card.html', context)
    buffer = BytesIO()
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(target=buffer)
    
    return buffer.getvalue()
