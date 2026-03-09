import logging
from ug_before_cbcs.models import UGBeforeCBCSStudentResult

logger = logging.getLogger(__name__)

def validate_marksheet_context(student, exam_part, context, exam_type=None, course_code=None, batch_code=None):
    """
    Validates marksheet context data before PDF generation.
    Extracts data from context and validates completeness.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam_part: Part number as string ('1', '2', or '3')
        context: Context dictionary from get_ug_old_ba_hons_part1_context
        exam_type: Optional exam type filter
        course_code: Optional course code filter
        batch_code: Optional batch code filter
    
    Returns:
        tuple: (is_valid: bool, error_messages: list)
    """
    if not context:
        return False, ["Context is empty or None"]
    
    # Extract data from context
    honours_papers = context.get('subjects', {}).get('honours', {}).get('papers', [])
    composition_papers = context.get('subjects', {}).get('composition', {}).get('papers', [])
    sub1_data = context.get('subjects', {}).get('subsidiary_1', {})
    sub2_data = context.get('subjects', {}).get('subsidiary_2', {})
    
    sub1 = sub1_data if sub1_data.get('name') else None
    sub2 = sub2_data if sub2_data.get('name') else None
    
    # Get results from database
    part_code = f"PART{exam_part}"
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
    
    results = results_query.order_by('paper_code')
    
    # Validate using the existing function
    return validate_marksheet_data(student, exam_part, honours_papers, composition_papers, sub1, sub2, results)

def validate_marksheet_data(student, exam_part, honours_papers, composition_papers, sub1, sub2, results):
    """
    Validates if the student has the minimum required papers for marksheet generation.
    
    Returns:
        tuple: (is_valid: bool, error_messages: list)
    """
    is_valid = True
    error_messages = []

    # 1. Validate Honours papers (must have at least 2)
    if len(honours_papers) < 2:
        is_valid = False
        error_messages.append(f"Honours papers not available. Found {len(honours_papers)}, required minimum 2.")

    # 2. Validate Subsidiary subjects (must have sub1 and sub2)
    if not sub1:
        is_valid = False
        error_messages.append("Subsidiary Subject 1 not available.")
    if not sub2:
        is_valid = False
        error_messages.append("Subsidiary Subject 2 not available.")

    # 3. Validate Composition papers
    is_rbh_student = any(p.paper_type_code == 'RB' for p in results)
    is_nrb_student = any(p.paper_type_code == 'NRB' for p in results)
    
    if is_rbh_student and len(composition_papers) < 1:
        is_valid = False
        error_messages.append(f"RBH Composition paper not available. Found {len(composition_papers)}, required 1.")
    elif is_nrb_student and len(composition_papers) < 2:
        is_valid = False
        error_messages.append(f"NRB Composition papers not available. Found {len(composition_papers)}, required 2 (Non-Hindi + MB).")
    elif not is_rbh_student and not is_nrb_student and not composition_papers:
        is_valid = False
        error_messages.append("Composition papers not available (neither RBH nor NRB detected).")

    if not is_valid:
        logger.warning(f"Validation failed for {student.registration_no} (Part {exam_part}): {'; '.join(error_messages)}")
        return False, error_messages
        
    return True, []
