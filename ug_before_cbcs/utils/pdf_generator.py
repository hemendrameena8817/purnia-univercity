from django.template.loader import get_template
from django.conf import settings
from ug_before_cbcs.models import (
    UGBeforeCBCSStudentProfile,

    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult,

)
from pup_umis_backend.utils.file_utils import image_to_base64
from ug_before_cbcs.utils.qr_generator import generate_qr_code_base64, generate_ug_marksheet_qr_text
from ug_before_cbcs.utils.validation import validate_marksheet_context
from .res_calculation import calculate_ba_hons_part1_result
import os
import logging
from decimal import Decimal
from weasyprint import HTML

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

def get_ug_old_ba_hons_part1_context(student, exam_part='1', exam_type=None, course_code=None, batch_code=None, custom_results=None):
    """
    Prepares and returns the context dictionary for the UG Before CBCS BA Hons Part 1 marksheet.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam_part: Part number as string ('1', '2', or '3')
        exam_type: Optional exam type filter (REGULAR, BACK)
        course_code: Optional course code filter
        batch_code: Optional batch code filter
        custom_results: Optional list of pre-filtered results to use instead of querying
    
    Returns:
        Context dictionary or None
    """
    # Convert part to uppercase format (PART1, PART2, PART3)
    part_code = f"PART{exam_part}"

    # Use custom results if provided, otherwise query
    if custom_results:
        results = custom_results
        if not results:
            logger.warning(f"No custom results provided for {student.registration_no} / {part_code}")
            return None
        first_result = results[0]
        exam = first_result.exam
    else:
        # 1. Get student results for this part, filtering by exam_type if provided
        results_query = UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam__part=part_code
        )
        
        if exam_type:
            results_query = results_query.filter(exam_type__iexact=exam_type)
            
        if course_code:
            results_query = results_query.filter(exam__course_code__iexact=course_code)
            
        if batch_code:
            results_query = results_query.filter(exam__batch_code=batch_code)
            
        first_result = results_query.select_related('exam').order_by('-exam__exam_year').first()

        if not first_result:
            logger.warning(f"No results found for {student.registration_no} / {part_code}")
            return None

        exam = first_result.exam

        # 2. Get all student results for this exam
        results = UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam=exam
        ).order_by('paper_code')

    # 3. Get exam summary
    # Exam summary fields are now part of StudentResult; aggregate as needed.
    summary = first_result

    # 4. Group Papers by subject
    subjects_map = {} # { subject_name: { papers: [], type: '' } }


    # Helper to clean marks
    def clean_mark(val):
        if val is None: return 0
        if isinstance(val, (int, float, Decimal)): return int(val)
        try:
            return int(val)
        except (ValueError, TypeError):
            return val  # Return as string (ABS, UFM, etc.)

    # Get discipline from student's discipline_code
    student_discipline = course_code or student.discipline_code.upper() if student.discipline_code else ""

    for result in results:
        sub_name = result.subject_name.upper() if result.subject_name else "UNKNOWN"
        
        # Calculate total marks obtained (theory + practical + sessional)
        theory_marks = clean_mark(result.theory)
        practical_marks = clean_mark(result.practical)
        sessional_marks = clean_mark(result.sessional)
        
        # Sum only numeric marks
        total_obtained_calc = 0
        for mark in [theory_marks, practical_marks, sessional_marks]:
            if isinstance(mark, (int, float)):
                total_obtained_calc += mark
        
        # Paper Data Structure
        paper_max = clean_mark(result.maximum_mark) or 100
        paper_pass = clean_mark(result.pass_mark) or 33
        paper_obt = clean_mark(result.mark_secured) or total_obtained_calc

        paper_data = {
            'uid': result.uid,
            'name': result.subject_name or result.paper_code,
            'paper_code': result.paper_code,
            'status': result.status.upper() if result.status else '',
            'max_marks': paper_max,
            'pass_marks': paper_pass,
            'obtained': paper_obt
        }
        
        # Categorize the subject using specific Part-based codes
        p_code = result.paper_code.upper() if result.paper_code else ""
        p_type = result.paper_type_code.upper() if result.paper_type_code else ""
        
        # Suffixes based on part (e.g. Part 1 -> 101, Part 2 -> 201)
        # We also check for the full code including Course (e.g. BSC101)
        hons_suffix = f"{exam_part}01"
        sub1_suffix = f"{exam_part}02"
        sub2_suffix = f"{exam_part}03"
        comp_suffixes = [f"{exam_part}04", f"{exam_part}05"]

        sub_type = 'subsidiary'
        if p_code.endswith(hons_suffix) or p_type in ['HONS', 'HON']:
            sub_type = 'honours'
        elif p_type in ['RB', 'NRB'] or any(p_code.endswith(s) for s in comp_suffixes):
            sub_type = 'composition'
        elif p_code.endswith(sub1_suffix):
            sub_type = 'subsidiary_1'
        elif p_code.endswith(sub2_suffix):
            sub_type = 'subsidiary_2'
        
        # General fallback
        if sub_type == 'subsidiary' and student_discipline:
            if student_discipline in sub_name or sub_name.startswith(student_discipline):
                sub_type = 'honours'

        # Use a unique key to prevent collisions (e.g., Honours English vs Composition English)
        if sub_type == 'composition':
            bucket_key = "COMPOSITION_GROUP"
        else:
            bucket_key = f"{sub_type}_{sub_name}"

        if bucket_key not in subjects_map:
            subjects_map[bucket_key] = {
                'name': result.subject_name if sub_type != 'composition' else 'Composition',
                'type': sub_type,
                'papers': [],
                'total_max': 0,
                'total_pass': 0,
                'total_obtained': 0
            }
        
        subjects_map[bucket_key]['papers'].append(paper_data)
        subjects_map[bucket_key]['total_max'] += paper_max
        # Pass marks logic is tricky: usually 45% for hons total, 33% for subs
        # For now, we take the pass mark from the result if provided
        subjects_map[bucket_key]['total_pass'] = max(subjects_map[bucket_key].get('total_pass', 0), paper_pass)
        
        if isinstance(paper_obt, (int, float)):
            subjects_map[bucket_key]['total_obtained'] += paper_obt

    # Separate subjects into groups
    honours_papers = []
    subsidiary_subjects = []
    composition_papers = []
    general_studies_papers = []

    for sub in subjects_map.values():
        if sub['type'] == 'honours':
            honours_papers.extend(sub['papers'])
        elif sub['type'] == 'composition':
            composition_papers.extend(sub['papers'])
        elif sub['type'] == 'subsidiary_1':
            subsidiary_subjects.append(sub) # We'll handle them by type specifically
        elif sub['type'] == 'subsidiary_2':
            subsidiary_subjects.append(sub)
        else:
            # Fallback for old grouping logic
            subsidiary_subjects.append(sub)

    # Sort Composition papers and assign display names
    # e.g. BA104 (RB or NRB) and BA105 (MB if NRB)
    final_composition_papers = []
    comp_papers_raw = sorted(composition_papers, key=lambda x: x['paper_code'])
    for p in comp_papers_raw:
        res_obj = next((r for r in results if r.uid == p['uid']), None)
        p_type = res_obj.paper_type_code.upper() if res_obj and res_obj.paper_type_code else ""
        p_code = p['paper_code'].upper() if p['paper_code'] else ""
        
        if p_type == 'RB' or 'RBH' in p_code or 'R.B' in p_code:
            p['display_name'] = "Rastrabhasha hindi"
        elif p_type == 'NRB' or 'Non-Hindi' in p['name']:
            if any(s in p_code for s in ['104', '204']):
                p['display_name'] = "Non-Hindi"
            else:
                p['display_name'] = f"MB: {p['name'].title()}"
        else:
            p['display_name'] = p['name']
        final_composition_papers.append(p)
    composition_papers = final_composition_papers

    # Organize and rename Honours papers
    is_honours_with_practical = False
    organized_honours = []
    paper1 = None
    paper2 = None
    practical = None

    # First, check if there's a practical components for Honours
    has_hons_practical = any(p['status'] == 'LAB' for p in honours_papers)
    is_honours_with_practical = has_hons_practical

    # Determine paper codes based on Course and Part (e.g. BSC101, BA201)
    specific_hons_code = f"{course_code.upper()}{exam_part}01" if course_code else None
    generic_hons_suffix = f"{exam_part}01"

    # Determine paper names based on part
    p1_name = 'Paper-I' if str(exam_part) == '1' else 'Paper-III'
    p2_name = 'Paper-II' if str(exam_part) == '1' else 'Paper-IV'

    for p in honours_papers:
        # Check for specific Course code or fallback to numeric suffix
        is_hons_paper = (specific_hons_code and specific_hons_code in p['paper_code']) or \
                        (not specific_hons_code and generic_hons_suffix in p['paper_code']) or \
                        p['paper_code'].endswith(generic_hons_suffix)

        if is_hons_paper:
            if p['status'] == 'END_TERM':
                paper1 = p
                paper1['name'] = p1_name
                if has_hons_practical:
                    paper1['max_marks'] = 75
                    paper1['pass_marks'] = 33 
            elif p['status'] == 'END2_TERM':
                paper2 = p
                paper2['name'] = p2_name
                if has_hons_practical:
                    paper2['max_marks'] = 75
            elif p['status'] == 'LAB':
                practical = p
                practical['name'] = 'Practical'
                if has_hons_practical:
                    practical['max_marks'] = 50
                    practical['pass_marks'] = 23
        else:
            organized_honours.append(p)

    # Add in specific order
    if paper1: organized_honours.append(paper1)
    if paper2: organized_honours.append(paper2)
    if practical: organized_honours.append(practical)
    
    honours_papers = organized_honours

    # Explicitly assign Subsidiaries by type or fallback order
    sub1 = next((s for s in subjects_map.values() if s['type'] == 'subsidiary_1'), None)
    sub2 = next((s for s in subjects_map.values() if s['type'] == 'subsidiary_2'), None)
    
    if not sub1 and subsidiary_subjects: sub1 = subsidiary_subjects[0]
    if not sub2 and len(subsidiary_subjects) > 1: sub2 = subsidiary_subjects[1]

    # Handle Practical Marks for Subsidiaries
    def apply_subsidiary_practical_rules(sub):
        if not sub or 'papers' not in sub: return
        
        has_prac = any('LAB' in p['status'] or 'PRAC' in p['status'] for p in sub['papers'])
        if has_prac:
            for p in sub['papers']:
                if 'END' in p['status']: # Theory
                    p['name'] = 'Theory'
                    p['max_marks'] = 75
                    p['pass_marks'] = 23
                else: # Practical
                    p['name'] = 'Practical'
                    p['max_marks'] = 25
                    p['pass_marks'] = 10
            
            # Recalculate totals for the subject
            sub['total_max'] = sum(p['max_marks'] for p in sub['papers'])
            sub['total_pass'] = sum(p['pass_marks'] for p in sub['papers'])
            # total_obtained is already summed during initial grouping

    apply_subsidiary_practical_rules(sub1)
    apply_subsidiary_practical_rules(sub2)

    # Sort subsidiary papers: Theory (END_TERM) first, then Practical (LAB/PRAC)
    def sort_subsidiary_papers(sub):
        if sub and 'papers' in sub:
            # Sort by status: END_TERM should come before LAB/PRAC
            sub['papers'].sort(key=lambda p: 0 if 'END' in p['status'] else 1)

    sort_subsidiary_papers(sub1)
    sort_subsidiary_papers(sub2)

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
    # Composition total is always 100 (either RB 100 or NRB 50 + MB 50)
    comp_total_max = 100
    
    gs_total_obt = sum_marks(general_studies_papers)
    gs_total_max = sum_max(general_studies_papers)

    # Get full honours subject name from the map
    honours_subject_name = None
    for sub in subjects_map.values():
        if sub['type'] == 'honours':
            honours_subject_name = sub['name']
            break
            
    if not honours_subject_name:
        if student.discipline_code:
            honours_subject_name = student.discipline_code
        else:
            honours_subject_name = "Honours"

    # Calculate Grand Total Marks
    calculated_grand_total = hons_total_obt + comp_total_obt + gs_total_obt
    if sub1: calculated_grand_total += sub1.get('total_obtained', 0)
    if sub2: calculated_grand_total += sub2.get('total_obtained', 0)

    # Calculate Grand Total Possible (Full Marks)
    grand_total_max = hons_total_max + comp_total_max + gs_total_max
    if sub1: grand_total_max += sub1.get('total_max', 0)
    if sub2: grand_total_max += sub2.get('total_max', 0)

    # Use stored total if valid and non-zero, otherwise use calculated
    stored_total = clean_mark(summary.total_secured_mark) if summary else 0
    final_grand_total = stored_total if stored_total and stored_total != 0 else calculated_grand_total

    # 5. Fetch Center Name from Mapping (if exists, else fallback to exam default)
    from ..models import UGBeforeCBCSExamCenterMapping
    mapping = UGBeforeCBCSExamCenterMapping.objects.filter(
        exam=exam, 
        student_college=student.college
    ).first()
    
    center_display_name = "N/A"
    if mapping:
        if mapping.center_college:
            center_display_name = mapping.center_college.name
        elif mapping.center_name:
            center_display_name = mapping.center_name
    else:
        center_display_name = exam.centre_name or "N/A"

    # Prepare Context
    context = {
        'exam_part': str(exam_part),
        'is_honours_with_practical': is_honours_with_practical,
        'student': student,
        'exam_name': exam.name or f"Part {exam_part} Examination",
        'exam_month_year': exam.exam_month_year or "N/A",
        'exam_year': exam.exam_year or "N/A",
        'batch_year': exam.batch_code or "N/A",
        'session_year': exam.session_code or "N/A",
        'hons_subject': honours_subject_name,
        'center_name': center_display_name,
        
        'subjects': {
            'honours': {
                'name': honours_subject_name,
                'papers': honours_papers,
                'total_max': hons_total_max,
                'total_pass': 90,
                'total_obtained': hons_total_obt,
                'theory_total': sum_marks([p for p in honours_papers if 'Practical' not in p['name']])
            },
            'subsidiary_1': {
                'name': sub1['name'] if sub1 else '',
                'papers': sub1['papers'] if sub1 else [],
                'total_max': sub1['total_max'] if sub1 else 0,
                'total_pass': sub1['total_pass'] if sub1 and 'total_pass' in sub1 else int((sub1['total_max'] if sub1 else 0) * 0.33),
                'total_obtained': sub1['total_obtained'] if sub1 else 0
            },
            'subsidiary_2': {
                'name': sub2['name'] if sub2 else '',
                'papers': sub2['papers'] if sub2 else [],
                'total_max': sub2['total_max'] if sub2 else 0,
                'total_pass': sub2['total_pass'] if sub2 and 'total_pass' in sub2 else int((sub2['total_max'] if sub2 else 0) * 0.33),
                'total_obtained': sub2['total_obtained'] if sub2 else 0
            },
            'composition': {
                'name': 'Composition',
                'papers': composition_papers,
                'total_max': comp_total_max,
                'total_pass': int(comp_total_max * 0.33),
                'total_obtained': comp_total_obt
            },
        },
        'grand_total_max': grand_total_max,
        'grand_total': final_grand_total,
        'result_status': calculate_ba_hons_part1_result(
            hons_total_obt, hons_total_max,
            sub1.get('total_obtained', 0) if sub1 else 0, sub1.get('total_max', 0) if sub1 else 0,
            sub2.get('total_obtained', 0) if sub2 else 0, sub2.get('total_max', 0) if sub2 else 0,
            comp_total_obt, comp_total_max
        ),
        'hons_total_words': num2words(hons_total_obt),
        'grand_total_words': num2words(final_grand_total) + " Only",
        'publication_date': exam.publication_date.strftime("%d-%m-%Y") if exam.publication_date else "N/A",
        
        # Generate QR code
        'qr_code': generate_qr_code_base64(
            generate_ug_marksheet_qr_text(
                student, 
                exam, 
                final_grand_total
            )
        ),
        
        # Images
        'university_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'watermark_logo': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/purnea-logo.png")),
        'controller_signature': image_to_base64(os.path.join(settings.BASE_DIR, "static/images/controller-of-examination-signature.png")),
    }

    return context

def generate_ug_old_ba_hons_part1_pdf(student, exam_part='1', exam_type=None, course_code=None, batch_code=None):
    """
    Generate marksheet PDF for UG Before CBCS student Part 1.
    Only generates PDF if validation passes.
    
    Returns:
        tuple: (pdf_content: bytes or None, error_message: str or None)
    """
    context = get_ug_old_ba_hons_part1_context(student, exam_part, exam_type, course_code, batch_code)
    
    if not context:
        return None, "No results found for this student and exam part"
    
    # Validate before generating PDF
    is_valid, error_messages = validate_marksheet_context(student, exam_part, context, exam_type, course_code, batch_code)
    if not is_valid:
        error_detail = "; ".join(error_messages)
        logger.error(f"Marksheet validation failed for {student.registration_no} (Part {exam_part}): {error_detail}")
        return None, error_detail

    template_name = f"ug_before_cbcs/ba_hons_marksheet_part1.html"
    
    html_string = get_template(template_name).render(context)
    
    try:
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        return pdf_file, None
    except Exception as e:
        error_msg = f"PDF generation error: {str(e)}"
        print("PDF ERROR:", error_msg) 
        logger.error(f"Error generating PDF: {e}")
        return None, error_msg

def get_ug_old_ba_hons_part1_latest_context(student, exam_part='1', course_code=None, session_code=None):
    """
    Get the latest consolidated marksheet context.
    Combines ALL papers (REGULAR + BACK), with the latest session_code taking precedence for duplicates.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam_part: Part number as string ('1', '2', or '3')
        course_code: Optional course code filter
        session_code: Optional specific session code filter
    
    Returns:
        Context dictionary for marksheet generation
    """
    part_code = f"PART{exam_part}"
    
    # Get ALL results for this part
    all_results = UGBeforeCBCSStudentResult.objects.filter(
        student=student,
        exam__part=part_code
    )
    
    if course_code:
        all_results = all_results.filter(exam__course_code__iexact=course_code)
    
    if session_code:
        all_results = all_results.filter(exam__session_code=session_code)
    
    all_results = all_results.select_related('exam').order_by('exam__session_code')
    
    if not all_results.exists():
        logger.warning(f"No results found for {student.registration_no} / {part_code}")
        return None
    
    # Build a map with latest session_code taking precedence
    # Key: (paper_code, status), Value: result object
    latest_papers = {}
    
    for result in all_results:
        key = (result.paper_code, result.status)
        
        # If key exists, compare session_codes and keep the latest
        if key in latest_papers:
            existing_session = latest_papers[key].exam.session_code if latest_papers[key].exam else ''
            current_session = result.exam.session_code if result.exam else ''
            
            # Keep the one with the later session_code
            if current_session > existing_session:
                latest_papers[key] = result
                logger.info(f"Override: {result.paper_code} {result.status} - {existing_session} → {current_session}")
        else:
            latest_papers[key] = result
    
    # Now use the existing context function with these filtered results
    # We'll pass the results as a custom queryset
    return get_ug_old_ba_hons_part1_context(
        student, 
        exam_part=exam_part, 
        exam_type=None,  # Don't filter by exam_type
        course_code=course_code, 
        batch_code=None,
        custom_results=list(latest_papers.values())
    )

def get_center_info_for_student(student, exam):
    """
    Get the examination center information for a student from the mapping table.
    Returns complete college object if available, otherwise just the name.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam: UGBeforeCBCSExam instance
    
    Returns:
        dict: Center information with uid, name, etc. or just name string
    """
    from ..models import UGBeforeCBCSExamCenterMapping
    
    if not student.college:
        return {
            'name': exam.centre_name,
            'uid': None,
            'college_code': None
        } if exam.centre_name else None
    
    mapping = UGBeforeCBCSExamCenterMapping.objects.filter(
        exam=exam,
        student_college=student.college
    ).select_related('center_college').first()
    
    if mapping:
        # Priority: center_college > center_name > exam.centre_name
        if mapping.center_college:
            return {
                'uid': str(mapping.center_college.uid),
                'name': mapping.center_college.name,
                'college_code': mapping.center_college.college_code,
                'short_name': mapping.center_college.short_name,
                'address': mapping.center_college.address,
            }
        elif mapping.center_name:
            return {
                'name': mapping.center_name,
                'uid': None,
                'college_code': None
            }
    
    # Fallback to exam's centre_name
    if exam.centre_name:
        return {
            'name': exam.centre_name,
            'uid': None,
            'college_code': None
        }
    
    return None

def get_ug_old_ba_hons_part1_progressive_contexts(student, exam_part='1', course_code=None, batch_code=None):
    """
    Generates year-by-year progressive BACK paper contexts.
    Shows how BACK papers progressively override REGULAR papers over the years.
    
    Logic:
    - Get all REGULAR papers (base marksheet)
    - For each year with BACK papers, show cumulative state:
      - Year 1 BACK: REGULAR + Year 1 BACK overrides
      - Year 2 BACK: REGULAR + Year 1 BACK + Year 2 BACK overrides
      - Year 3 BACK: REGULAR + Year 1 BACK + Year 2 BACK + Year 3 BACK overrides
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam_part: Part number as string ('1', '2', or '3')
        course_code: Optional course code filter
        batch_code: Optional batch code filter
    
    Returns:
        List of dictionaries for each BACK session showing progressive state
    """
    part_code = f"PART{exam_part}"
    
    # Get ALL results for this part
    all_results = UGBeforeCBCSStudentResult.objects.filter(
        student=student,
        exam__part=part_code
    )
    
    if course_code:
        all_results = all_results.filter(exam__course_code__iexact=course_code)
    if batch_code:
        all_results = all_results.filter(exam__batch_code=batch_code)
    
    all_results = all_results.select_related('exam').order_by('exam__session_code', 'exam_type')
    
    if not all_results.exists():
        logger.warning(f"No results found for {student.registration_no} / {part_code}")
        return []
    
    # Separate REGULAR and BACK papers
    regular_papers = {}  # {(paper_code, status): result}
    back_sessions = {}   # {session_code: [back_results]}
    all_sessions = set()  # Track all unique session codes
    
    for result in all_results:
        exam_type = (result.exam_type or '').upper()
        key = (result.paper_code, result.status)
        session = result.exam.session_code or 'UNKNOWN'
        
        # Track all sessions
        if session:
            all_sessions.add(session)
        
        if exam_type == 'BACK':
            if session not in back_sessions:
                back_sessions[session] = []
            back_sessions[session].append(result)
        else:
            # REGULAR - only add if not already present
            if key not in regular_papers:
                regular_papers[key] = result
    
    # If no BACK papers, return only REGULAR papers
    if not back_sessions:
        logger.info(f"No BACK papers found for {student.registration_no} Part {exam_part}. Returning REGULAR papers only.")
        
        # Return just the REGULAR result
        if not regular_papers:
            return {'results': [], 'available_sessions': []}
        
        first_regular = next(iter(regular_papers.values()))
        return {
            'results': [{
                'type': 'regular',
                'session_code': first_regular.exam.session_code if first_regular.exam else None,
                'exam_year': first_regular.exam.exam_year if first_regular.exam else None,
                'exam_month_year': first_regular.exam.exam_month_year if first_regular.exam else None,
                'publication_date': first_regular.exam.publication_date if first_regular.exam else None,
                'centre': get_center_info_for_student(student, first_regular.exam) if first_regular.exam else None,
                'exam_name': first_regular.exam.name if first_regular.exam else f"Part {exam_part}",
                'result': {
                    'total_papers': len(regular_papers),
                    'papers': [
                        {
                            'paper_code': result.paper_code,
                            'subject_name': result.subject_name,
                            'status': result.status,
                            'exam_type': result.exam_type,
                            'session_code': result.exam.session_code if result.exam else None,
                            'mark_secured': result.mark_secured,
                            'maximum_mark': result.maximum_mark,
                            'pass_mark': result.pass_mark,
                        }
                        for result in regular_papers.values()
                    ]
                }
            }],
            'available_sessions': sorted(list(all_sessions))
        }
    
    # Sort BACK sessions chronologically
    sorted_back_sessions = sorted(back_sessions.keys())
    
    # Helper function to format papers
    def format_papers(papers_dict):
        return [
            {
                'uid': str(result.uid),
                'paper_code': result.paper_code,
                'subject_name': result.subject_name,
                'status': result.status,
                'exam_type': result.exam_type,
                'paper_type_code': result.paper_type_code,
                'session_code': result.exam.session_code if result.exam else None,
                'mark_secured': result.mark_secured,
                'maximum_mark': result.maximum_mark,
                'pass_mark': result.pass_mark,
            }
            for result in papers_dict.values()
        ]
    
    # Build progressive results: REGULAR base + BACK by year
    results_list = []
    
    # 1. Add REGULAR result (base)
    if regular_papers:
        first_regular = next(iter(regular_papers.values()))
        results_list.append({
            'type': 'regular',
            'session_code': first_regular.exam.session_code if first_regular.exam else None,
            'exam_code': first_regular.exam.exam_code if first_regular.exam else None,
            'exam_year': first_regular.exam.exam_year if first_regular.exam else None,
            'exam_month_year': first_regular.exam.exam_month_year if first_regular.exam else None,
            'publication_date': first_regular.exam.publication_date if first_regular.exam else None,
            'centre': get_center_info_for_student(student, first_regular.exam) if first_regular.exam else None,
            'exam_name': first_regular.exam.name if first_regular.exam else f"Part {exam_part}",
            'result': {
                'total_papers': len(regular_papers),
                'papers': format_papers(regular_papers)
            }
        })
    
    # 2. Add BACK results year by year (only BACK papers, no REGULAR)
    cumulative_back_map = {}  # Cumulative BACK papers across years
    
    for idx, session in enumerate(sorted_back_sessions):
        back_results = back_sessions[session]
        
        # Add BACK papers from this session to cumulative map
        for result in back_results:
            key = (result.paper_code, result.status)
            cumulative_back_map[key] = result
            logger.info(f"Session {session}: Added/Updated BACK {result.paper_code} {result.status}")
        
        first_exam = back_results[0].exam
        
        results_list.append({
            'type': 'back',
            'session_code': session,
            'exam_code': first_exam.exam_code if first_exam else None,
            'exam_year': first_exam.exam_year if first_exam else None,
            'exam_month_year': first_exam.exam_month_year if first_exam else None,
            'publication_date': first_exam.publication_date if first_exam else None,
            'centre': get_center_info_for_student(student, first_exam) if first_exam else None,
            'exam_name': first_exam.name if first_exam else f"Part {exam_part} - {session}",
            'is_latest': (idx == len(sorted_back_sessions) - 1),
            'result': {
                'back_papers_in_this_session': len(back_results),
                'cumulative_back_papers': len(cumulative_back_map),
                'papers': format_papers(cumulative_back_map)
            }
        })
        
        logger.info(f"Progressive BACK for {student.registration_no} - Session {session}: "
                   f"{len(back_results)} new BACK, {len(cumulative_back_map)} total cumulative BACK")
    
    # Return results with available sessions for filtering
    return {
        'results': results_list,
        'available_sessions': sorted(list(all_sessions))
    }
