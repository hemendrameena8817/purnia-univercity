from django.template.loader import get_template
from django.conf import settings
from bca_hons_year.models import (
    BCAHonsStudentProfile,
    BCAHonsStudentCourseAssessment,
    BCAHonsExam,
    BCAHonsCommonCourseStructure,
    BCAHonsCourseStructure,
    BCAHonsExamCenterMapping
)
from pup_umis_backend.utils.file_utils import image_to_base64
from ug_before_cbcs.utils.qr_generator import generate_qr_code_base64
import os
import logging
from decimal import Decimal
from collections import defaultdict
from django.db.models import Q

logger = logging.getLogger(__name__)

def num2words(num):
    """Simple number to words converter."""
    if not isinstance(num, (int, float, Decimal)): return ""
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
        if num > 0: words.append(units[num])
    elif num >= 10:
        words.append(teens[num - 10])
    elif num > 0:
        words.append(units[num])
    return " ".join(words)

def get_bca_hons_marksheet_context(student, exam_val="3"):
    """
    Prepares the context for BCA Hons Part III Marksheet including Part I and II marks.
    """
    from bca_hons_year.utils.tr.grading import get_hons_classification
    
    # 1. Fetch assessments for all years
    assessments = BCAHonsStudentCourseAssessment.objects.filter(
        student=student,
        year__in=["1", "2", "3"]
    ).order_by('year', 'paper_code')

    # 2. Map assessments by (year, paper_code, label)
    marks_map = defaultdict(lambda: {"obtained": 0, "max": 0, "pass": 0, "absent": False, "found": False})
    
    for ass in assessments:
        label = str(ass.label or "").upper()
        if any(x in label for x in ["ESE", "THEORY", "Theory"]):
            m_type = "THEORY"
        elif any(x in label for x in ["CIA", "INTERNAL", "IA", "PRACTICAL"]):
            m_type = "INTERNAL"
        else:
            m_type = "THEORY"
            
        key = (ass.year, ass.paper_code, m_type)
        
        obt = float(ass.ind_final_marks_obtained if ass.ind_final_marks_obtained is not None else (ass.ind_marks_obtained or 0))
        max_m = float(ass.ind_max_marks or 0)
        pass_m = float(ass.ind_pass_marks or 0)
        
        if not marks_map[key]["found"] or obt > marks_map[key]["obtained"]:
            marks_map[key] = {
                "obtained": obt,
                "max": max_m,
                "pass": pass_m,
                "absent": bool(ass.ind_is_absent),
                "found": True
            }

    # 3. Fetch Course Structure for Subjects
    # Honours subjects for all parts
    all_hons = BCAHonsCommonCourseStructure.objects.filter(paper_type="HONOURS").order_by('year', 'code')
    
    parts_data = []
    sl_no_counter = 1
    year_labels = {"1": "Part - I", "2": "Part - II", "3": "Part - III"}
    
    for year in ["1", "2", "3"]:
        year_subjects = []
        year_total_obtained = 0
        year_total_max = 0
        
        hons_subs = all_hons.filter(year=year)
        for sub in hons_subs:
            theory = marks_map.get((year, sub.code, "THEORY"), {"obtained": 0, "max": 75, "pass": 34, "absent": False, "found": False})
            internal = marks_map.get((year, sub.code, "INTERNAL"), {"obtained": 0, "max": 25, "pass": 11, "absent": False, "found": False})
            
            # If marks not found, get defaults from structure
            if not theory["found"]:
                struct = BCAHonsCourseStructure.objects.filter(year=year, course_code=sub.code).filter(label__in=["ESE", "THEORY"]).first()
                if struct:
                    theory["max"] = float(struct.max_marks or 75)
                    theory["pass"] = float(struct.min_marks or 34)
            
            if not internal["found"]:
                struct = BCAHonsCourseStructure.objects.filter(year=year, course_code=sub.code).filter(label__in=["CIA", "INTERNAL", "IA", "PRACTICAL"]).first()
                if struct:
                    internal["max"] = float(struct.max_marks or 25)
                    internal["pass"] = float(struct.min_marks or 11)

            total_sub_obtained = theory["obtained"] + internal["obtained"]
            year_total_obtained += total_sub_obtained
            year_total_max += theory["max"] + internal["max"]
            
            year_subjects.append({
                'sl_no': sl_no_counter,
                'name': sub.course_name.upper(),
                'paper_no': sub.code,
                'theory': theory,
                'internal': internal,
                'total_obtained': total_sub_obtained
            })
            sl_no_counter += 1
            
        if year_subjects:
            parts_data.append({
                'name': year_labels[year],
                'subjects': year_subjects,
                'total_obtained': year_total_obtained,
                'total_max': year_total_max
            })

    # 4. Handle Composition / General Studies
    gs_subjects = BCAHonsCommonCourseStructure.objects.filter(year="3").filter(
        Q(course_name__icontains="ENVIRONMENTAL") | Q(course_name__icontains="VOCATIONAL") | Q(paper_type="COMPOSITION")
    ).distinct()
    
    gs_data = []
    gs_total_obtained = 0
    gs_total_max = 0
    for sub in gs_subjects:
        theory = marks_map.get(("3", sub.code, "THEORY"), {"obtained": 0, "max": 100, "pass": 33, "absent": False, "found": False})
        if not theory["found"]:
             struct = BCAHonsCourseStructure.objects.filter(year="3", course_code=sub.code).filter(label__in=["ESE", "THEORY"]).first()
             if struct:
                 theory["max"] = float(struct.max_marks or 100)
                 theory["pass"] = float(struct.min_marks or 33)
                 
        gs_data.append({
            'sl_no': sl_no_counter,
            'name': sub.course_name.upper(),
            'theory': theory,
            'total_obtained': theory["obtained"]
        })
        gs_total_obtained += theory["obtained"]
        gs_total_max += theory["max"]
        sl_no_counter += 1

    # 5. Overall Totals and Grading
    hons_total_marks = sum(p['total_obtained'] for p in parts_data)
    hons_total_max = sum(p['total_max'] for p in parts_data)
    grand_total_obtained = hons_total_marks + gs_total_obtained
    grand_total_max = hons_total_max + gs_total_max
    
    result_status = get_hons_classification(hons_total_marks, hons_total_max)
    
    # 6. Metadata
    exam = BCAHonsExam.objects.filter(year=exam_val).last()
    center_name = "N/A"
    if exam:
        mapping = BCAHonsExamCenterMapping.objects.filter(exam=exam, attached_colleges=student.college).first()
        if mapping: center_name = mapping.center.name

    context = {
        'student': student,
        'exam_name': exam.name if exam else f"Bachelor of Computer Application (Honours) Part-III Examination",
        'exam_month_year': exam.exam_month_year if exam else "N/A",
        'publication_date': exam.publication_date.strftime("%d-%m-%Y") if exam and exam.publication_date else "N/A",
        'batch_year': student.batch.name if student.batch else "N/A",
        'session_year': student.session_str or "N/A",
        'center_name': center_name,
        'parts': parts_data,
        'general_studies': gs_data,
        'grand_total': grand_total_obtained,
        'grand_total_max': grand_total_max,
        'hons_total_marks': hons_total_marks,
        'hons_total_max': hons_total_max,
        'hons_total_words': num2words(hons_total_marks),
        'total_words': num2words(grand_total_obtained) + " Only",
        'result_status': result_status,
        
        # QR & Logos
        'qr_code': generate_qr_code_base64(f"BCA-MARKSHEET|Roll:{student.roll_no}|Reg:{student.registration_no}|Total:{hons_total_marks}"),
        'university_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/controller-of-examination-signature.png")),
    }
    return context

def generate_bca_hons_marksheet_pdf(student, exam_val="3"):
    """
    Renders the Marksheet PDF for BCA Hons.
    """
    from weasyprint import HTML
    context = get_bca_hons_marksheet_context(student, exam_val)
    template_name = "bca_hons_year/marksheet_part3.html"
    html_string = get_template(template_name).render(context)
    try:
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        return pdf_file
    except Exception as e:
        logger.error(f"Error generating BCA Hons Marksheet PDF: {e}")
        return None
