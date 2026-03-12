import base64
import io
import os
from django.conf import settings
from django.template.loader import get_template
from weasyprint import HTML
import qrcode
from llb.utils.generate_llb_barcode_text import generate_llb_barcode_text
from llb.utils.calculate_res import calculate_llb_result

def image_to_base64(path):
    """
    Convert an image file to a base64 string.
    
    Args:
        path: Absolute file path to the image
        
    Returns:
        str: Base64 encoded string of the image, or empty string if file not found
    """
    import os
    import base64
    
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    return ""

def generate_marksheet_pdf(result, semester=None):
    """
    Generates a PDF marksheet for a given LLBResult object using WeasyPrint.
    If semester is provided, only assessments for that semester will be included.
    """
    # 1. Generate QR Code
    barcode_text = generate_llb_barcode_text(result)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(barcode_text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert image to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # 3. Get assessments (filtered by semester if provided)
    if hasattr(result, '_filtered_assessments'):
        assessments = result._filtered_assessments
    elif semester:
        assessments = result.student_assessments_result.filter(semester=semester)
    else:
        assessments = result.student_assessments_result.all()

    # 4. Calculate result statistics
    result_stats = calculate_llb_result(assessments)

    # 5. Context for the template
    context = {
        'result': result,
        'student': result.student,
        'assessments': assessments,
        'qr_code': qr_code_base64,
        'pass_percentage': 33,
        'exam_name': result.exam.name if result.exam else 'LLB Examination',
        'exam_year': result.exam.session if result.exam else '',
        'batch_year': result.student.batch.name if result.student.batch else '',
        'exam_month_year': result.exam.exam_month_year if result.exam else '',
        'course': result.student.course.name if result.student.course else '-',
        'center_name': result.exam.center_mappings.first().center.name if result.exam and result.exam.center_mappings.exists() else '-',
        
        # Result statistics
        'total_full_marks': result_stats['total_full_marks'],
        'total_obtained_marks': result_stats['total_obtained_marks'],
        'calculated_result_status': result_stats['result_status'],
        'result_display': result_stats['result_display'],
        'percentage': result_stats['percentage'],

        # Images
        'university_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'watermark_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/controller-of-examination-signature.png")),
    }
    
    # 4. Render Template
    template_path = 'llb/detailed_marksheet_LLB_1.html'
    try:
        template = get_template(template_path)
        html = template.render(context)
        
        # Debug: Check if template rendered correctly
        if '{{' in html or '{%' in html:
            print("WARNING: Template not fully rendered! Raw template syntax found in HTML.")
            print(f"Context keys: {context.keys()}")
        
    except Exception as e:
        print(f"Error rendering template: {e}")
        return None
    
    # 5. Generate PDF using WeasyPrint
    try:
        pdf = HTML(string=html).write_pdf()
        return pdf
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None
