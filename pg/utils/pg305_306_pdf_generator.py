"""
PDF Generator for PG305/PG306 Attendance Sheets
Generates 4 students per page with filtered subject enrollment
"""

import os
import re as _re
import logging
from django.conf import settings
from django.template.loader import get_template
from weasyprint import HTML
from pg.models import (
    PGExamSchedule,
    PGExamCenterMapping,
    PGStudentCourseAssessment,
)
from pup_umis_backend.utils.file_utils import image_to_base64, generate_barcode_base64

logger = logging.getLogger(__name__)

# Roman numeral mappings
_roman_str_to_int = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
}

roman_map_inv = {
    '1': 'I', '2': 'II', '3': 'III', '4': 'IV', '5': 'V',
    '6': 'VI', '7': 'VII', '8': 'VIII'
}


def generate_pg305_306_attendance_pdf(exam, college, department, paper_code, student_ids_filter=None):
    """
    Generate PG305/PG306 attendance sheets with 4 students per page.
    
    Args:
        exam: PGExam object
        college: College object
        department: PGDepartment object
        paper_code: 'PG305' or 'PG306'
        student_ids_filter: Optional list of student IDs to filter (pre-filtered by script)
    
    Returns:
        PDF bytes or None
    """
    
    # ── Semester detection ──
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
    
    # ── Get students enrolled in this paper code ──
    from pg.models import PGExamRegistration
    
    regs_qs = PGExamRegistration.objects.filter(
        exam=exam,
        student__college=college,
        student__department=department,
        status='REGISTERED',
    )
    
    if sem_variants_int:
        regs_qs = regs_qs.filter(sem__in=sem_variants_int)
    
    # Filter by pre-filtered student IDs (from script)
    if student_ids_filter:
        regs_qs = regs_qs.filter(student_id__in=student_ids_filter)
    
    regs_qs = regs_qs.select_related(
        'student', 'student__department', 'student__program'
    ).order_by('student__roll_no', 'student__registration_no')
    
    regs_list = list(regs_qs)
    
    if not regs_list:
        logger.warning(
            f"[PG305/306] No students found for {paper_code} in {department.name}, {college.name}"
        )
        return None
    
    logger.info(f"[PG305/306] Processing {len(regs_list)} students for {paper_code}")
    
    # ── Get students who actually have this paper enrolled ──
    student_ids = [r.student_id for r in regs_list]
    
    # Check which students have this specific paper code in their assessments
    enrolled_students = set(
        PGStudentCourseAssessment.objects.filter(
            student_id__in=student_ids,
            paper_code=paper_code
        ).values_list('student_id', flat=True).distinct()
    )
    
    # Filter registrations to only students who have this paper
    regs_list = [r for r in regs_list if r.student_id in enrolled_students]
    
    if not regs_list:
        logger.warning(
            f"[PG305/306] No students enrolled in {paper_code} for {department.name}, {college.name}"
        )
        return None
    
    logger.info(f"[PG305/306] {len(regs_list)} students actually enrolled in {paper_code}")
    
    # ── Center mapping ──
    center_name = "-"
    cm = PGExamCenterMapping.objects.filter(exams=exam, attached_colleges=college).first()
    if cm and cm.center:
        center_name = cm.center.name
    
    # ── Get exam schedules ──
    # PG305/PG306 share common exam schedules, not paper-specific
    all_schedules = PGExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure', 'group').order_by('exam_date', 'exam_time')
    
    # Use all schedules (PG305/PG306 don't have separate schedules)
    paper_schedules = list(all_schedules)
    
    # ── University logo ──
    def _find_logo():
        possible_paths = [
            os.path.join(settings.BASE_DIR, "static", "images", "common", "purnea-logo.png"),
            os.path.join(settings.BASE_DIR, "static", "images", "purnea-logo.png"),
            os.path.join(settings.MEDIA_ROOT, "common", "purnea-logo.png"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return image_to_base64(p)
        return None
    
    university_logo = _find_logo()
    
    # ── Build attendance data ──
    attendance_data = []
    
    for reg in regs_list:
        student = reg.student
        
        # Student photo
        photo_b64 = None
        if hasattr(student, 'profile_image') and student.profile_image:
            try:
                photo_path = student.profile_image.path if hasattr(student.profile_image, 'path') else None
                if photo_path and os.path.exists(photo_path):
                    photo_b64 = image_to_base64(photo_path)
            except Exception as e:
                logger.debug(f"Photo not found for {student.registration_no}: {e}")
        
        # Barcode
        barcode_b64 = None
        if student.roll_no:
            try:
                barcode_b64 = generate_barcode_base64(student.roll_no)
            except Exception as e:
                logger.debug(f"Barcode generation failed for {student.roll_no}: {e}")
        
        # Build schedule list for this student
        student_schedules = []
        for sched in paper_schedules:
            # Use department name as subject (e.g., "POLITICAL SCIENCE", "ECONOMICS")
            subject_name = department.name if department else paper_code
            
            schedule_entry = {
                'date': sched.exam_date.strftime('%d-%m-%Y') if sched.exam_date else '-',
                'subject_name': subject_name,
                'subject_code': sched.common_course_structure.course_code if sched.common_course_structure else paper_code,
            }
            student_schedules.append(schedule_entry)
        
        # Construct full name
        full_name = '-'
        if student.first_name or student.last_name:
            name_parts = [student.first_name or '', student.last_name or '']
            full_name = ' '.join(filter(None, name_parts)).strip() or '-'
        
        attendance_data.append({
            'name': full_name,
            'department_name': department.name if department else '-',
            'registration_no': student.registration_no or '-',
            'roll_no': student.roll_no or '-',
            'photo': photo_b64,
            'barcode': barcode_b64,
            'schedules': student_schedules,
        })
    
    # ── Render template ──
    sem_display = str(sem_variants_int[0]) if sem_variants_int else (exam.session or '-')
    
    # Get paper name
    paper_name = ""
    if paper_schedules and paper_schedules[0].common_course_structure:
        paper_name = paper_schedules[0].common_course_structure.course_name or ""
    
    context = {
        'university_logo': university_logo,
        'exam_header': f"{exam.name} (Semester {sem_display})",
        'center_name': center_name,
        'college_name': college.name,
        'paper_code': paper_code,
        'paper_name': paper_name,
        'attendance_data': attendance_data,
    }
    
    template = get_template('pg/pg305_306_attendance_sheet.html')
    html_string = template.render(context)
    
    # ── Generate PDF ──
    try:
        pdf_bytes = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        logger.info(
            f"[PG305/306] Generated PDF for {paper_code}: {college.name}, "
            f"{department.name}, {len(attendance_data)} students, {len(pdf_bytes)} bytes"
        )
        return pdf_bytes
    except Exception as e:
        logger.error(f"[PG305/306] PDF generation failed: {e}", exc_info=True)
        return None
