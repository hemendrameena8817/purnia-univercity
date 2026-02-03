def generate_mca_admit_card_pdf(student, exam):
    from weasyprint import HTML, CSS
    import io, base64, os
    from django.conf import settings
    from django.template.loader import get_template
    from mca_sem.models import MCAExamCenterMapping, MCAExamSchedule
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

    def to_base64(path):
        """Convert image file to base64 string"""
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return ""
    # Prepare context for template
    context = {
        "exam": exam,
        "student": student,
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.college_code if exam_center else "-",
        "schedules": schedules,
        "university_logo": to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "student_photo": to_base64(student.profile_image.path if student.profile_image else None),
        "student_sig": to_base64(student.signature.path if student.signature else None),
        "controller_signature": to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
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
