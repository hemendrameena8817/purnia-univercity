import base64
import io
import os
from types import SimpleNamespace
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

def safe_marks_to_int(marks):
    """Safely convert marks to integer, handling non-numeric values like 'AB' for absent students."""
    if marks is None:
        return 0
    try:
        return int(float(marks))
    except (ValueError, TypeError):
        # If marks is a string like 'AB' or cannot be converted, treat as 0
        return 0

def get_display_marks(marks):
    """Get marks for display - returns 'AB' as 'AB', numeric values as-is."""
    if marks is None:
        return 0
    try:
        # Try to convert to float and back to int to clean up numeric values
        return int(float(marks))
    except (ValueError, TypeError):
        # If conversion fails, return the original value (like 'AB')
        return marks

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


def build_semester2_display_rows(assessments):
    theory_rows = []
    practical_rows = []
    combined_map = {}

    for assessment in assessments:
        course_structure = getattr(assessment, 'course_structure', None)
        if not course_structure:
            continue

        course_code = (getattr(course_structure, 'course_code', '') or '').upper()
        status = (getattr(course_structure, 'status', '') or '').upper()

        if course_code in ('IX', 'X'):
            if course_code not in combined_map:
                combined_map[course_code] = {
                    'name': course_structure.name or '-',
                    'course_code': course_code,
                    'full_marks': 0,
                    'pass_marks': 0,
                    'obtained_marks': 0,
                    'display_marks': 0,
                }

            combined_map[course_code]['name'] = course_structure.name or combined_map[course_code]['name']
            combined_map[course_code]['full_marks'] += int(course_structure.full_marks or 0)
            combined_map[course_code]['pass_marks'] += int(course_structure.pass_marks or 0)
            combined_map[course_code]['obtained_marks'] += safe_marks_to_int(assessment.ind_marks_obtained)
            # For combined courses, if any assessment has 'AB', show as 'AB' in display
            current_display = combined_map[course_code]['display_marks']
            assessment_display = get_display_marks(assessment.ind_marks_obtained)
            if isinstance(assessment_display, str) and assessment_display == 'AB':
                combined_map[course_code]['display_marks'] = 'AB'
            elif current_display != 'AB':
                combined_map[course_code]['display_marks'] = (
                    current_display + safe_marks_to_int(assessment.ind_marks_obtained)
                    if isinstance(current_display, (int, float)) else safe_marks_to_int(assessment.ind_marks_obtained)
                )
            continue

        row = {
            'name': course_structure.name or '-',
            'course_code': course_structure.course_code or '-',
            'full_marks': int(course_structure.full_marks or 0),
            'pass_marks': int(course_structure.pass_marks or 0),
            'obtained_marks': safe_marks_to_int(assessment.ind_marks_obtained),  # For calculations
            'display_marks': get_display_marks(assessment.ind_marks_obtained),  # For display
        }

        if status == 'ESE':
            theory_rows.append(row)
        elif status == 'CIA':
            practical_rows.append(row)

    for course_code in ('IX', 'X'):
        if course_code in combined_map:
            practical_rows.append(combined_map[course_code])

    return theory_rows, practical_rows


def generate_marksheet_pdf(result=None, semester=None, student=None, exam=None, assessments=None, grace=None, total_marks=None):
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

    student = student or getattr(result, 'student', None)
    exam = exam or getattr(result, 'exam', None)
    if assessments is None:
        if result is not None and hasattr(result, '_filtered_assessments'):
            assessments = result._filtered_assessments
        else:
            assessments = student.course_assessments.filter(exam=exam, semester=semester).select_related('course_structure').order_by('paper_code')
    if result is None:
        result = SimpleNamespace(student=student, exam=exam, grace=grace, total_marks=total_marks)

    # 1. Calculate result statistics
    if semester == '3RD':
        cumulative_assessments = student.course_assessments.filter(
            semester__in=['1ST', '2ND', '3RD']
        ).select_related('course_structure').order_by('semester', 'paper_code')
        result_stats = calculate_llb_result_semester_3(cumulative_assessments)
    else:
        result_stats = calculate_llb_result(assessments)

    # 2. Generate QR Code
    barcode_text = generate_llb_barcode_text(
        result=result,
        semester=semester,
        student=student,
        exam=exam,
        assessments=assessments,
        total_full_marks=result_stats['total_full_marks'],
        total_obtained_marks=result_stats['total_obtained_marks'],
    )
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
        'student': student,
        'assessments': assessments,
        'qr_code': qr_code_base64,
        'pass_percentage': 33,
        'exam_name': exam.name if exam else 'LLB Examination',
        'exam_year': exam.session if exam else '',
        'batch_year': student.batch.name if student and student.batch else '',
        'exam_month_year': exam.exam_month_year if exam else '',
        'course': student.course.name if student and student.course else '-',
        'center_name': None,
        
        # Result statistics
        'total_full_marks': result_stats['total_full_marks'],
        'total_pass_marks': result_stats['total_pass_marks'],
        'total_obtained_marks': result_stats['total_obtained_marks'],
        'calculated_result_status': result_stats['result_status'],
        'result_display': result_stats['result_display'],
        'percentage': result_stats['percentage'],

        # Images
        'university_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        # 'watermark_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/controller-of-examination-signature.png")),
    }
    
    # 6. Get center information
    if exam and student:
        from .progressive_context import get_center_info_for_student
        center_info = get_center_info_for_student(student, exam)
        if center_info:
            context['center_name'] = center_info.get('name', '-')
        else:
            context['center_name'] = '-'

    if semester == '2ND':
        theory_rows, practical_rows = build_semester2_display_rows(assessments)
        context.update({
            'ese_full_marks': result_stats['ese_full_marks'],
            'ese_obtained_marks': result_stats['ese_obtained_marks'],
            'cia_full_marks': result_stats['cia_full_marks'],
            'cia_obtained_marks': result_stats['cia_obtained_marks'],
            'theory_rows': theory_rows,
            'practical_rows': practical_rows,
            'cia_pass_marks': sum(row['pass_marks'] for row in practical_rows),
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
