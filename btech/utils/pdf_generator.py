def generate_btech_admit_card_pdf(student, exam):
    from weasyprint import HTML, CSS
    import io, base64, os
    from django.conf import settings
    from django.template.loader import get_template
    from btech.models import BTechExamCenterMapping, BTechExamSchedule, BTechExamRegistration
    from pup_umis_backend.utils.file_utils import image_to_base64
    import logging

    logger = logging.getLogger(__name__)

    # Get exam center mapping
    exam_center = None
    if student.college:
        mapping = BTechExamCenterMapping.objects.filter(
            exams=exam,
            attached_colleges=student.college
        ).first()
        if mapping:
            exam_center = mapping.center
    
    # Get the latest exam registration for this student and exam
    registration = BTechExamRegistration.objects.filter(
        student=student,
        exam=exam
    ).order_by('-created_at').first()

    # Get exam schedules
    schedules_query = BTechExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure')

    if registration and registration.exam_type in ['BACK', 'IMPROVEMENT']:
        # Filter schedules to only include subjects selected for backlog/improvement
        backlog_ids = registration.backlog_subjects.values_list('id', flat=True)
        schedules = schedules_query.filter(common_course_structure_id__in=backlog_ids)
    else:
        # Default behavior: show all schedules for the exam
        schedules = schedules_query


    # Prepare context for template
    context = {
        "exam": exam,
        "student": student,
        "registration": registration,
        "exam_type": registration.exam_type if registration else "REGULAR",
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.center_code if exam_center else "-",
        "schedules": schedules,
        "university_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "watermark_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "student_photo": image_to_base64(student.profile_image.path if student.profile_image else None),
        "student_sig": image_to_base64(student.signature.path if student.signature else None),
        "controller_signature": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
    }

    # Render HTML template
    html_string = get_template("btech/admit_card.html").render(context)

    try:
        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        
        logger.info(f"PDF generated successfully using WeasyPrint, size: {len(pdf_file)} bytes")
        return pdf_file
        
    except Exception as e:
        logger.error(f"PDF generation failed with WeasyPrint: {str(e)}")
        return None
