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
            student_subject_ids = list(reg.backlog_subjects.all().values_list('id', flat=True))
        
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
