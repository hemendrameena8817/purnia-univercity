from django.template.loader import get_template
from django.conf import settings
from ug_before_cbcs.models import (
    UGBeforeCBCSStudentProfile,

    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult,

)
from pup_umis_backend.utils.file_utils import image_to_base64
from ug_before_cbcs.utils.qr_generator import generate_qr_code_base64, generate_ug_marksheet_qr_text
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

def get_ug_old_ba_hons_marksheet_context(student, exam_part, exam_type=None):
    """
    Prepares and returns the context dictionary for the UG Before CBCS BA Hons marksheet.
    """
    """
    Generate marksheet PDF for UG Before CBCS student using simplified models.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam_part: Part number as string ('1', '2', or '3')
    
    Returns:
        PDF bytes or None
    """
    # Convert part to uppercase format (PART1, PART2, PART3)
    part_code = f"PART{exam_part}"

    # 1. Get student results for this part, filtering by exam_type if provided
    results_query = UGBeforeCBCSStudentResult.objects.filter(
        student=student,
        exam__part=part_code
    )
    
    if exam_type:
        results_query = results_query.filter(exam_type__iexact=exam_type)
        
    first_result = results_query.select_related('exam', 'subject').order_by('-exam__exam_year').first()

    if not first_result:
        logger.warning(f"No results found for {student.registration_no} / {part_code}")
        return None

    exam = first_result.exam

    # 2. Get all student results for this exam
    results = UGBeforeCBCSStudentResult.objects.filter(
        student=student,
        exam=exam
    ).select_related('subject').order_by('subject__paper_code')

    # 3. Get exam summary
    # Exam summary fields are now part of StudentResult; aggregate as needed.
    summary = None  # Set to None or aggregate from results if needed.

    # 4. Group Papers by subject type
    honours_papers = []
    subsidiary_papers = []
    composition_papers = []
    general_studies_papers = []

    # Helper to clean marks
    def clean_mark(val):
        if val is None: return 0
        if isinstance(val, (int, float, Decimal)): return int(val)
        try:
            return int(val)
        except (ValueError, TypeError):
            return val  # Return as string (ABS, UFM, etc.)

    # Get discipline from student's discipline_code
    student_discipline = student.discipline_code.upper() if student.discipline_code else ""

    for result in results:
        subject = result.subject
        sub_name = subject.subject_name.upper() if subject.subject_name else ""
        
        # Calculate total marks obtained (theory + practical + sessional)
        theory_marks = clean_mark(result.theory)
        practical_marks = clean_mark(result.practical)
        sessional_marks = clean_mark(result.sessional)
        
        # Sum only numeric marks
        total_obtained = 0
        for mark in [theory_marks, practical_marks, sessional_marks]:
            if isinstance(mark, (int, float)):
                total_obtained += mark
        
        # Paper Data Structure
        paper_data = {
            'name': subject.subject_name or subject.paper_code,
            'paper_code': subject.paper_code,
            'status': result.status.upper() if result.status else '',
            'max_marks': clean_mark(result.maximum_mark) or 100,
            'pass_marks': clean_mark(result.pass_mark) or 33,
            'obtained': clean_mark(result.mark_secured) or total_obtained
        }
        
        # Identification Logic: Prioritize paper_type_code
        is_honours = False
        if subject.paper_type_code and subject.paper_type_code.upper() == 'HONS':
            is_honours = True
        elif subject.subject_type and 'HON' in subject.subject_type.upper():
            is_honours = True
        elif student_discipline and student_discipline in sub_name:
            is_honours = True
        
        if is_honours:
            honours_papers.append(paper_data)
        elif part_code == 'PART3' and ('GES' in sub_name or 'GENERAL' in sub_name or 'STUDIES' in sub_name):
            general_studies_papers.append(paper_data)
        elif 'HINDI' in sub_name or 'MB' in sub_name or 'COMP' in sub_name or 'RB' in sub_name or 'COMPOSITION' in sub_name:
            composition_papers.append(paper_data)
        else:
            subsidiary_papers.append(paper_data)

    # Organize and rename Honours papers
    is_honours_with_practical = False
    organized_honours = []
    paper1 = None
    paper2 = None
    practical = None

    for p in honours_papers:
        if p['paper_code'] == '101':
            if p['status'] == 'END_TERM':
                paper1 = p
                paper1['name'] = 'Paper-I'
            elif p['status'] == 'END2_TERM':
                paper2 = p
                paper2['name'] = 'Paper-II'
            elif p['status'] == 'LAB':
                practical = p
                practical['name'] = 'Practical'
                is_honours_with_practical = True
        else:
            # For other honours papers that are not '101'
            organized_honours.append(p)

    # Add in specific order
    if paper1: organized_honours.append(paper1)
    if paper2: organized_honours.append(paper2)
    if practical: organized_honours.append(practical)
    
    honours_papers = organized_honours

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

    # Get full honours subject name from the first honours paper
    honours_subject_name = "Honours"
    if honours_papers and len(honours_papers) > 0:
        honours_subject_name = honours_papers[0]['name']
    elif student.discipline_code:
        honours_subject_name = student.discipline_code

    # Prepare Context
    context = {
        'is_honours_with_practical': is_honours_with_practical,
        'student': student,
        'exam_name': exam.name or f"Part {exam_part} Examination",
        'exam_month_year': exam.exam_month_year or "N/A",
        'exam_year': exam.exam_year or "N/A",
        'batch_year': exam.batch_code or "N/A",
        'session_year': exam.session_code or "N/A",
        'hons_subject': honours_subject_name,
        'center_name': "N/A",
        
        'subjects': {
            'honours': {
                'name': honours_subject_name,
                'papers': honours_papers,
                'total_max': hons_total_max,
                'total_pass': int(hons_total_max * 0.45),
                'total_obtained': hons_total_obt
            },
            'subsidiary_1': {
                'name': sub1['name'] if sub1 else '',
                'papers': [sub1] if sub1 else [],
                'total_max': sub1['max_marks'] if sub1 else 0,
                'total_pass': sub1['pass_marks'] if sub1 else 0,
                'total_obtained': sub1['obtained'] if sub1 else 0
            },
            'subsidiary_2': {
                'name': sub2['name'] if sub2 else '',
                'papers': [sub2] if sub2 else [],
                'total_max': sub2['max_marks'] if sub2 else 0,
                'total_pass': sub2['pass_marks'] if sub2 else 0,
                'total_obtained': sub2['obtained'] if sub2 else 0
            },
            'composition': {
                'name': 'Composition',
                'papers': composition_papers,
                'total_max': comp_total_max,
                'total_pass': int(comp_total_max * 0.33),
                'total_obtained': comp_total_obt
            },
            'general_studies': {
                'name': 'General & Environmental Studies',
                'papers': general_studies_papers,
                'total_max': gs_total_max,
                'total_pass': int(gs_total_max * 0.33),
                'total_obtained': gs_total_obt
            }
        },
        'grand_total': clean_mark(summary.total_secured_mark) if summary else "N/A",
        'result_status': summary.final_result if summary else "PENDING",
        'hons_total_words': num2words(hons_total_obt) + " Only",
        'publication_date': exam.publication_date.strftime("%d-%m-%Y") if exam.publication_date else "N/A",
        
        # Generate QR code
        'qr_code': generate_qr_code_base64(
            generate_ug_marksheet_qr_text(
                student, 
                exam, 
                clean_mark(summary.total_secured_mark) if summary else 0
            )
        ),
        
        # Images
        'university_logo': image_to_base64(os.path.join(settings.MEDIA_ROOT, "media/common/purnea-logo.png")),
        'watermark_logo': image_to_base64(os.path.join(settings.MEDIA_ROOT, "media/common/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.MEDIA_ROOT, "media/common/controller-of-examination-signature.png")),
    }

    return context

def generate_ug_old_ba_hons_marksheet_pdf(student, exam_part, exam_type=None):
    """
    Generate marksheet PDF for UG Before CBCS student using simplified models.
    """
    from weasyprint import HTML
    context = get_ug_old_ba_hons_marksheet_context(student, exam_part, exam_type)

    if not context:
        return None

    # Render template
    if student.discipline_code and 'HONS' in student.discipline_code.upper():
        template_name = f"ug_before_cbcs/ba_hons_marksheet_part{exam_part.lower()}.html"
    else:
        # Fallback for other courses if needed in the future
        template_name = f"ug_before_cbcs/ba_hons_marksheet_part{exam_part.lower()}.html"
        
    html_string = get_template(template_name).render(context)
    
    try:
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        return pdf_file
    except Exception as e:
        print("PDF ERROR:", str(e)) 
        logger.error(f"Error generating PDF: {e}")
        return None
