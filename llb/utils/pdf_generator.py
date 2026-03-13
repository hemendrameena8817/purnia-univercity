import base64
import io
import os
from django.conf import settings
from django.template.loader import get_template
from weasyprint import HTML
import qrcode
from llb.utils.generate_llb_barcode_text import generate_llb_barcode_text
from llb.utils.calculate_res import calculate_llb_result, calculate_llb_result_semester_3

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

def group_assessments_for_semester3(assessments):
    """
    Groups assessments by course_code for 3rd semester stacked display.
    Each group is a list with ESE first, CIA second (if both exist).
    Returns a list of groups (each group is a list of assessments).
    """
    from collections import OrderedDict
    groups = OrderedDict()
    for a in assessments:
        code = (a.course_structure.course_code if a.course_structure else '') or (getattr(a, 'paper_code', '') or '')
        if code not in groups:
            groups[code] = []
        # ESE goes first (top row), CIA goes second (bottom row)
        if a.course_structure and a.course_structure.status == 'ESE':
            groups[code].insert(0, a)
        else:
            groups[code].append(a)
    return list(groups.values())


def generate_marksheet_pdf(result, semester=None):
    """
    Generates a PDF marksheet for a given LLBResult object using WeasyPrint.
    If semester is provided, only assessments for that semester will be included.
    Uses different templates for different semesters.
    """
    # Determine which template to use based on semester
    if semester == '1ST':
        template_path = 'llb/detailed_marksheet_LLB_1.html'
    elif semester == '2ND':
        template_path = 'llb/detailed_marksheet_LLB_2.html'
    elif semester == '3RD':
        template_path = 'llb/detailed_marksheet_LLB_3.html'
    else:
        print(f"PDF generation skipped: Only 1ST, 2ND, and 3RD semesters supported (got: {semester})")
        return None
    
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
    if semester == '3RD':
        # Query from student directly to get assessments across ALL semesters (not just this result)
        cumulative_assessments = result.student.course_assessments.filter(
            semester__in=['1ST', '2ND', '3RD']
        ).select_related('course_structure').order_by('semester', 'paper_code')
        result_stats = calculate_llb_result_semester_3(cumulative_assessments)
    else:
        result_stats = calculate_llb_result(assessments)
    
    # 4.6. Convert marks to words for 3rd semester
    def number_to_words(n):
        """Convert number to words (Indian English)"""
        if n == 0:
            return "Zero"
        
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", 
                 "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        def convert_below_thousand(num):
            if num == 0:
                return ""
            elif num < 10:
                return ones[num]
            elif num < 20:
                return teens[num - 10]
            elif num < 100:
                return tens[num // 10] + (" " + ones[num % 10] if num % 10 != 0 else "")
            else:
                return ones[num // 100] + " Hundred" + (" " + convert_below_thousand(num % 100) if num % 100 != 0 else "")
        
        if n < 1000:
            return convert_below_thousand(n)
        elif n < 100000:
            thousands = n // 1000
            remainder = n % 1000
            result = convert_below_thousand(thousands) + " Thousand"
            if remainder > 0:
                result += " " + convert_below_thousand(remainder)
            return result
        else:
            return str(n)  # Fallback for very large numbers
    
    marks_in_words = number_to_words(result_stats['total_obtained_marks']) + " Only"

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
        'total_pass_marks': result_stats['total_pass_marks'],
        'total_obtained_marks': result_stats['total_obtained_marks'],
        'calculated_result_status': result_stats['result_status'],
        'result_display': result_stats['result_display'],
        'percentage': result_stats['percentage'],

        # Images
        'university_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'watermark_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/controller-of-examination-signature.png")),
    }

    if semester == '2ND':
        context.update({
            'ese_full_marks': result_stats['ese_full_marks'],
            'ese_obtained_marks': result_stats['ese_obtained_marks'],
            'cia_full_marks': result_stats['cia_full_marks'],
            'cia_obtained_marks': result_stats['cia_obtained_marks'],
        })

    if semester == '3RD':
        context.update({
            'total_pass_marks': 1260,
            'part3_full_marks': result_stats.get('part3_full_marks', 0),
            'part3_pass_marks': 450,
            'part3_obtained_marks': result_stats.get('part3_obtained_marks', 0),
            'part2_full_marks': result_stats.get('part2_full_marks', 0),
            'part2_pass_marks': 450,
            'part2_obtained_marks': result_stats.get('part2_obtained_marks', 0),
            'part1_full_marks': result_stats.get('part1_full_marks', 0),
            'part1_pass_marks': 360,
            'part1_obtained_marks': result_stats.get('part1_obtained_marks', 0),
            'marks_in_words': marks_in_words,
            'grouped_assessments': group_assessments_for_semester3(assessments),
        })
    
    # 4. Render Template
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
