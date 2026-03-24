from io import BytesIO
import os
import base64
import re
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from django.db import models
from ..models import (
    UGStudentProfile, ExamRegistration, StudentCourseAssessment, 
    UGExamCenterMapping, UGExamSchedule
)
from .registration_card_pdf import get_base64_image

def get_sem_integer(sem_str):
    """Helper to convert 'Semester-I' or '1' to integer 1."""
    if not sem_str: return None
    sem_str = str(sem_str).strip()
    if sem_str.isdigit(): return int(sem_str)
    
    # Simple Roman Numeral mapping
    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}
    sem_upper = sem_str.upper()
    for rom, val in roman_map.items():
        if sem_upper.endswith(f"-{rom}") or sem_upper.endswith(f" {rom}") or sem_upper == rom:
            return val
    return None

def generate_ug_admit_card_pdf(student, exam):
    """
    Utility to generate Admit Card PDF for a UG student.
    Matches MCA's template context structure.
    """
    # 1. Get Exam Registration to determine Exam Type
    sem_int = get_sem_integer(exam.semester)
    
    registration = ExamRegistration.objects.filter(
        student=student,
        sem=sem_int,
        session=exam.session,
    ).first()
    
    # Fallback if specific sem match fails
    if not registration:
        registration = ExamRegistration.objects.filter(
            student=student,
            session=exam.session,
        ).first()

    exam_type = registration.exam_type if registration else 'REGULAR'

    # 2. Get Center Information
    center_mapping = UGExamCenterMapping.objects.filter(
        exam=exam,
        attached_colleges=student.college
    ).select_related('center').first()

    # 3. Get Exam Schedules
    # Filter by exam and department name match (name_exact)
    # MJC is optional for some, required for others - handled by Q OR filter
    
    print(f"DEBUG: Generating Admit Card for Student: {student.registration_no}, Exam: {exam.name}")
    print(f"DEBUG: Exam Registration found: {registration.uid if registration else 'None'}")
    print(f"DEBUG: Using Exam Type (Internal): {exam_type}")

    # 3. Get Exam Schedules
    print(f"DEBUG: Generating Admit Card for Student: {student.registration_no}, Exam: {exam.name}")
    print(f"DEBUG: Using Exam Type: {exam_type}")

    # For now, showing all schedules matching the exam and type to ensure something displays
    schedules_qs = UGExamSchedule.objects.filter(
        exam=exam,
    ).order_by('exam_date', 'exam_time')

    final_count = schedules_qs.count()
    print(f"DEBUG: Total schedules found: {final_count}")
    
    for s in schedules_qs:
        paper_name = s.exam_subject.course_name if s.exam_subject else (s.json_data.get('subject_name') if s.json_data else "General Paper")
        print(f"  - MATCHED: {s.exam_subject.paper_code if s.exam_subject else 'No Code'} | {paper_name} | {s.exam_date}")

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

    # Ensure exam name is robust
    display_exam_name = exam.name if exam.name else f"UG {exam.semester or ''} Examination {exam.session or ''}".strip()

    context = {
        'exam': {'name': display_exam_name},
        'student': {
            'roll_no': student.roll_no or "-",
            'registration_no': student.registration_no or "-",
            'full_name': f"{student.first_name} {student.last_name or ''}".strip(),
            'father_name': student.father_name or "-",
            'mother_name': student.mother_name or "-",
            'gender': student.gender or "-",
            'college_name': student.college.name if student.college else "-",
        },
        'status': exam_type,
        'center_code': center_mapping.center.center_code if center_mapping and center_mapping.center else "-",
        'center_name': center_mapping.center.name if center_mapping and center_mapping.center else "NOT ALLOTTED",
        'student_photo': get_b64_only(student.profile_image),
        'student_sig': get_b64_only(student.signature),
        'university_logo': university_logo_b64,
        'watermark_logo': university_logo_b64, # Using same logo as watermark
        'controller_signature': controller_sig_b64,
        'schedules': []
    }

    # Populate schedules from registered assessments
    if registration:
        registered_assessments = registration.assessment.all()
        print(f"DEBUG: Populating schedules for {registered_assessments.count()} assessments")
        
        # 3. Process Assessments Step-by-Step (Unique by Category + Name)
        seen_subjects = set()
        for ass in registered_assessments:
            # Step 1: Get subject name and course category (MJC/MIC/etc.)
            course_name = ass.course_name
            category = ass.course_type
            
            # Skip if we already processed this exact Category + Subject combo
            subj_key = f"{category}:{course_name}"
            if subj_key in seen_subjects:
                continue
            seen_subjects.add(subj_key)
            
            # Step 2 & 3: Get Department object and ID
            # Use assessment's department if available
            dept_obj = ass.department or student.department
            dept_id = dept_obj.id if dept_obj else None

            print(f"DEBUG: Processing {category} - {course_name} (Dept ID: {dept_id})")

            # Step 4: Check Exam Schedule Context
            sch_qs = UGExamSchedule.objects.filter(exam=exam)

            # Step 5: Filter by category and department
            sch = None
            if dept_id:
                # Primary match: By department ID AND category
                sch = sch_qs.filter(
                    department__id=dept_id,
                    exam_type__iexact=category
                ).last()

            # Step 6: Fallback - If department match fails, check records where department is null but mjc matches
            if not sch and dept_id:
                sch = sch_qs.filter(
                    department__isnull=True,
                    mjc__id=dept_id,
                    exam_type__iexact=category
                ).last()

            if sch:
                print(f"  - MATCHED via {'category' if sch.department.exists() else 'mjc-fallback'} logic: {sch.exam_date} | {sch.exam_time}")
            else:
                print(f"  - NO SCHEDULE found for Category: {category}")

            # Prepare row data
            context['schedules'].append({
                'category': category or "-",
                'code': ass.paper_code or (sch.exam_subject.paper_code if sch and sch.exam_subject else "-"),
                'name': course_name or (sch.exam_subject.course_name if sch and sch.exam_subject else (sch.json_data.get('subject_name') if sch and sch.json_data else "-")),
                'exam_time': sch.exam_time if sch else "-",
                'exam_date': sch.exam_date if sch else "-",
                'sitting': (sch.sitting if sch else "General") if sch else "-",
            })
    else:
        print("DEBUG: No ExamRegistration found for student, schedules list will be empty.")

    # 5. Render & Generate
    html_string = render_to_string('ug/admit_card.html', context)
    buffer = BytesIO()
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(target=buffer)
    
    return buffer.getvalue()

