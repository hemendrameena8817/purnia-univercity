import base64
import requests
from django.core.files.storage import default_storage
from weasyprint import HTML
from django.template.loader import render_to_string
from io import BytesIO
from django.conf import settings
import os

from PIL import Image, ImageOps

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
                # We interpret file content as BytesIO for Pillow
                # .open('rb') ensures we get bytes even from S3
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
                # Handle cases where .url might be relative or absolute
                url = image_file_or_url.url
                
            if url and url.startswith('http'):
                try:
                    response = requests.get(url, timeout=5, stream=True)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                except Exception as e:
                    print(f"URL Fetch failed: {e}")

        # 4. Final Processing: Convert to RGB JPEG (strips EXIF/Target Errors)
        if img:
            # Handle Orientation/EXIF if present (optional but good practice)
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

def generate_registration_card(student, registration, assessments):
    """
    Generate Registration Card PDF for a student using WeasyPrint
    """
    buffer = BytesIO()
    
    # Organize Courses by Type
    mjc_courses = []
    mic_courses = []
    mdc_courses = []
    aec_courses = []
    sec_courses = []
    
    # Use unique paper codes to avoid duplicates
    seen_codes = set()
    unique_assessments = []
    
    for a in assessments:
        code = a.paper_code or a.course_code
        if code not in seen_codes:
            seen_codes.add(code)
            unique_assessments.append(a)
            
    for a in unique_assessments:
        # User requested to show Course Code (e.g. MJC-3) instead of Paper Code
        # We prioritize course_code for display
        display_code = a.course_code if a.course_code else a.paper_code
        
        name = a.course_name
        ctype = (a.course_type or "").upper()
        ccode = (a.course_code or "").upper()
        
        item = {
            'code': display_code,
            'name': name,
            'dept': a.department.name if a.department else ""
        }
        
        if ctype.startswith("MJC") or ccode.startswith("MJC"):
            mjc_courses.append(item)
        elif ctype.startswith("MIC") or ccode.startswith("MIC"):
            mic_courses.append(item)
        elif ctype.startswith("MDC") or ccode.startswith("MDC"):
            mdc_courses.append(item)
        elif ctype.startswith("AEC") or ccode.startswith("AEC") or ccode.startswith("AECC"):
            aec_courses.append(item)
        elif ctype.startswith("SEC") or ccode.startswith("SEC"):
            sec_courses.append(item)
    
    # Sort courses by their code to ensure consistent order (e.g. MJC-3 before MJC-4)
    mjc_courses.sort(key=lambda x: x['code'] or '')
    mic_courses.sort(key=lambda x: x['code'] or '')
    mdc_courses.sort(key=lambda x: x['code'] or '')
    aec_courses.sort(key=lambda x: x['code'] or '')
    sec_courses.sort(key=lambda x: x['code'] or '')

    # Subject Names
    major_subject_name = student.major_course.name if student.major_course else (mjc_courses[0]['dept'] if mjc_courses else "")
    minor_subject_name = student.minor_course.name if student.minor_course else (mic_courses[0]['dept'] if mic_courses else "")
    mdc_subject_name = student.mdc_course.name if student.mdc_course else (mdc_courses[0]['dept'] if mdc_courses else "")
    
    # Semester Text
    # Semester Text
    sem = registration.sem
    suffix = "TH"
    if sem == 1: suffix = "ST"
    elif sem == 2: suffix = "ND"
    elif sem == 3: suffix = "RD"
    sem_text = f"{sem}{suffix}"
    
    # Prepare Images
    profile_image_src = get_base64_image(student.profile_image)
    signature_src = get_base64_image(student.signature)
    
    # Logo (Prioritize local static file)
    base_static_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images')
    logo_path = os.path.join(base_static_path, 'purnea-logo.png')
    logo_src = None
    
    if os.path.exists(logo_path):
        try:
            with open(logo_path, 'rb') as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')
                logo_src = f"data:image/png;base64,{b64_data}"
        except Exception as e:
            print(f"Error loading local logo: {e}")
    # Fixed Signatures (from static/ug/images/)
    # Ensure these files exist at: pup-umis-backend/ug/static/ug/images/
    base_static_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images')
    
    # Sig 1: Assistan
    sig_assistant_path = os.path.join(base_static_path, 'sig_assistant.png')
    sig_assistant_src = None
    if os.path.exists(sig_assistant_path):
        with open(sig_assistant_path, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
            sig_assistant_src = f"data:image/png;base64,{b64_data}"
            
    # Sig 2: Deputy Registrar
    sig_deputy_path = os.path.join(base_static_path, 'sig_deputy.png')
    sig_deputy_src = None
    if os.path.exists(sig_deputy_path):
        with open(sig_deputy_path, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
            sig_deputy_src = f"data:image/png;base64,{b64_data}"
            
    # Sig 3: Registrar
    sig_registrar_path = os.path.join(base_static_path, 'sig_registrar.png')
    sig_registrar_src = None
    if os.path.exists(sig_registrar_path):
        with open(sig_registrar_path, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
            sig_registrar_src = f"data:image/png;base64,{b64_data}"

    # Prepare Context
    context = {
        'student': {
            'registration_no': student.registration_no,
            'full_name': f"{student.first_name} {student.last_name or ''}".strip(),
            'mother_name': student.mother_name,
            'father_name': student.father_name,
            'gender': student.gender,
            'profile_image_url': profile_image_src, # Now Base64
            'signature_url': signature_src,         # Now Base64
        },
        'logo_url': logo_src,
        'college_name': student.user.college.name if student.user.college else "",
        'course_name': student.program.name.split('-')[0].strip() if student.program else "-",
        'semester_text': sem_text,
        'session': registration.batch.name,
        
        'major_subject_name': major_subject_name,
        'minor_subject_name': minor_subject_name,
        'mdc_subject_name': mdc_subject_name,
        
        'mjc_courses': mjc_courses,
        'mic_courses': mic_courses,
        'mdc_courses': mdc_courses,
        'aec_courses': aec_courses,
        'sec_courses': sec_courses,
        
        'signatures': {
            'assistant': sig_assistant_src,
            'deputy': sig_deputy_src,
            'registrar': sig_registrar_src,
        }
    }
    
    # Render HTML
    html_string = render_to_string('ug/registration_card.html', context)
    
    # Generate PDF
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(target=buffer)
    
    buffer.seek(0)
    return buffer
