from io import BytesIO
from django.db.models import Q
from difflib import SequenceMatcher
import os
import base64
import qrcode
import re
import datetime
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

def normalize_course_name(value):
    value = str(value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()

def find_strict_subject_schedule(queryset, course_name, paper_code, new_course_code=None):
    target_name = normalize_course_name(course_name)

    # PRIORITY 1: Course Name (Exact or Fuzzy Match) MUST BE FIRST!
    # Because 'paper_code' is shared across different subjects in AEC/VAC/SEC (e.g. 1006 = Hindi, English, Urdu)
    if target_name:
        if course_name:
            match = queryset.filter(exam_subject__course_name__iexact=course_name).order_by('exam_date', 'exam_time').first()
            if match:
                return match

        best_match = None
        best_score = 0.0
        for schedule in queryset.select_related('exam_subject').order_by('exam_date', 'exam_time'):
            subject = schedule.exam_subject
            if not subject:
                continue
            schedule_name = normalize_course_name(subject.course_name)
            if not schedule_name:
                continue
            if schedule_name == target_name:
                return schedule
                
            # Allow substring match ("urdu" in "mil urdu") to prevent shared paper_code fallback trap
            if target_name in schedule_name or schedule_name in target_name:
                return schedule
                
            # Check for high similarity fuzzy match
            score = SequenceMatcher(None, target_name, schedule_name).ratio()
            if score > best_score:
                best_score = score
                best_match = schedule
        
        # High threshold for strict match
        if best_score > 0.85:
            return best_match

    # PRIORITY 2: Paper Code Fallbacks
    if paper_code:
        match = queryset.filter(exam_subject__paper_code=paper_code).order_by('exam_date', 'exam_time').first()
        if match:
            return match

    if new_course_code:
        match = queryset.filter(exam_subject__new_course_code=new_course_code).order_by('exam_date', 'exam_time').first()
        if match:
            return match

    return None

def find_best_subject_schedule(queryset, course_name, paper_code, new_course_code=None, allow_last_fallback=False):
    target_name = normalize_course_name(course_name)

    # PRIORITY 1: Course Name Match (Highest priority to avoid shared code collision)
    if target_name:
        if course_name:
            match = queryset.filter(exam_subject__course_name__iexact=course_name).order_by('exam_date', 'exam_time').first()
            if match:
                return match

        best_match = None
        best_score = 0.0
        for schedule in queryset.select_related('exam_subject').order_by('exam_date', 'exam_time'):
            subject = schedule.exam_subject
            if not subject:
                continue
            schedule_name = normalize_course_name(subject.course_name)
            if not schedule_name:
                continue
            if target_name in schedule_name or schedule_name in target_name:
                return schedule
            score = SequenceMatcher(None, target_name, schedule_name).ratio()
            if score > best_score:
                best_score = score
                best_match = schedule

        # Lower threshold for best match
        if best_score >= 0.70:
            return best_match

    # PRIORITY 2: Paper Code Fallback
    if paper_code:
        match = queryset.filter(exam_subject__paper_code=paper_code).order_by('exam_date', 'exam_time').first()
        if match:
            return match

    if new_course_code:
        match = queryset.filter(exam_subject__new_course_code=new_course_code).order_by('exam_date', 'exam_time').first()
        if match:
            return match

    return queryset.order_by('exam_date', 'exam_time').first() if allow_last_fallback else None

def generate_ug_admit_card_pdf(student, exam):
    """
    Utility to generate Admit Card PDF for a UG student.
    Matches MCA's template context structure.
    """
    # 1. Get Exam Registration to determine Exam Type
    sem_int = get_sem_integer(exam.semester)
    
    # 1. Fetch Exam Registration (Strictly for the target Exam and REGISTERED status)
    registration = ExamRegistration.objects.filter(
        student=student,
        exam=exam,
        status='REGISTERED'
    ).first()
    
    if not registration:
        print(f"DEBUG: No REGISTERED ExamRegistration found for student {student.registration_no} and exam {exam.uid}")
        return None

    exam_type = registration.exam_type

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

    # 4. Prepare Context
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
        # Filter only ESE-Theory subjects as requested
        registered_assessments = registration.assessment.filter(label__iexact='ESE-Theory')
        print(f"DEBUG: Populating schedules for {registered_assessments.count()} ESE-Theory assessments")
        
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
            # dept_obj = ass.department or student.department
            dept_obj = student.department
            dept_id = dept_obj.id if dept_obj else None

            print(f"DEBUG: Processing {category} - {course_name} (Dept ID: {dept_id})")

            # Step 1: Category cleaning & Department resolution
            # Clean category (e.g. 'AEC' from 'AEC-1')
            base_cat = str(category).split('-')[0].strip().upper() if category else ""
            
            # Smart Overrides: For AEC/VAC/SEC/MJC/MIC/MDC, resolve the best possible department
            curr_dept_id = dept_id
            if base_cat == 'MJC' and student.major_course:
                curr_dept_id = student.major_course.id
            elif base_cat == 'MIC' and student.minor_course:
                curr_dept_id = student.minor_course.id
            elif base_cat == 'MDC' and student.mdc_course:
                curr_dept_id = student.mdc_course.id
            elif base_cat in ['AEC', 'VAC', 'SEC'] and student.major_course:
                curr_dept_id = student.major_course.id

            # Step 4: Check Exam Schedule Context
            sch_qs = UGExamSchedule.objects.filter(exam=exam)

            # --- SYSTEMATIC 3-STEP LOOKUP (Common Priority) ---
            sch = None
            if base_cat in ['AEC', 'VAC', 'SEC']:
                # Priority 2: Student MJC Specific Mapping (MJC Overrides MUST be prioritized first)
                student_major_course_id = student.major_course.id if student.major_course else None
                if student_major_course_id:
                    sch = find_strict_subject_schedule(
                        sch_qs.filter(
                            mjc__id=student_major_course_id,
                            department__isnull=True,
                            exam_subject__isnull=False,
                            exam_type__iexact=base_cat
                        ),
                        course_name,
                        ass.paper_code,
                        ass.new_course_code
                    )

                if not sch:
                    # Priority 1: Common Paper Pool (Both Department and MJC NULL)
                    # This fixes the 2:00 PM vs 10:00 AM problem for Art of Being Happy / Creative Writing
                    sch = find_strict_subject_schedule(
                        sch_qs.filter(
                            department__isnull=True,
                            mjc__isnull=True,
                            exam_subject__isnull=False,
                            exam_type__iexact=base_cat
                        ),
                        course_name,
                        ass.paper_code,
                        ass.new_course_code
                    )
            else:
                # Standard Subjects (MJC, MIC, MDC)
                
                # Check 1: Find EXACT schedule mapped to this specific Course (MJC/MIC/MDC)
                if not sch and curr_dept_id:
                    matches = sch_qs.filter(mjc__id=curr_dept_id, exam_type__iexact=base_cat)
                    if matches.count() == 1:
                        sch = matches.first()
                    elif matches.count() > 1:
                        # Take the first available if multiple exist
                        sch = matches.order_by('exam_date', 'exam_time').first()

                # Check 2: If Course mapping misses, fallback to the Student's real Department
                if not sch and dept_id:
                    matches = sch_qs.filter(department__id=dept_id, exam_type__iexact=base_cat)
                    if matches.count() == 1:
                        sch = matches.first()
                    elif matches.count() > 1:
                        sch = matches.order_by('exam_date', 'exam_time').first()

                # Check 3: Final Resort, any schedule matching the category
                if not sch:
                    matches = sch_qs.filter(exam_type__iexact=base_cat, department__isnull=True, mjc__isnull=True)
                    if matches.count() == 1:
                        sch = matches.first()
                    elif matches.count() > 1:
                        sch = matches.order_by('exam_date', 'exam_time').first()

            # FALLBACK - If NO match is found anywhere
            if not sch and dept_id:
                matches = sch_qs.filter(department__id=dept_id, exam_type__iexact=base_cat)
                if matches.count() >= 1:
                    sch = matches.order_by('exam_date', 'exam_time').first()
                # print(f"  - MATCHED via {'category' if sch.department.exists() else 'mjc-fallback'} logic: {sch.exam_date} | {sch.exam_time}")
            # else:
                # print(f"  - NO SCHEDULE found for Category: {category}")

            if base_cat == 'SEC' and course_name and 'Creative Writing' in str(course_name):
                print(f"==================== DEBUG SEC CREATIVE WRITING ====================")
                print(f"course_name: {course_name}, paper_code: {ass.paper_code}")
                print(f"base_cat: {base_cat}, dept_id: {dept_id}, curr_dept_id: {curr_dept_id}")
                
                print("--- Priority 1 Pool (Common) ---")
                qs1 = sch_qs.filter(department__isnull=True, mjc__isnull=True, exam_subject__isnull=False, exam_type__iexact=base_cat).order_by('exam_date', 'exam_time')
                for q in qs1: 
                    print(f"  {q.exam_date} {q.exam_time} | Subj: {q.exam_subject.course_name} | Code: {q.exam_subject.paper_code}")
                
                student_major_course_id = student.major_course.id if student.major_course else None
                if student_major_course_id:
                    print(f"--- Priority 2 Pool (MJC Specific map) for {student_major_course_id} ---")
                    qs2 = sch_qs.filter(mjc__id=student_major_course_id, department__isnull=True, exam_subject__isnull=False, exam_type__iexact=base_cat).order_by('exam_date', 'exam_time')
                    for q in qs2: 
                        print(f"  {q.exam_date} {q.exam_time} | Subj: {q.exam_subject.course_name} | Code: {q.exam_subject.paper_code}")

                print(f">>> Final resolved schedule for this assessment: {sch}")
                if sch:
                    print(f"    Date: {sch.exam_date}, Time: {sch.exam_time}, Sitting: {sch.sitting}")
                print(f"====================================================================")

            # Prepare row data
            exam_time_val = sch.exam_time if sch else "-"
            exam_date_val = sch.exam_date if sch else "-"
            sitting_val = (sch.sitting if sch else "General") if sch else "-"

            # HARDCODED OVERRIDE FOR AEC MIL - URDU
            if base_cat == 'AEC' and course_name and course_name.strip() == 'MIL - Urdu':
                exam_date_val = datetime.date(2026, 4, 9)
                exam_time_val = "01:00 PM to 05:00 PM"
                sitting_val = "2nd Sitting"

            context['schedules'].append({
                'category': category or "-",
                # PRIORITY: 1. Schedule code -> 2. Paper code -> 3. Course code
                'code': (sch.exam_subject.paper_code if sch and sch.exam_subject else None) or \
                        ass.paper_code or ass.new_course_code or "-",
                'name': course_name or (sch.exam_subject.course_name if sch and sch.exam_subject else (sch.json_data.get('subject_name') if sch and sch.json_data else "-")),
                'exam_time': exam_time_val,
                'exam_date': exam_date_val,
                'sitting': sitting_val,
            })
 
        # 4. Sort schedules according to Requested Order (AEC, VAC, SEC, MJC, MIC, MDC)
        order_priority = {
            'AEC': 1, 'VAC': 2, 'SEC': 3, 'MJC': 4, 'MIC': 5, 'MDC': 6
        }
        
        def get_sort_key(s):
            # Primary: Date
            dt = s['exam_date']
            # Fallback for empty dates to keep them at the bottom
            date_val = str(dt) if dt and dt != "-" else "9999-12-31"
            
            # Secondary: Category Priority
            cat_str = str(s['category']).split('-')[0].strip().upper()
            pri = order_priority.get(cat_str, 99)
            
            return (date_val, pri)

        context['schedules'].sort(key=get_sort_key)
    else:
        print("DEBUG: No ExamRegistration found for student, schedules list will be empty.")

    # 5. Generate QR Code
    qr_code_image = None
    try:
        import qrcode
        qr_data = (
            f"Candidate Name: {context['student']['full_name']}\n"
            f"Registration No: {context['student']['registration_no']}\n"
            f"Roll No: {context['student']['roll_no']}\n"
            f"Exam: {context['exam']['name']}\n"
            f"College: {context['student']['college_name']}\n"
            f"Center: {context['center_name']}\n"
            f"Exam Type: {context['status']}"
        )

        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        qr_code_image = f"data:image/png;base64,{qr_b64}"
    except Exception as e:
        print(f"DEBUG: QR code generation failed: {e}")

    context['qr_code_image'] = qr_code_image

    # 6. Render & Generate
    html_string = render_to_string('ug/admit_card.html', context)
    buffer = BytesIO()
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(target=buffer)
    
    return buffer.getvalue()

