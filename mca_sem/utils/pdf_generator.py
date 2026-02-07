def generate_mca_admit_card_pdf(student, exam):
    from weasyprint import HTML, CSS
    import io, base64, os
    from django.conf import settings
    from django.template.loader import get_template
    from mca_sem.models import MCAExamCenterMapping, MCAExamSchedule
    from pup_umis_backend.utils.file_utils import image_to_base64
    import logging

    logger = logging.getLogger(__name__)

    # Get exam center mapping
    exam_center = None
    if student.college:
        mapping = MCAExamCenterMapping.objects.filter(
            exam=exam,
            attached_colleges=student.college
        ).first()
        if mapping:
            exam_center = mapping.center
    
    # Get exam schedules
    schedules = MCAExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure')


    # Prepare context for template
    context = {
        "exam": exam,
        "student": student,
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.center_code if exam_center else "-",
        "status": student.get_status_display() if student else "-",
        "schedules": schedules,
        "university_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "watermark_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "student_photo": image_to_base64(student.profile_image.path if student.profile_image else None),
        "student_sig": image_to_base64(student.signature.path if student.signature else None),
        "controller_signature": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
    }

    # Render HTML template
    html_string = get_template("mca_sem/admit_card.html").render(context)

    try:
        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        
        logger.info(f"PDF generated successfully using WeasyPrint, size: {len(pdf_file)} bytes")
        return pdf_file
        
    except Exception as e:
        logger.error(f"PDF generation failed with WeasyPrint: {str(e)}")
        return None

def generate_mca_roll_sheet_pdf(exam, college):
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from mca_sem.models import (
        MCAExamRegistration,
        MCAExamSchedule,
        MCACommonCourseStructure,
        MCAExamCenterMapping
    )
    from pup_umis_backend.utils.file_utils import image_to_base64
    import os
    import logging

    logger = logging.getLogger(__name__)

    # 1. Get all students registered for this exam in this college
    registrations = MCAExamRegistration.objects.filter(
        exam=exam,
        student__college=college
    ).select_related('student', 'student__batch').order_by('student__roll_no', 'student__registration_no')

    if not registrations.exists():
        logger.warning(f"No registrations found for Exam: {exam.name}, College: {college.name}")
        return None

    # Get exam center mapping for this college
    center_name = "-"
    center_mapping = MCAExamCenterMapping.objects.filter(
        exam=exam,
        attached_colleges=college
    ).first()
    if center_mapping and center_mapping.center:
        center_name = center_mapping.center.name

    # 2. Get the subjects (schedules) for this exam
    schedules = MCAExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure').order_by('exam_date', 'exam_time')

    subjects = []
    all_subject_ids = []
    for s in schedules:
        if s.common_course_structure:
            subjects.append({
                'id': s.common_course_structure.id,
                'code': s.common_course_structure.code,
                'course_name': s.common_course_structure.course_name
            })
            all_subject_ids.append(s.common_course_structure.id)

    # 3. Prepare student data rows
    student_data = []
    for reg in registrations:
        student = reg.student
        
        # Determine subjects student is registered for
        if reg.exam_type == 'REGULAR':
            student_subject_ids = all_subject_ids
        else:
            # For BACKLOG/IMPROVEMENT, get specific subjects
            student_subject_ids = list(reg.subjects.all().values_list('id', flat=True))
        
        student_data.append({
            'name': student.get_full_name(),
            'roll_no': student.roll_no or "-",
            'registration_no': student.registration_no or "-",
            'subject_ids': student_subject_ids
        })

    # 4. Prepare Context
    context = {
        "exam": exam,
        "college": college,
        "course_name": "MCA",
        "batch_name": registrations[0].student.batch.name if registrations[0].student.batch else "-",
        "session_name": exam.session or "-",
        "college_name": college.name or "-",
        "center_name": center_name,
        "semester": f"{exam.semester}" if exam.semester else "-",
        "syllabus": "-",
        "subjects": subjects,
        "student_data": student_data,
        "controller_signature": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
    }

    # Render HTML template
    html_string = get_template("mca_sem/roll_sheet.html").render(context)

    try:
        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        return pdf_file
    except Exception as e:
        logger.error(f"Roll Sheet PDF generation failed: {str(e)}")
        return None


def generate_mca_attendance_sheet_pdf(exam, college):
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from mca_sem.models import (
        MCAExamRegistration,
        MCAExamSchedule,
        MCAExamCenterMapping
    )
    from pup_umis_backend.utils.file_utils import image_to_base64, generate_barcode_base64
    import os
    import logging

    logger = logging.getLogger(__name__)

    # 1. Get registrations
    registrations = MCAExamRegistration.objects.filter(
        exam=exam,
        student__college=college
    ).select_related('student', 'student__batch', 'student__college').order_by('student__roll_no', 'student__registration_no')

    if not registrations.exists():
        return None

    # 2. Get center info
    center_mapping = MCAExamCenterMapping.objects.filter(
        exam=exam,
        attached_colleges=college
    ).first()
    center_name = f"{center_mapping.center.college_code} - {center_mapping.center.name}" if center_mapping and center_mapping.center else "-"

    # 3. Get all global schedules for this exam (for regular students)
    global_schedules = MCAExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure').order_by('exam_date', 'exam_time')

    # 4. Prepare student-wise data
    attendance_data = []
    semester_label = f"SEM {exam.semester}" if exam.semester else "-"

    for reg in registrations:
        student = reg.student
        
        # Determine student's schedules
        student_schedules = []
        if reg.exam_type == 'REGULAR':
            target_schedules = global_schedules
        else:
            # For BACKLOG, filter schedules matching their registered backlog subjects
            backlog_ids = list(reg.subjects.all().values_list('id', flat=True))
            target_schedules = global_schedules.filter(common_course_structure_id__in=backlog_ids)

        for s in target_schedules:
            student_schedules.append({
                'date': s.exam_date.strftime('%d-%m-%Y') if s.exam_date else "-",
                'sitting': s.sitting or "-",
                'subject_name': s.common_course_structure.course_name if s.common_course_structure else "-",
                'subject_code': s.common_course_structure.code if s.common_course_structure else "-",
            })

        # Generate Barcode Data
        # Format: Roll: XXX, Reg: YYY, Name: ZZZ, Sem: AAA
        barcode_text = f"Roll:{student.roll_no or ''}, Reg:{student.registration_no or ''}, Name:{student.get_full_name()}, Sem:{semester_label}"
        barcode_base64 = generate_barcode_base64(barcode_text)

        attendance_data.append({
            'name': student.get_full_name(),
            'registration_no': student.registration_no or "-",
            'roll_no': student.roll_no or "-",
            'college_name': student.college.name if student.college else "-",
            'photo': image_to_base64(student.profile_image.path if student.profile_image else None),
            'schedules': student_schedules,
            'barcode': barcode_base64
        })

    # Header like: MCA-1ST-REGULAR-MCA
    exam_header = f"MCA-{exam.semester}"

    context = {
        "attendance_data": attendance_data,
        "center_name": center_name,
        "exam_header": exam_header,
        "university_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
    }

    html_string = get_template("mca_sem/attendance_sheet.html").render(context)

    try:
        return HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
    except Exception as e:
        logger.error(f"Attendance Sheet PDF generation failed: {str(e)}")
        return None
