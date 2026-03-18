import os
import logging
from collections import defaultdict
from django.conf import settings
from django.template.loader import get_template
from weasyprint import HTML
from pup_umis_backend.utils.file_utils import image_to_base64
from bca_hons_year.models import (
    BCAHonsStudentProfile, 
    BCAHonsCourse, 
    BCAHonsCommonCourseStructure, 
    BCAHonsCourseStructure,
    BCAHonsStudentCourseAssessment
)
from bca_hons_year.utils.tr.grading import determine_overall_result, get_hons_classification

logger = logging.getLogger(__name__)

def _get_marks(student_id, code, student_map, mark_type='ESE'):
    """Return the BEST ESE or CIA marks for a student + paper code among all attempts."""
    best_res = {"marks": 0.0, "found": False, "absent": False}
    search_labels = []
    if mark_type == 'ESE':
        search_labels = ['ESE', 'THEORY', 'Theory']
    else:
        search_labels = ['CIA', 'IA', 'INTERNAL', 'Internal Assessment']

    all_absent = True
    for rec in student_map.get(student_id, []):
        if rec.paper_code == code:
            label = str(rec.label or "").upper()
            if any(s.upper() in label for s in search_labels):
                is_absent = bool(rec.ind_is_absent)
                if not is_absent: all_absent = False
                marks = float(rec.ind_final_marks_obtained or rec.ind_marks_obtained or 0) if not is_absent else 0
                if not best_res["found"] or marks >= best_res["marks"]:
                    best_res["marks"] = marks
                    best_res["found"] = True
                    best_res["absent"] = is_absent
    if not all_absent: best_res["absent"] = False
    return best_res

def generate_bca_hons_result_declaration_pdf(exam, college, batch_uid=None):
    """
    Generates a result declaration PDF for BCA Hons showing pass/fail roll numbers.
    Follows TR logic strictly.
    """
    year = exam.year or 3
    
    # 1. Fetch Students
    student_filters = {"college": college}
    if batch_uid: student_filters["batch__uid"] = batch_uid
    students = BCAHonsStudentProfile.objects.filter(**student_filters).distinct().order_by("roll_no")

    if not students: return None

    # 2. Setup Data Structures
    target_years = [str(y) for y in range(1, int(year) + 1)]
    assessments = BCAHonsStudentCourseAssessment.objects.filter(
        student__in=students,
        year__in=target_years
    ).order_by("-id")

    # Audit log for students without assessments
    no_assessment_students = students.exclude(bca_hons_student_course_assessment__year=str(year))
    print(f"DEBUG (BCA): Students WITHOUT assessments for year {year}: {no_assessment_students.count()}")
    for s in no_assessment_students:
        print(f"  {s.registration_no} - {s.roll_no} : {s.get_full_name()}")

    student_map = defaultdict(list)
    for rec in assessments:
        student_map[rec.student_id].append(rec)

    # 3. Filter students which have entries for the target year
    students = [s for s in students if any(rec.year == str(year) for rec in student_map.get(s.id, []))]
    if not students: return None

    pass_roll_nos = []
    fail_roll_nos = []

    # Fetch structures (using standard BCA Hons papers)
    y1_hons = list(BCAHonsCommonCourseStructure.objects.filter(year="1", paper_type="HONOURS").values_list("code", flat=True))
    y2_hons = list(BCAHonsCommonCourseStructure.objects.filter(year="2", paper_type="HONOURS").values_list("code", flat=True))
    y3_hons = list(BCAHonsCommonCourseStructure.objects.filter(year="3", paper_type="HONOURS").values_list("code", flat=True))
    
    y1_subs = sorted(list(BCAHonsCommonCourseStructure.objects.filter(year="1", paper_type="SUBSIDIARY").values_list("code", flat=True)))
    y2_subs = sorted(list(BCAHonsCommonCourseStructure.objects.filter(year="2", paper_type="SUBSIDIARY").values_list("code", flat=True)))

    # Pre-fetch structures for fast lookups (Same logic as TR)
    all_structs = list(BCAHonsCourseStructure.objects.all())
    def get_struct_max(year_str, c_code, m_type):
        label_search = ['ESE', 'THEORY', 'Theory'] if m_type == 'ESE' else ['CIA', 'IA', 'INTERNAL', 'INTERNAL ASSESSMENT']
        for s in all_structs:
            if s.year == str(year_str) and s.course_code == c_code:
                if any(ls.upper() in (s.label or "").upper() for ls in label_search):
                    return float(s.max_marks or 0)
        return 75.0 if m_type == 'ESE' else 25.0 # Fallback

    # Calculate Results
    for student in students:
        hons_marks_data = []
        sub_marks_data = [] # Subsidiaries AND Composition subjects
        
        # Honours
        h_plans = []
        if int(year) >= 1: h_plans.append(("1", y1_hons))
        if int(year) >= 2: h_plans.append(("2", y2_hons))
        if int(year) >= 3: h_plans.append(("3", y3_hons))
        
        for yr_str, codes in h_plans:
            for code in codes:
                m_ese = _get_marks(student.id, code, student_map, mark_type='ESE')
                m_cia = _get_marks(student.id, code, student_map, mark_type='CIA')
                
                ese_max = get_struct_max(yr_str, code, 'ESE')
                cia_max = get_struct_max(yr_str, code, 'CIA')
                
                hons_marks_data.append((
                    m_ese["marks"] if not m_ese["absent"] else 0, ese_max,
                    m_cia["marks"] if not m_cia["absent"] else 0, cia_max
                ))

        # Subsidiaries
        s_plans = []
        if int(year) >= 1: s_plans.append(("1", y1_subs))
        if int(year) >= 2: s_plans.append(("2", y2_subs))
        
        for yr_str, codes in s_plans:
            for code in codes:
                m_ese = _get_marks(student.id, code, student_map, mark_type='ESE')
                m_cia = _get_marks(student.id, code, student_map, mark_type='CIA')
                
                ese_max = get_struct_max(yr_str, code, 'ESE')
                cia_max = get_struct_max(yr_str, code, 'CIA')
                
                sub_marks_data.append((
                    m_ese["marks"] if not m_ese["absent"] else 0, ese_max,
                    m_cia["marks"] if not m_cia["absent"] else 0, cia_max
                ))
                
        # Composition subjects (RBH/GES) counted as subsidiaries (33% passing)
        comp_plans = []
        if int(year) >= 1: 
            y1_comp = list(BCAHonsCommonCourseStructure.objects.filter(year="1", paper_type="COMPOSITION").values_list("code", flat=True))
            comp_plans.append(("1", y1_comp))
        if int(year) >= 2: 
            y2_comp = list(BCAHonsCommonCourseStructure.objects.filter(year="2", paper_type="COMPOSITION").values_list("code", flat=True))
            comp_plans.append(("2", y2_comp))
        if int(year) >= 3:
            y3_comp = list(BCAHonsCommonCourseStructure.objects.filter(year="3", paper_type="COMPOSITION").values_list("code", flat=True))
            comp_plans.append(("3", y3_comp))
            
        for yr_str, codes in comp_plans:
            for code in codes:
                m_comp = _get_marks(student.id, code, student_map, mark_type='ESE')
                comp_max = get_struct_max(yr_str, code, 'ESE')
                sub_marks_data.append((
                    m_comp["marks"] if not m_comp["absent"] else 0, comp_max,
                    0, 0
                ))

        overall_res = determine_overall_result(hons_marks_data, sub_marks_data)
        
        display_roll = student.roll_no or "N/A"
        if overall_res in ["Pass with Hons.", "PASS"]:
            pass_roll_nos.append(display_roll)
        else:
            fail_roll_nos.append(display_roll)

    # Chunking for 15 per page
    unified_students = []
    if not pass_roll_nos:
        unified_students.append({"roll": "\u00A0", "status": "PASS", "is_placeholder": True})
    else:
        for roll in pass_roll_nos:
            unified_students.append({"roll": roll, "status": "PASS", "is_placeholder": False})
            
    if not fail_roll_nos:
        unified_students.append({"roll": "\u00A0", "status": "FAIL", "is_placeholder": True})
    else:
        for roll in fail_roll_nos:
            unified_students.append({"roll": roll, "status": "FAIL", "is_placeholder": False})

    STUDENTS_PER_PAGE = 15
    pages = []
    for i in range(0, len(unified_students), STUDENTS_PER_PAGE):
        chunk = unified_students[i:i + STUDENTS_PER_PAGE]
        p_count = sum(1 for s in chunk if s["status"] == "PASS" and not s.get("is_placeholder", False))
        f_count = sum(1 for s in chunk if s["status"] == "FAIL" and not s.get("is_placeholder", False))
        pages.append({
            "students": chunk,
            "pass_count": p_count,
            "fail_count": f_count
        })

    logo_path = os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")
    context = {
        "university_logo": image_to_base64(logo_path) if os.path.exists(logo_path) else None,
        "exam_name": exam.name,
        "college_name": college.name,
        "college_code": college.college_code,
        "course_name": students[0].course.name if (students and students[0].course) else "BCA Hons",
        "year": year,
        "pages": pages,
        "pass_count": len(pass_roll_nos),
        "fail_count": len(fail_roll_nos),
        "total_count": len(pass_roll_nos) + len(fail_roll_nos),
    }

    html_string = get_template("bca_hons_year/result_declaration.html").render(context)
    try:
        return HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
    except Exception as e:
        logger.error(f"BCA Hons Result Declaration PDF failed: {e}")
        return None
