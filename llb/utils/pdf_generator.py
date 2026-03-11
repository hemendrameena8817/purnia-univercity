import base64
import io
import os
from django.conf import settings
from django.template.loader import get_template
from weasyprint import HTML
import qrcode
from llb.utils.generate_llb_barcode_text import generate_llb_barcode_text

def generate_marksheet_pdf(result):
    """
    Generates a PDF marksheet for a given LLBResult object using WeasyPrint.
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
    
    # 2. Add University Logo
    logo_path = os.path.join(settings.MEDIA_ROOT, 'common', 'purnea-logo.png')
    university_logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            university_logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    # 3. Context for the template
    context = {
        'result': result,
        'student': result.student,
        'qr_code': qr_code_base64,
        'university_logo': university_logo_base64,
        'pass_percentage': 33,
        'exam_name': result.exam.name if result.exam else 'LLB Examination',
        'exam_year': result.exam.session if result.exam else '',
        'batch_year': result.student.batch.name if result.student.batch else '',
        'exam_month_year': result.exam.exam_month_year if result.exam else '',
        'hons_subject': result.student.course.name if result.student.course else '',
        'center_name': result.student.college.name if result.student.college else '',
    }
    
    # 4. Render Template
    template_path = 'llb/detailed_marksheet_LLB_1.html'
    template = get_template(template_path)
    html = template.render(context)
    
    # 5. Generate PDF using WeasyPrint
    try:
        pdf = HTML(string=html).write_pdf()
        return pdf
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None
