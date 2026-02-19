import base64
import requests
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
import os
from PIL import Image, ImageOps
import qrcode

def get_base64_image(image_file_or_url):
    """
    Convert an image (FileField or URL) to base64 string using Pillow.
    Robustly handles S3 (boto3), Local Storage, and HTTP URLs.
    """
    if not image_file_or_url:
        return None
        
    img = None
    
    try:
        # 1. Try Django Storage (.open) - Works for S3 & Local
        if hasattr(image_file_or_url, 'open'):
            try:
                with image_file_or_url.open('rb') as f:
                    img = Image.open(BytesIO(f.read()))
            except Exception as e:
                print(f"Storage open failed: {e}")
                
                # 2. Fallback: Try Local Filesystem Path directly
                try:
                    if hasattr(image_file_or_url, 'path') and os.path.exists(image_file_or_url.path):
                        with open(image_file_or_url.path, 'rb') as f:
                            img = Image.open(BytesIO(f.read()))
                except Exception:
                    pass

        # 3. Fallback: Try HTTP URL (External or S3 signed/public URL)
        if img is None:
            url = None
            if isinstance(image_file_or_url, str):
                url = image_file_or_url
            elif hasattr(image_file_or_url, 'url'):
                url = image_file_or_url.url
                
            if url and url.startswith('http'):
                try:
                    response = requests.get(url, timeout=5, stream=True)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                except Exception as e:
                    print(f"URL Fetch failed: {e}")

        # 4. Final Processing
        if img:
            try:
                img = ImageOps.exif_transpose(img) 
            except: 
                pass
                
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{b64_data}"
            
    except Exception as e:
        print(f"Critical error in get_base64_image: {e}")
        return None
    return None

def generate_qr_code_base64(data):
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64_data}"

def generate_voc_registration_card(registration):
    """
    Generate Registration Card PDF for a VOC student using WeasyPrint
    """
    buffer = BytesIO()
    
    # Prepare Images
    profile_image_src = get_base64_image(registration.profile_picture)
    signature_src = get_base64_image(registration.signature)
    
    # Load assets (signatures and university logo)
    # They are now expected to be in global static/images/
    assets_path = os.path.join(settings.BASE_DIR, 'static', 'images')
    
    def get_asset_b64(filename):
        path = os.path.join(assets_path, filename)
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
            except Exception as e:
                print(f"Error reading asset {filename}: {e}")
        return None

    # Official Signatures from global static images
    sig_assistant_src = get_asset_b64('sig_assistant.png')
    sig_deputy_src = get_asset_b64('sig_deputy.png')
    sig_registrar_src = get_asset_b64('sig_registrar.png')
    
    # QR Code Data
    qr_data = (
        f"Name: {registration.student_name}\n"
        f"Registration No: {registration.registration_number or 'N/A'}\n"
        f"Course: {registration.course.name if registration.course else 'N/A'}\n"
        f"College: {registration.college.name if registration.college else 'N/A'}"
    )
    qr_code_src = generate_qr_code_base64(qr_data)
    
    # Prepare Context
    context = {
        'reg': registration,
        'display_data': {
            'registrationNo': registration.registration_number or 'N/A',
            'name': registration.student_name,
            'motherName': registration.mother_name or 'N/A',
            'fatherName': registration.father_name or 'N/A',
            'course': registration.course.name if registration.course else 'N/A',
            'collegeName': registration.college.name if registration.college else 'N/A',
            'session': registration.session.name if registration.session else (registration.batch.name if registration.batch else 'N/A'),
            'serialNumber': str(registration.sr_no).zfill(5) if registration.sr_no else '______',
            'studentPhoto': profile_image_src,
            'signature': signature_src,
        },
        'qr_code_src': qr_code_src,
        'signatures': {
            'assistant': sig_assistant_src,
            'deputy': sig_deputy_src,
            'registrar': sig_registrar_src,
        }
    }
    
    # Render HTML
    html_string = render_to_string('voc_new_registration/registration_card.html', context)
    
    # Generate PDF
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(target=buffer)
    
    buffer.seek(0)
    return buffer
