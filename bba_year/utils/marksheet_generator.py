from django.template.loader import get_template
from django.conf import settings
from bba_year.models import (
    BBAStudentProfile,
    BBAStudentCourseAssessment,
    BBAExam,
    BBACommonCourseStructure,
    BBACourseStructure,
    BBAExamCenterMapping
)
from pup_umis_backend.utils.file_utils import image_to_base64
from ug_before_cbcs.utils.qr_generator import generate_qr_code_base64, generate_ug_marksheet_qr_text
import os
import logging
from decimal import Decimal
from django.db.models import Q
from collections import defaultdict

logger = logging.getLogger(__name__)

def num2words(num):
    """Robust number to words converter."""
    if not isinstance(num, (int, float, Decimal)):
        return ""
    num = int(num)
    if num == 0: return "ZERO"
    
    units = ["", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE"]
    teens = ["TEN", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN", "NINETEEN"]
    tens = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]
    thousands = ["", "THOUSAND", "MILLION", "BILLION"]

    def convert_hundreds(n):
        res = []
        if n >= 100:
            res.append(units[n // 100] + " HUNDRED")
            n %= 100
        if n >= 20:
            res.append(tens[n // 10])
            n %= 10
            if n > 0: res.append(units[n])
        elif n >= 10:
            res.append(teens[n - 10])
        elif n > 0:
            res.append(units[n])
        return " ".join(res)

    words = []
    i = 0
    while num > 0:
        if num % 1000 != 0:
            words.append(convert_hundreds(num % 1000) + (" " + thousands[i] if thousands[i] else ""))
        num //= 1000
        i += 1
        
    res_str = " ".join(reversed(words)).strip()
    return res_str.title()

from bba_year.utils.tr.grading import determine_overall_result, get_hons_classification

def get_roman(num):
    """Convert integer to Roman numeral."""
    val = [
        10, 9, 5, 4, 1
    ]
    syb = [
        "X", "IX", "V", "IV", "I"
    ]
    roman_num = ''
    i = 0
    while  num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num

def get_bba_marksheet_context(student, exam_val="3"):
    """
    Prepares the context for BBA Part III Marksheet including Part I and II marks.
    """
    # 1. Fetch assessments for all years
    assessments = BBAStudentCourseAssessment.objects.filter(
        student=student,
        year__in=["1", "2", "3"]
    ).order_by('year', 'paper_code')

    # 2. Map assessments by (year, paper_code, label)
    marks_map = defaultdict(lambda: {"obtained": 0, "max": 0, "pass": 0, "absent": False, "found": False})
    
    for ass in assessments:
        label = str(ass.label or "").upper()
        # Mark mapping based on TR labels
        if any(x in label for x in ["ESE", "THEORY", "Theory"]):
            m_type = "THEORY"
        elif any(x in label for x in ["CIA", "INTERNAL", "INTERNAL ASSESSMENT", "IA"]):
            m_type = "INTERNAL"
        else:
            m_type = "THEORY" # Fallback
            
        key = (ass.year, ass.paper_code, m_type)
        
        obt = float(ass.ind_final_marks_obtained if ass.ind_final_marks_obtained is not None else (ass.ind_marks_obtained or 0))
        max_m = float(ass.ind_max_marks or 0)
        pass_m = float(ass.ind_pass_marks or 0)
        
        # Keep the best marks for each paper/type
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
    all_hons = BBACommonCourseStructure.objects.filter(paper_type="HONOURS").order_by('year', 'code')
    
    parts_data = []
    year_hons_total_marks = 0
    year_hons_total_max = 0
    
    year_labels = {"1": "1st", "2": "2nd", "3": "3rd"}
    
    paper_counter = 1
    for year in ["1", "2", "3"]:
        year_subjects = []
        year_total_obtained = 0
        year_total_max = 0
        
        hons_subs = all_hons.filter(year=year).order_by('code')
        for sub in hons_subs:
            theory = marks_map.get((year, sub.code, "THEORY"), {"obtained": 0, "max": 100, "pass": 45, "absent": False, "found": False})
            internal = marks_map.get((year, sub.code, "INTERNAL"), {"obtained": 0, "max": 0, "pass": 0, "absent": False, "found": False})
            
            # If marks not found, get defaults from structure
            if not theory["found"]:
                struct = BBACourseStructure.objects.filter(year=year, course_code=sub.code).filter(label__in=["ESE", "THEORY"]).first()
                if struct:
                    theory["max"] = float(struct.max_marks or 100)
                    theory["pass"] = float(struct.min_marks or 45)
            
            if not internal["found"]:
                struct = BBACourseStructure.objects.filter(year=year, course_code=sub.code).filter(label__in=["CIA", "INTERNAL", "IA"]).first()
                if struct:
                    internal["max"] = float(struct.max_marks or 0)
                    internal["pass"] = float(struct.min_marks or 0)

            total_sub_obtained = theory["obtained"] + internal["obtained"]
            year_total_obtained += total_sub_obtained
            year_total_max += theory["max"] + internal["max"]
            
            year_subjects.append({
                'name': sub.course_name.upper(),
                'paper_no': get_roman(paper_counter),
                'theory': theory,
                'internal': internal,
                'total_max': float(theory["max"] + internal["max"]),
                'total_obtained': total_sub_obtained
            })
            paper_counter += 1
            
        if year_subjects:
            # Calculate aggregate pass marks for the part (45% for Honours)
            theory_max_sum = sum(s['theory']['max'] for s in year_subjects)
            internal_max_sum = sum(s['internal']['max'] for s in year_subjects)
            
            parts_data.append({
                'name': year_labels[year],
                'subjects': year_subjects,
                'total_obtained': year_total_obtained,
                'total_max': year_total_max,
                'total_pass': int(theory_max_sum * 0.45),
                'internal_pass': int(internal_max_sum * 0.45)
            })

    # 4. Handle Subsidiary Subjects
    subsidiary_data = []
    all_subs = BBACommonCourseStructure.objects.filter(paper_type="SUBSIDIARY").order_by('year', 'code')
    
    subs_sl_no = 4 # Starting Sl. No as per image (after 3 parts of Honours)
    for year in ["1", "2"]:
        year_subs = []
        year_total_obtained = 0
        year_total_max = 0
        
        subs_subs = all_subs.filter(year=year).order_by('code')
        for sub in subs_subs:
            theory = marks_map.get((year, sub.code, "THEORY"), {"obtained": 0, "max": 100, "pass": 33, "absent": False, "found": False})
            if not theory["found"]:
                 struct = BBACourseStructure.objects.filter(year=year, course_code=sub.code).filter(label__in=["ESE", "THEORY"]).first()
                 if struct:
                     theory["max"] = float(struct.max_marks or 100)
                     theory["pass"] = float(struct.min_marks or 33)
            
            year_subs.append({
                'name': sub.course_name.upper(),
                'theory': theory,
                'total_obtained': theory["obtained"],
                'total_max': theory["max"]
            })
            year_total_obtained += theory["obtained"]
            year_total_max += theory["max"]
            
        if year_subs:
            subsidiary_data.append({
                'sl_no': subs_sl_no,
                'name': year_labels[year],
                'subjects': year_subs,
                'total_obtained': year_total_obtained,
                'total_max': year_total_max
            })
            subs_sl_no += 1

    # 5. General Studies / Environmental Studies (Part 3)
    gs_subjects = BBACommonCourseStructure.objects.filter(year="3").filter(
        Q(course_name__icontains="ENVIRONMENTAL") | Q(course_name__icontains="VOCATIONAL") | Q(paper_type="GENERAL_STUDIES")
    ).distinct()
    
    gs_data = []
    gs_total_obtained = 0
    gs_total_max = 0
    for sub in gs_subjects:
        theory = marks_map.get(("3", sub.code, "THEORY"), {"obtained": 0, "max": 100, "pass": 33, "absent": False, "found": False})
        if not theory["found"]:
             struct = BBACourseStructure.objects.filter(year="3", course_code=sub.code).filter(label__in=["ESE", "THEORY"]).first()
             if struct:
                 theory["max"] = float(struct.max_marks or 100)
                 theory["pass"] = float(struct.min_marks or 33)
                 
        gs_data.append({
            'name': sub.course_name.upper(),
            'theory': theory,
            'total_obtained': theory["obtained"],
            'total_max': theory["max"]
        })
        gs_total_obtained += theory["obtained"]
        gs_total_max += theory["max"]

    # 6. Overall Totals and Grading
    hons_total_obtained = sum(p['total_obtained'] for p in parts_data)
    hons_total_max = sum(p['total_max'] for p in parts_data)
    
    subs_total_obtained = sum(p['total_obtained'] for p in subsidiary_data)
    subs_total_max = sum(p['total_max'] for p in subsidiary_data)
    
    grand_total_obtained = hons_total_obtained + subs_total_obtained + gs_total_obtained
    grand_total_max = hons_total_max + subs_total_max + gs_total_max
    
    result_status = get_hons_classification(hons_total_obtained, hons_total_max)
    
    # 7. Metadata
    exam = BBAExam.objects.filter(year=exam_val).last()
    center_name = "N/A"
    if exam:
        mapping = BBAExamCenterMapping.objects.filter(exam=exam, attached_colleges=student.college).first()
        if mapping: center_name = mapping.center.name

    context = {
        'student': student,
        'exam_name': exam.name if exam else f"Bachelor of Business Administration vocal (Honours) Part-III Examination",
        'exam_month_year': exam.exam_month_year if exam else "N/A",
        'publication_date': exam.publication_date.strftime("%d-%m-%Y") if exam and exam.publication_date else "N/A",
        'batch_year': student.batch.name if student.batch else "N/A",
        'session_year': student.session_str or "N/A",
        'center_name': center_name,
        'parts': parts_data,
        'subsidiary_parts': subsidiary_data,
        'general_studies': gs_data,
        'grand_total': grand_total_obtained,
        'grand_total_max': grand_total_max,
        'hons_total_marks': hons_total_obtained,
        'hons_total_max': hons_total_max,
        'hons_total_words': num2words(hons_total_obtained),
        'total_words': num2words(grand_total_obtained) + " ONLY",
        'result_status': result_status,
        
        # QR \u0026 Logos
        'qr_code': generate_qr_code_base64(f"BBA-MARKSHEET|Roll:{student.roll_no}|Reg:{student.registration_no}|Total:{hons_total_obtained}"),
        'university_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/controller-of-examination-signature.png")),
    }
    return context


def generate_bba_marksheet_pdf(student, exam_val="3"):
    """
    Renders the Marksheet PDF for BBA.
    """
    from weasyprint import HTML
    context = get_bba_marksheet_context(student, exam_val)
    
    template_name = "bba_year/marksheet_part3.html"
    html_string = get_template(template_name).render(context)
    
    try:
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        return pdf_file
    except Exception as e:
        logger.error(f"Error generating BBA Marksheet PDF: {e}")
        return None
