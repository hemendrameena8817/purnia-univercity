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

def has_back_papers(results):
    """
    Check if any of the given results contain BACK exam papers.
    
    Args:
        results: List of UGBeforeCBCSStudentResult objects
    
    Returns:
        bool: True if any BACK papers are found
    """
    return any(result.exam_type and result.exam_type.upper() == 'BACK' for result in results)


def _normalize_mark(value):
    """Convert mark to float when possible, otherwise return None."""
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_display_mark(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _get_pass_marks(paper, subject_key):
    """Fetch pass marks for a paper with sensible fallbacks."""
    # Composition papers always use fixed thresholds (15 for 50-mark papers, otherwise 33)
    if subject_key == 'composition':
        max_marks = _normalize_mark(paper.get('max_marks'))
        if max_marks is not None and max_marks <= 50:
            return 15
        return 33

    pass_mark = paper.get('pass_marks')
    normalized = _normalize_mark(pass_mark)
    if normalized is not None:
        return _coerce_display_mark(normalized)

    # Fallbacks when individual pass marks are unavailable
    max_marks = _normalize_mark(paper.get('max_marks'))
    if max_marks is not None:
        return _coerce_display_mark(max_marks * 0.33)
    return 0.0


def calculate_back_subject_summary(subjects, session_code=None):
    """
    Determine BACK subject status across Honours, Subsidiaries, and Composition.
    Returns a dictionary with totals and final qualification status.
    """
    if not subjects:
        return {
            'subjects': [],
            'total': 0,
            'passed': 0,
            'failed': 0,
            'result': None,
        }

    summary = []
    subject_order = ['honours', 'subsidiary_1', 'subsidiary_2', 'composition']

    for subject_key in subject_order:
        subject_data = subjects.get(subject_key)
        if not subject_data:
            continue

        papers = subject_data.get('papers', [])
        back_papers = []
        for paper in papers:
            if (paper.get('exam_type', '').upper() != 'BACK'):
                continue
            if session_code and paper.get('session_code') and paper.get('session_code') != session_code:
                continue
            if session_code and not paper.get('session_code'):
                continue
            back_papers.append(paper)
        if not back_papers:
            continue

        subject_passed = True
        for paper in back_papers:
            obtained = _normalize_mark(paper.get('obtained'))
            pass_mark = _get_pass_marks(paper, subject_key)
            if obtained is None or obtained < pass_mark:
                subject_passed = False
                break

        summary.append({
            'subject': subject_key,
            'passed': subject_passed,
        })

    total = len(summary)
    failed = len([item for item in summary if not item['passed']])
    passed = total - failed

    if total == 0:
        result = None
    elif failed == 0:
        result = 'QUALIFIED'
    elif failed == total:
        result = 'NOT QUALIFIED'
    else:
        result = 'PARTIALLY QUALIFIED'

    return {
        'subjects': summary,
        'total': total,
        'passed': passed,
        'failed': failed,
        'result': result,
    }


def calculate_back_total_marks(subjects, session_code=None):
    total_marks = 0.0
    if not subjects:
        return 0

    subject_order = ['honours', 'subsidiary_1', 'subsidiary_2', 'composition']

    for subject_key in subject_order:
        subject_data = subjects.get(subject_key) if subjects else None
        if not subject_data:
            continue

        for paper in subject_data.get('papers', []):
            if (paper.get('exam_type', '') or '').upper() != 'BACK':
                continue
            if session_code and paper.get('session_code') and paper.get('session_code') != session_code:
                continue
            if session_code and not paper.get('session_code'):
                continue

            obtained = _normalize_mark(paper.get('obtained'))
            if obtained is not None:
                total_marks += obtained

    if total_marks == 0:
        return 0
    return _coerce_display_mark(total_marks)


def subject_has_back(papers, session_code=None):
    """Helper to determine if any paper in the collection is BACK for the requested session."""
    if not papers:
        return False

    for paper in papers:
        if (paper.get('exam_type') or '').upper() != 'BACK':
            continue
        if session_code and paper.get('session_code') and paper.get('session_code') != session_code:
            continue
        if session_code and not paper.get('session_code'):
            # When session filtering is requested but paper lacks session info, skip it
            continue
        return True
    return False

def get_ug_old_ba_hons_part1_context(
    student,
    exam_part='1',
    course_code=None,
    custom_results=None,
    requested_session_code=None,
):
    """
    Prepares and returns the context dictionary for the UG Before CBCS BA Hons Part 1 marksheet.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam_part: Part number as string ('1', '2', or '3')
        course_code: Optional course code filter
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
        
        # If requested_session_code is provided, try to find an exam from that session
        # Otherwise use the first result's exam
        if requested_session_code:
            session_result = next(
                (r for r in results if r.exam and r.exam.session_code == requested_session_code),
                None
            )
            if session_result:
                exam = session_result.exam
                first_result = session_result
                logger.info(f"Using exam from requested session {requested_session_code}: {exam.name}")
            else:
                # Fallback to first result if no match found
                first_result = results[0]
                exam = first_result.exam
                logger.warning(f"No exam found for session {requested_session_code} in custom results, using: {exam.session_code}")
        else:
            first_result = results[0]
            exam = first_result.exam
    else:
        # Get all student results for this part
        results_query = UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam__part=part_code
        )
            
        if course_code:
            results_query = results_query.filter(exam__course_code__iexact=course_code)
        
        # If a specific session is requested, try to find exam matching that session first
        if requested_session_code:
            # Look for results with the requested session code
            session_result = results_query.filter(
                exam__session_code=requested_session_code
            ).select_related('exam').first()
            
            if session_result:
                exam = session_result.exam
                first_result = session_result
                logger.info(f"Using exam for requested session {requested_session_code}: {exam.name}")
            else:
                # Fallback to latest exam if no results found for requested session
                first_result = results_query.select_related('exam').order_by('-exam__exam_year').first()
                if first_result:
                    exam = first_result.exam
                    logger.warning(f"No results found for session {requested_session_code}, using latest exam: {exam.name}")
                else:
                    logger.warning(f"No results found for {student.registration_no} / {part_code}")
                    return None
        else:
            # No session requested - use latest exam by year
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
            'exam_type': result.exam_type.upper() if result.exam_type else '',
            'session_code': result.exam.session_code if result.exam else None,
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

    def _detect_composition_track(paper, res_obj):
        name = (paper.get('name') or '').upper()
        code = (paper.get('paper_code') or '').upper()
        type_code = res_obj.paper_type_code.upper() if res_obj and res_obj.paper_type_code else ''

        if type_code == 'NRB':
            return 'NRB'
        if type_code == 'RB':
            return 'RB'
        if any(token in name for token in ['NON-HINDI', 'MB']) or 'NRB' in code:
            return 'NRB'
        if 'RASTRABHASH' in name or 'RBH' in code or 'R.B' in code:
            return 'RB'
        return None

    # Sort Composition papers and assign display names
    # e.g. BA104 (RB or NRB) and BA105 (MB if NRB)
    comp_papers_raw = sorted(composition_papers, key=lambda x: x['paper_code'])
    comp_papers_augmented = []
    composition_tracks_present = set()
    for p in comp_papers_raw:
        res_obj = next((r for r in results if r.uid == p['uid']), None)
        track = _detect_composition_track(p, res_obj)
        if track:
            composition_tracks_present.add(track)
        comp_papers_augmented.append((p, res_obj, track))

    preferred_track = None
    if 'NRB' in composition_tracks_present:
        preferred_track = 'NRB'
    elif 'RB' in composition_tracks_present:
        preferred_track = 'RB'

    final_composition_papers = []
    composition_individual_fail = False
    composition_total_pass = 0

    for p, res_obj, track in comp_papers_augmented:
        if preferred_track and track and track != preferred_track:
            continue

        p_type = res_obj.paper_type_code.upper() if res_obj and res_obj.paper_type_code else ""
        p_code = p['paper_code'].upper() if p['paper_code'] else ""

        normalized_max = _normalize_mark(p.get('max_marks'))
        normalized_pass = _normalize_mark(p.get('pass_marks'))

        if track == 'NRB':
            if normalized_max is None or normalized_max > 50:
                p['max_marks'] = 50
                normalized_max = 50
            if normalized_pass is None or normalized_pass > 15:
                p['pass_marks'] = 15
        elif track == 'RB':
            if normalized_max is None or normalized_max < 100:
                p['max_marks'] = 100
                normalized_max = 100
            if normalized_pass is None or normalized_pass < 33:
                p['pass_marks'] = 33

        if p_type == 'RB' or 'RBH' in p_code or 'R.B' in p_code:
            p['display_name'] = "Rastrabhasha hindi"
        elif p_type == 'NRB' or 'Non-Hindi' in p['name']:
            if any(s in p_code for s in ['104', '204']):
                p['display_name'] = "Non-Hindi"
            else:
                p['display_name'] = f"MB: {p['name'].title()}"
        else:
            p['display_name'] = p['name']

        paper_pass = _get_pass_marks(p, 'composition')
        p['pass_marks'] = paper_pass
        composition_total_pass += paper_pass

        obtained_mark = _normalize_mark(p.get('obtained'))
        if obtained_mark is None or obtained_mark < paper_pass:
            composition_individual_fail = True

        final_composition_papers.append(p)

    composition_papers = final_composition_papers

    if preferred_track == 'NRB' and composition_total_pass < 33:
        composition_total_pass = 33

    # Get honours subject name to check for Music special case
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

    # Organize and rename Honours papers
    is_honours_with_practical = False
    organized_honours = []
    paper1 = None
    paper2 = None
    practical = None

    # First, check if there's a practical components for Honours
    has_hons_practical = any(p['status'] == 'LAB' for p in honours_papers)
    is_honours_with_practical = has_hons_practical

    # Check if this is Music subject (case-insensitive)
    is_music_subject = honours_subject_name and 'MUSIC' in honours_subject_name.upper()
    
    # Check if this is BSC Chemistry Part-I (special case)
    is_bsc_chemistry_part1 = (
        course_code and 'BSC' in course_code.upper() and 
        honours_subject_name and 'CHEMISTRY' in honours_subject_name.upper() and
        str(exam_part) == '1'
    )
    
    print(f"DEBUG: is_bsc_chemistry_part1={is_bsc_chemistry_part1}")
    print(f"DEBUG: has_hons_practical={has_hons_practical}")
    print(f"DEBUG: honours_papers count={len(honours_papers)}")
    print(f"DEBUG: honours_papers statuses: {[p['status'] for p in honours_papers]}")

    # Special handling for Music subject: 
    # Music has only 1 END_TERM (100 marks) + 1 LAB (100 marks)
    # Should show as separate rows: Paper-I + Practical (no Paper-II)
    if is_music_subject and has_hons_practical:
        print("DEBUG: Entering Music logic...")
        # For Music: keep END_TERM and LAB separate but adjust max marks and names
        end_term_paper = next((p for p in honours_papers if p['status'] == 'END_TERM'), None)
        lab_paper = next((p for p in honours_papers if p['status'] == 'LAB'), None)
        
        if end_term_paper and lab_paper:
            # Update END_TERM paper to be Paper-I with 100 marks
            end_term_paper['name'] = 'Paper-I' if str(exam_part) == '1' else 'Paper-II'
            end_term_paper['max_marks'] = 100
            end_term_paper['pass_marks'] = 40  # 40% of 100
            
            # Update LAB paper to be Practical with 100 marks
            lab_paper['name'] = 'Practical'
            lab_paper['max_marks'] = 100
            lab_paper['pass_marks'] = 40  # 40% of 100
            
            # Calculate totals (100 + 100 = 200)
            hons_total_obt = 0
            hons_total_max = 200
            
            if isinstance(end_term_paper['obtained'], (int, float)):
                hons_total_obt += end_term_paper['obtained']
            if isinstance(lab_paper['obtained'], (int, float)):
                hons_total_obt += lab_paper['obtained']
            
            # Keep papers separate (don't combine)
            organized_honours = [end_term_paper, lab_paper]
            honours_papers = organized_honours
        else:
            # Fallback to regular processing if papers missing
            pass

    # Special handling for BSC Chemistry Part-I:
    # BSC Chemistry has 3 END_TERM papers (END_TERM, END2_TERM, END3_TERM) + 1 LAB paper
    # All papers have 50 marks each
    elif is_bsc_chemistry_part1 and has_hons_practical:
        print("DEBUG: Entering BSC Chemistry logic...")
        # Get all END_TERM, END2_TERM, END3_TERM papers for Chemistry
        end_term_papers = [p for p in honours_papers if p['status'] in ['END_TERM', 'END2_TERM', 'END3_TERM']]
        lab_paper = next((p for p in honours_papers if p['status'] == 'LAB'), None)
        
        print(f"DEBUG: Found {len(end_term_papers)} theory papers and 1 lab paper: {lab_paper is not None}")
        
        if len(end_term_papers) == 3 and lab_paper:
            # Sort END_TERM papers by status to ensure consistent ordering
            status_order = {'END_TERM': 0, 'END2_TERM': 1, 'END3_TERM': 2}
            end_term_papers.sort(key=lambda x: status_order.get(x['status'], 999))
            
            # Name them as I A, I B, I C
            paper_names = ['I A', 'I B', 'I C']
            for i, paper in enumerate(end_term_papers):
                paper['name'] = paper_names[i]
                paper['max_marks'] = 50
                paper['pass_marks'] = 20  # 40% of 50
            
            # Update LAB paper
            lab_paper['name'] = 'Practical'
            lab_paper['max_marks'] = 50
            lab_paper['pass_marks'] = 20  # 40% of 50
            
            # Calculate totals (50*3 + 50 = 200)
            hons_total_obt = 0
            hons_total_max = 200
            
            for paper in end_term_papers:
                if isinstance(paper['obtained'], (int, float)):
                    hons_total_obt += paper['obtained']
            
            if isinstance(lab_paper['obtained'], (int, float)):
                hons_total_obt += lab_paper['obtained']
            
            # Keep all 4 papers separate
            organized_honours = end_term_papers + [lab_paper]
            honours_papers = organized_honours
            print("DEBUG: BSC Chemistry processing completed!")
        else:
            print(f"DEBUG: BSC Chemistry fallback - end_term_papers: {len(end_term_papers)}, lab_paper: {lab_paper is not None}")
    else:
        print(f"DEBUG: Not entering special logic - is_bsc_chemistry_part1={is_bsc_chemistry_part1}, has_hons_practical={has_hons_practical}")

    # Regular processing for non-special subjects or fallback
    if not is_music_subject and not is_bsc_chemistry_part1:
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
            subject_name = (sub.get('name') or '').upper()
            is_music_subsidiary = 'MUSIC' in subject_name

            if is_music_subsidiary:
                theory_max_marks = 50
                practical_max_marks = 50
                theory_pass_marks = 15
                practical_pass_marks = 20
            else:
                theory_max_marks = 75
                practical_max_marks = 25
                theory_pass_marks = 23
                practical_pass_marks = 10

            for p in sub['papers']:
                if 'END' in p['status']: # Theory
                    p['name'] = 'Theory'
                    p['max_marks'] = theory_max_marks
                    p['pass_marks'] = theory_pass_marks
                else: # Practical
                    p['name'] = 'Practical'
                    p['max_marks'] = practical_max_marks
                    p['pass_marks'] = practical_pass_marks
            
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
                'total_pass': composition_total_pass,
                'total_obtained': comp_total_obt,
                'has_individual_fail': composition_individual_fail,
            },
        },
        'grand_total_max': grand_total_max,
        'grand_total': final_grand_total,
        'result_status': calculate_ba_hons_part1_result(
            hons_total_obt, hons_total_max,
            sub1.get('total_obtained', 0) if sub1 else 0, sub1.get('total_max', 0) if sub1 else 0,
            sub2.get('total_obtained', 0) if sub2 else 0, sub2.get('total_max', 0) if sub2 else 0,
            comp_total_obt, comp_total_max,
            composition_individual_fail=composition_individual_fail,
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

    context['requested_session_code'] = requested_session_code
    subjects_context = context.get('subjects', {})
    back_summary = calculate_back_subject_summary(subjects_context, requested_session_code)
    context['back_summary'] = back_summary
    context['back_result'] = back_summary.get('result')

    subject_flags = {}
    for subject_key in ['honours', 'subsidiary_1', 'subsidiary_2', 'composition']:
        subject_data = subjects_context.get(subject_key) or {}
        has_back_flag = subject_has_back(subject_data.get('papers'), requested_session_code)
        subject_data['has_back'] = has_back_flag
        subject_flags[f"{subject_key}_has_back"] = has_back_flag

    context.update(subject_flags)
    context['composition_has_back'] = subject_flags.get('composition_has_back', False)
    context['show_back_totals'] = back_summary.get('total', 0) > 0
    back_total_marks = calculate_back_total_marks(subjects_context, requested_session_code)
    context['back_total_marks_obtained'] = back_total_marks

    # Regenerate QR code with back total if back papers exist
    if context['show_back_totals'] and back_total_marks > 0:
        context['qr_code'] = generate_qr_code_base64(
            generate_ug_marksheet_qr_text(
                student, 
                exam, 
                back_total_marks
            )
        )

    return context

def get_bsc_chemistry_part1_context(student, exam_part=None, course_code=None, session_code=None):
    """
    Special context generator for BSC Chemistry Part-I with 4 papers (I A, I B, I C, Practical)
    """
    logger.info(f"Generating BSC Chemistry Part-I context for {student.registration_no}")
    
    # Get the consolidated context first (without session_code since the base function doesn't support it)
    context = get_ug_old_ba_hons_part1_context(
        student,
        exam_part=exam_part,
        course_code=course_code,
        requested_session_code=session_code,
    )
    
    # Override the template name for BSC Chemistry Part-I
    context['template_name'] = 'ug_before_cbcs/bsc_chemistry_part1_marksheet.html'
    
    # Ensure the honours papers are correctly ordered for Chemistry
    if 'subjects' in context and 'honours' in context['subjects']:
        honours_papers = context['subjects']['honours']['papers']
        
        # Sort papers by status: END_TERM, END2_TERM, END3_TERM, LAB
        status_order = {'END_TERM': 0, 'END2_TERM': 1, 'END3_TERM': 2, 'LAB': 3}
        honours_papers.sort(key=lambda x: status_order.get(x.get('status', ''), 999))
        
        # Update paper names to match the expected format
        paper_names = ['I A', 'I B', 'I C', 'Practical']
        for i, paper in enumerate(honours_papers):
            if i < len(paper_names):
                paper['name'] = paper_names[i]
                paper['max_marks'] = 50
                paper['pass_marks'] = 20  # 40% of 50
        
        logger.info(f"Processed {len(honours_papers)} BSC Chemistry papers")
    
    return context

def get_ug_old_ba_hons_part1_latest_context(student, exam_part='1', course_code=None, session_code=None):
    """
    Get the latest consolidated marksheet context.
    Combines ALL papers (REGULAR + BACK), with the latest session_code taking precedence for duplicates.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam_part: Part number as string ('1', '2', or '3')
        course_code: Optional course code filter
        session_code: Optional specific session code filter
            - If provided, tries to use data from that session
            - If papers are missing in that session, falls back to data from EARLIER sessions only
            - Never uses papers from sessions newer than the requested session_code
    
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
    
    all_results = all_results.select_related('exam').order_by('exam__session_code')
    
    if not all_results.exists():
        logger.warning(f"No results found for {student.registration_no} / {part_code}")
        return None
    
    # Build a map with latest session_code taking precedence
    # Key: (paper_code, status), Value: result object
    latest_papers = {}
    
    for result in all_results:
        key = (result.paper_code, result.status)
        result_session = result.exam.session_code if result.exam else ''
        
        # If session_code is specified, prioritize papers from that session and earlier
        if session_code:
            # If we want papers from a specific session, only use those from that session or earlier
            if result_session == session_code:
                latest_papers[key] = result
                logger.debug(f"Using {result.paper_code} from requested session {session_code}")
            elif key not in latest_papers and result_session <= session_code:
                # Only use earlier sessions if the paper is not available in the requested session
                latest_papers[key] = result
                logger.debug(f"Using {result.paper_code} from earlier session {result_session} (not available in {session_code})")
            elif key not in latest_papers and result_session > session_code:
                # Don't use papers from newer sessions than requested
                logger.debug(f"Skipping {result.paper_code} from newer session {result_session} (requested: {session_code})")
        else:
            # No session specified - use latest logic
            if key in latest_papers:
                existing_session = latest_papers[key].exam.session_code if latest_papers[key].exam else ''
                
                # Keep the one with the later session_code
                if result_session > existing_session:
                    latest_papers[key] = result
                    logger.info(f"Override: {result.paper_code} {result.status} - {existing_session} → {result_session}")
            else:
                latest_papers[key] = result
    
    # Now use the existing context function with these filtered results
    # We'll pass the results as a custom queryset
    return get_ug_old_ba_hons_part1_context(
        student,
        exam_part=exam_part,
        course_code=course_code,
        custom_results=list(latest_papers.values()),
        requested_session_code=session_code,
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
    
    # If no BACK papers, return only REGULAR papers
    if not back_sessions:
        logger.info(f"No BACK papers found for {student.registration_no} Part {exam_part}. Returning REGULAR papers only.")
        
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
                    'papers': format_papers(regular_papers)
                }
            }],
            'available_sessions': sorted(list(all_sessions))
        }
    
    # Sort BACK sessions chronologically
    sorted_back_sessions = sorted(back_sessions.keys())
    
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
                'papers': format_papers(dict(enumerate(back_results)))
            }
        })
        
        logger.info(f"Progressive BACK for {student.registration_no} - Session {session}: "
                   f"{len(back_results)} new BACK, {len(cumulative_back_map)} total cumulative BACK")
    
    # Return results with available sessions for filtering
    return {
        'results': results_list,
        'available_sessions': sorted(list(all_sessions))
    }
