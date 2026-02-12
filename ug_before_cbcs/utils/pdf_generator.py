from django.template.loader import get_template
from django.conf import settings
from ug_before_cbcs.models import (
    UGBeforeCBCSExamRegistration,
    UGBeforeCBCSStudentAssessment,
    UGBeforeCBCSExamResult
)
from pup_umis_backend.utils.file_utils import image_to_base64
import os
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

def num2words(num):
    """
    Simple number to words converter for marks.
    Only supports up to 999 for now as marks don't exceed that.
    """
    if not isinstance(num, (int, float, Decimal)):
        return ""
    
    num = int(num)
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    if num == 0: return "Zero"
    
    words = []
    
    if num >= 100:
        words.append(units[num // 100] + " Hundred")
        num %= 100
        
    if num >= 20:
        words.append(tens[num // 10])
        num %= 10
        if num > 0:
            words.append(units[num])
    elif num >= 10:
        words.append(teens[num - 10])
    elif num > 0:
        words.append(units[num])
        
    return " ".join(words)

def generate_ug_old_marksheet_pdf(student, exam_part):
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        logger.error("WeasyPrint not installed.")
        return None

    # 1. Get the latest registration
    registration = UGBeforeCBCSExamRegistration.objects.filter(
        student=student,
        exam__part=exam_part
    ).select_related('exam', 'center', 'student__college', 'student__discipline').order_by('-created_at').first()

    if not registration:
        logger.warning(f"No registration found for {student.registration_no} / {exam_part}")
        return None

    # 2. Get Assessments
    assessments = UGBeforeCBCSStudentAssessment.objects.filter(
        registration=registration
    ).select_related('subject')

    # 3. Get Result Summary
    result_summary = UGBeforeCBCSExamResult.objects.filter(registration=registration).first()

    # 4. Group Papers
    honours_papers = []
    subsidiary_papers = []
    composition_papers = []
    general_studies_papers = []

    # Helper to clean marks
    def clean_mark(val):
        if val is None: return 0
        if isinstance(val, (int, float, Decimal)): return int(val)
        if str(val).isdigit(): return int(val)
        return val # Return as string (ABS, etc.)

    student_discipline = student.discipline.name.upper() if student.discipline and student.discipline.name else ""

    for assess in assessments:
        sub_name = assess.subject.name.upper()
        
        # Paper Data Structure
        paper_data = {
            'name': assess.subject.name,
            'max_marks': assess.max_marks or 100, # Default to 100 if null
            'pass_marks': assess.pass_marks or 33, # Default
            'obtained': clean_mark(assess.marks_secured)
        }
        
        # Identification Logic
        is_honours = False
        if assess.subject_type == 'HONOURS':
            is_honours = True
        elif student_discipline and student_discipline in sub_name:
            is_honours = True
        
        if is_honours:
            honours_papers.append(paper_data)
        elif exam_part == 'PART3' and ('GES' in sub_name or 'GENERAL' in sub_name or 'STUDIES' in sub_name):
             general_studies_papers.append(paper_data)
        elif 'HINDI' in sub_name or 'MB' in sub_name or 'COMP' in sub_name or 'RB' in sub_name:
            composition_papers.append(paper_data)
        else:
            subsidiary_papers.append(paper_data)

    # Sort Honours Papers
    honours_papers.sort(key=lambda x: x['name'])

    # Assign Subsidiaries (Only for Part 1/2)
    sub1 = subsidiary_papers[0] if len(subsidiary_papers) > 0 else None
    sub2 = subsidiary_papers[1] if len(subsidiary_papers) > 1 else None

    # Calculate Totals
    def sum_marks(papers):
        total = 0
        for p in papers:
            if isinstance(p['obtained'], (int, float)):
                total += p['obtained']
        return total

    def sum_max(papers):
        return sum(p['max_marks'] for p in papers)

    hons_total_obt = sum_marks(honours_papers)
    hons_total_max = sum_max(honours_papers)
    
    comp_total_obt = sum_marks(composition_papers)
    comp_total_max = sum_max(composition_papers)
    
    gs_total_obt = sum_marks(general_studies_papers)
    gs_total_max = sum_max(general_studies_papers)

    # Prepare Context
    context = {
        'student': student,
        'exam_name': registration.exam.name,
        'exam_month': registration.exam.exam_month_year,
        'hons_subject': student.discipline.name if student.discipline else "General",
        'center_name': registration.center.name if registration.center else "N/A",
        
        'subjects': {
            'honours': {
                'name': student.discipline.name if student.discipline else "Honours",
                'papers': honours_papers,
                'total_max': hons_total_max,
                'total_pass': int(hons_total_max * 0.45),
                'total_obtained': hons_total_obt
            },
            'subsidiary_1': sub1,
            'subsidiary_2': sub2,
            'composition': {
                'papers': composition_papers,
                'total_max': comp_total_max,
                'total_pass': int(comp_total_max * 0.33),
                'total_obtained': comp_total_obt
            },
            'general_studies': {
                'papers': general_studies_papers,
                'total_max': gs_total_max,
                'total_pass': int(gs_total_max * 0.33),
                'total_obtained': gs_total_obt
            }
        },
        'grand_total': clean_mark(result_summary.grand_total_secured) if result_summary else "N/A",
        'result_status': result_summary.result_status if result_summary else "PENDING",
        'hons_total_words': num2words(hons_total_obt) + " Only",
        'publication_date': "20-04-2023", # Placeholder or from exam
        
        'university_logo': image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        'watermark_logo': image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
    }

    # Render
    if exam_part == 'PART3':
        template_name = "ug_before_cbcs/marksheet_part3.html"
    elif exam_part == 'PART2':
        template_name = "ug_before_cbcs/marksheet_part2.html"
    else:
        template_name = "ug_before_cbcs/marksheet_part1.html"

    html_string = get_template(template_name).render(context)
    
    try:
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        return pdf_file
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return None
