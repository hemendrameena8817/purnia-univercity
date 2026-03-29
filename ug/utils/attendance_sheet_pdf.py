import os
import io
import time
import base64
import logging
import datetime
from django.conf import settings
from django.template.loader import get_template
from django.db.models import Q
from weasyprint import HTML
from ug.utils.file_utils import image_to_base64, generate_qrcode_base64

from ug.models import (
    ExamRegistration,
    UGExamSchedule,
    UGExamCenterMapping,
    StudentCourseAssessment,
)
from ug.utils.admit_card_pdf import find_strict_subject_schedule
from ug.utils.roll_sheet_pdf import get_sem_integer

logger = logging.getLogger(__name__)

def _resolve_student_schedules_for_attendance(student, exam):
    """
    Local implementation of the Admit Card schedule resolution logic 
    to ensure 100% parity without modifying admit_card_pdf.py.
    """
    registration = ExamRegistration.objects.filter(
        student=student, exam=exam, status='REGISTERED'
    ).first()
    
    if not registration:
        return []

    sch_qs = UGExamSchedule.objects.filter(exam=exam).select_related('exam_subject')
    registered_assessments = registration.assessment.filter(label__iexact='ESE-Theory')
    
    seen_subjects = set()
    schedules_data = []
    
    for ass in registered_assessments:
        course_name = ass.course_name
        category = ass.course_type
        
        subj_key = f"{category}:{course_name}"
        if subj_key in seen_subjects:
            continue
        seen_subjects.add(subj_key)
        
        dept_obj = student.department
        dept_id = dept_obj.id if dept_obj else None
        base_cat = str(category).split('-')[0].strip().upper() if category else ""
        
        curr_dept_id = student.major_course.id if student.major_course else dept_id

        sch = None
        if base_cat in ['AEC', 'VAC', 'SEC']:
            student_major_course_id = student.major_course.id if student.major_course else None
            if student_major_course_id:
                sch = find_strict_subject_schedule(
                    sch_qs.filter(mjc__id=student_major_course_id, department__isnull=True, exam_subject__isnull=False, exam_type__iexact=base_cat),
                    course_name, ass.paper_code, ass.new_course_code
                )
            if not sch:
                sch = find_strict_subject_schedule(
                    sch_qs.filter(department__isnull=True, mjc__isnull=True, exam_subject__isnull=False, exam_type__iexact=base_cat),
                    course_name, ass.paper_code, ass.new_course_code
                )
        else:
            if not sch and curr_dept_id:
                matches = sch_qs.filter(Q(mjc__id=curr_dept_id) | Q(department__id=curr_dept_id), exam_type__iexact=base_cat)
                if matches.exists():
                    sch = matches.order_by('exam_date', 'exam_time').first()
            if not sch and dept_id:
                matches = sch_qs.filter(department__id=dept_id, exam_type__iexact=base_cat)
                if matches.exists():
                    sch = matches.order_by('exam_date', 'exam_time').first()
            if not sch:
                matches = sch_qs.filter(exam_type__iexact=base_cat, department__isnull=True, mjc__isnull=True)
                if matches.exists():
                    sch = matches.order_by('exam_date', 'exam_time').first()

        if not sch and dept_id:
            matches = sch_qs.filter(department__id=dept_id, exam_type__iexact=base_cat)
            if matches.exists():
                sch = matches.order_by('exam_date', 'exam_time').first()

        exam_date_obj = sch.exam_date if sch else None
        sitting_val = (sch.sitting if sch else "") if sch else "-"

        # HARDCODED OVERRIDES (PARITY WITH ADMIT CARD)
        overrides = {
            'AEC': {
                'MIL- English Communication': {'date': datetime.date(2026, 4, 8), 'sitting': ""},
                'MIL - Urdu': {'date': datetime.date(2026, 4, 9), 'sitting': ""},
                'MIL - Maithili': {'date': datetime.date(2026, 4, 9), 'sitting': ""},
                'MIL - Bengali': {'date': datetime.date(2026, 4, 9), 'sitting': ""},
            },
            'VAC': {
                'Fit India': {'date': datetime.date(2026, 4, 10), 'sitting': ""},
                'Art of Being Happy': {'date': datetime.date(2026, 4, 11), 'sitting': ""},
            },
            'SEC': {
                'Basic IT Tools': {'date': datetime.date(2026, 4, 13), 'sitting': ""},
                'Digital Marketing': {'date': datetime.date(2026, 4, 15), 'sitting': ""},
                'Public Speaking English Language and Leadership': {'date': datetime.date(2026, 4, 15), 'sitting': ""},
            }
        }
        
        if base_cat in overrides and course_name and course_name.strip() in overrides[base_cat]:
            ov = overrides[base_cat][course_name.strip()]
            exam_date_obj = ov['date']
            sitting_val = ov['sitting']

        schedules_data.append({
            'category': category or "-",
            'code': (sch.exam_subject.new_course_code if sch and sch.exam_subject else None) or \
                    ass.new_course_code or ass.paper_code or "-",
            'name': course_name or (sch.exam_subject.course_name if sch and sch.exam_subject else (sch.json_data.get('subject_name') if sch and sch.json_data else "-")),
            'date': exam_date_obj.strftime('%d-%m-%Y') if exam_date_obj else "-",
            'sitting': sitting_val,
            'raw_date': exam_date_obj
        })

    # Sort
    order_priority = {'AEC': 1, 'VAC': 2, 'SEC': 3, 'MJC': 4, 'MIC': 5, 'MDC': 6}
    def get_sort_key(s):
        dt = s['raw_date']
        date_val = str(dt) if dt else "9999-12-31"
        cat_str = str(s['category']).split('-')[0].strip().upper()
        return (date_val, order_priority.get(cat_str, 99))

    schedules_data.sort(key=get_sort_key)
    return schedules_data

def generate_ug_attendance_sheet_pdf(exam, college, department_uid=None, registration_no=None):
    """
    Generates student-wise UG Attendance Sheet PDF.
    Implements 100% parity with Admit Card schedule logic routing.
    """
    sem_int = get_sem_integer(exam.semester)
    session_str = str(exam.session or "").strip()
    
    filters = {
        'student__college': college,
        'exam': exam,
        'status': 'REGISTERED'
    }
    if sem_int:
        filters['sem'] = sem_int
    if session_str:
        filters['session__iexact'] = session_str

    if department_uid:
        filters['student__department__uid'] = department_uid
    if registration_no:
        if isinstance(registration_no, str) and "," in registration_no:
            filters['student__registration_no__in'] = [r.strip() for r in registration_no.split(",") if r.strip()]
        else:
            filters['student__registration_no'] = registration_no

    regs_qs = ExamRegistration.objects.filter(**filters).select_related(
        'student', 'student__department', 'student__program', 'student__major_course'
    ).prefetch_related('assessment').order_by('student__roll_no', 'student__registration_no')

    regs_list = list(regs_qs)
    if not regs_list:
        logger.warning(f"[UG ATTENDANCE] No registrations found for exam='{exam.name}'")
        return None

    # Center mapping
    center_name = "-"
    cm = UGExamCenterMapping.objects.filter(exam=exam, attached_colleges=college).select_related('center').first()
    if cm and cm.center:
        center_name = cm.center.name

    # University logo
    def _find_logo():
        possible_paths = [
            os.path.join(settings.BASE_DIR, "static", "images", "common", "purnea-logo.png"),
            os.path.join(settings.BASE_DIR, "static", "images", "purnea-logo.png"),
            os.path.join(settings.BASE_DIR, "ug", "static", "ug", "images", "purnea-logo.png"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return image_to_base64(p)
        return None

    university_logo = _find_logo()

    global_context = {
        'university_logo': university_logo,
        'exam_header': f"{exam.name} (Semester {sem_int if sem_int else '-'})",
        'center_name': center_name,
        'session': exam.session or '-',
        'course_name': 'Under Graduation',
        'semester': str(sem_int) if sem_int else '-',
        'college_name': college.name,
    }

    def _get_optimized_base64_photo(image_field):
        if not image_field: return None
        try:
            from PIL import Image
            with image_field.open('rb') as f:
                img = Image.open(f)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                max_width = 150
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    height = int(float(img.height) * float(ratio))
                    img = img.resize((max_width, height), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=75)
                return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception as e:
            try:
                return image_to_base64(image_field.path)
            except:
                return None

    total_regs = len(regs_list)
    BATCH_SIZE = 20
    all_pages = []
    template = get_template('ug/attendance_sheet.html')
    
    # Pre-evaluate base schedule QS
    base_sch_qs = UGExamSchedule.objects.filter(exam=exam).select_related('exam_subject')

    for i in range(0, total_regs, BATCH_SIZE):
        batch_regs = regs_list[i : i + BATCH_SIZE]
        batch_attendance_data = []
        start_time = time.time()
        
        for reg in batch_regs:
            student = reg.student
            
            # Use local deterministic logic (Mimicking Admit Card)
            student_schedules = _resolve_student_schedules_for_attendance(student, exam)
            
            # Barcode & Photo (using QR code as requested before)
            barcode_text = f"Roll:{student.roll_no or ''} Reg:{student.registration_no or ''} Name:{student.first_name} {student.last_name or ''}"
            try:
                barcode_base64 = generate_qrcode_base64(barcode_text)
            except Exception:
                barcode_base64 = None

            photo_base64 = _get_optimized_base64_photo(student.profile_image)
            dept_name = student.major_course.name if student.major_course else "-"

            batch_attendance_data.append({
                'name': f"{student.first_name} {student.last_name or ''}".strip(),
                'roll_no': student.roll_no or 'N/A',
                'registration_no': student.registration_no or 'N/A',
                'department_name': dept_name,
                'college_name': college.name,
                'photo': photo_base64,
                'barcode': barcode_base64,
                'schedules': student_schedules,
            })

        batch_context = global_context.copy()
        batch_context['attendance_data'] = batch_attendance_data
        
        html_string = template.render(batch_context)
        try:
            batch_doc = HTML(string=html_string, base_url=settings.BASE_DIR).render()
            all_pages.extend(batch_doc.pages)
        except Exception as e:
            logger.error(f"[UG ATTENDANCE] Rendering error: {e}")
            continue
            
        import gc
        del batch_attendance_data
        del html_string
        del batch_doc
        gc.collect()

    if not all_pages:
        return None

    try:
        base_doc = HTML(string="<html></html>").render()
        base_doc.pages = all_pages
        return base_doc.write_pdf()
    except Exception as e:
        logger.error(f"[UG ATTENDANCE] Final PDF assembly failed: {e}")
        return None
