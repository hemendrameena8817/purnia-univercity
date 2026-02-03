import base64
import io
import os
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
import qrcode
from plw.utils.generate_plw_barcode_text import generate_plw_barcode_text

def generate_marksheet_pdf(result):
    """
    Generates a PDF marksheet for a given PLWResult object.
    """
    # 1. Generate QR Code
    barcode_text = generate_plw_barcode_text(result)
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
    }
    
    # 3. Render Template
    template_path = 'plw/detailed_marksheet_PLW.html'
    template = get_template(template_path)
    html = template.render(context)
    
    # 4. Create PDF
    result_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        io.BytesIO(html.encode("utf-8")),
        dest=result_buffer
    )
    
    if pisa_status.err:
        return None
        
    return result_buffer.getvalue()
