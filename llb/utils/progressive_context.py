"""
Progressive marksheet context generator for LLB.
Shows all raw entries grouped: REGULAR together, BACK grouped by session.
No cumulative override logic - that is only for PDF generation.
"""
import logging
from ..models import LLBStudentCourseAssessment
from .calculate_res import calculate_llb_result

logger = logging.getLogger(__name__)


def get_llb_progressive_contexts(student, semester):
    """
    Returns all raw assessment entries for a student in a semester,
    grouped by exam type:
      - REGULAR: one group with all subjects
      - BACK: grouped by session, each showing only that session's back papers
    
    Frontend can use this data to display, create, update, or delete entries.
    
    Args:
        student: LLBStudentProfile instance
        semester: Semester code (e.g., '1ST', '2ND', '3RD')
    
    Returns:
        Dictionary with 'results' and 'available_sessions'
    """
    all_assessments = LLBStudentCourseAssessment.objects.filter(
        student=student,
        semester=semester
    ).select_related('exam', 'course_structure').order_by('exam__session', 'paper_code')
    
    if not all_assessments.exists():
        logger.warning(f"No assessments found for {student.registration_no} / {semester}")
        return {'results': [], 'available_sessions': []}
    
    # Separate REGULAR and BACK papers
    regular_assessments = []
    back_sessions = {}   # {session: [assessments]}
    all_sessions = set()
    regular_exam = None
    
    for assessment in all_assessments:
        exam_type = (assessment.exam_type or '').upper()
        session = assessment.exam.session if assessment.exam else 'UNKNOWN'
        
        if session:
            all_sessions.add(session)
        
        if exam_type == 'BACK':
            if session not in back_sessions:
                back_sessions[session] = []
            back_sessions[session].append(assessment)
        else:
            regular_assessments.append(assessment)
            if not regular_exam and assessment.exam:
                regular_exam = assessment.exam
    
    def format_assessment(a):
        return {
            'uid': str(a.uid),
            'paper_code': a.paper_code,
            'subject_name': a.course_structure.name if a.course_structure else None,
            'label': a.label,
            'full_marks': a.course_structure.full_marks if a.course_structure else 0,
            'pass_marks': a.course_structure.pass_marks if a.course_structure else 0,
            'ind_marks_obtained': a.ind_marks_obtained,
            'ind_max_marks': a.ind_max_marks,
            'ind_is_absent': a.ind_is_absent,
            'ind_grace_obtained': a.ind_grace_obtained,
            'ind_is_pass': a.ind_is_pass,
            'exam_type': a.exam_type,
            'session': a.exam.session if a.exam else None,
            'subject_result': a.subject_result,
            'grade': a.grade,
        }
    
    def format_exam(exam):
        if not exam:
            return None
        return {
            'uid': str(exam.uid),
            'name': exam.name,
            'session': exam.session,
            'semester': exam.semester,
            'publication_date': str(exam.publication_date) if exam.publication_date else None,
            'exam_month_year': exam.exam_month_year,
        }
    
    results = []
    
    # REGULAR group
    if regular_assessments:
        result_stats = calculate_llb_result(regular_assessments)
        results.append({
            'type': 'regular',
            'session_code': regular_exam.session if regular_exam else None,
            'exam': format_exam(regular_exam),
            'centre': get_center_info_for_student(student, regular_exam),
            'assessments': [format_assessment(a) for a in regular_assessments],
            'result_stats': result_stats,
        })
    
    # BACK groups - one per session
    for session in sorted(back_sessions.keys()):
        back_list = back_sessions[session]
        back_exam = back_list[0].exam if back_list else None
        result_stats = calculate_llb_result(back_list)
        
        results.append({
            'type': 'back',
            'session_code': session,
            'session': session,
            'exam': format_exam(back_exam),
            'centre': get_center_info_for_student(student, back_exam),
            'assessments': [format_assessment(a) for a in back_list],
            'result_stats': result_stats,
        })
    
    return {
        'results': results,
        'available_sessions': sorted(list(all_sessions))
    }


def get_llb_latest_assessments(student, semester, session=None):
    """
    Get the latest consolidated assessments for PDF generation.
    Combines ALL papers (REGULAR + BACK), with the latest session taking
    precedence for duplicate (paper_code, label) pairs.
    
    Similar to get_ug_old_ba_hons_part1_latest_context in ug_before_cbcs.
    
    Args:
        student: LLBStudentProfile instance
        semester: Semester code (e.g., '1ST', '2ND', '3RD')
        session: Optional specific session filter (e.g., '2022-23').
                 If provided, only returns assessments from that session.
                 If None, returns latest consolidated across all sessions.
    
    Returns:
        tuple: (assessments_list, exam) or (None, None) if no data found
    """
    all_assessments = LLBStudentCourseAssessment.objects.filter(
        student=student,
        semester=semester
    ).select_related('exam', 'course_structure').exclude(
        exam__isnull=True
    ).order_by('exam__session', 'paper_code')
    
    if session:
        # Filter to specific session only
        all_assessments = all_assessments.filter(exam__session=session)
    
    if not all_assessments.exists():
        logger.warning(f"No assessments found for {student.registration_no} / {semester}" +
                       (f" / session={session}" if session else ""))
        return None, None
    
    if session:
        # Specific session - return as-is
        assessments_list = list(all_assessments)
        exam = assessments_list[0].exam if assessments_list else None
        return assessments_list, exam
    
    # Latest consolidation: for duplicate (paper_code, label), keep latest session
    latest_papers = {}  # key: (paper_code, label) -> assessment
    latest_exam = None
    
    for assessment in all_assessments:
        key = (assessment.paper_code, assessment.label)
        
        if key in latest_papers:
            existing = latest_papers[key]
            existing_session = existing.exam.session if existing.exam else ''
            current_session = assessment.exam.session if assessment.exam else ''
            
            # Keep the one with the later session
            if current_session > existing_session:
                latest_papers[key] = assessment
                logger.info(
                    f"Override: {assessment.paper_code} {assessment.label} "
                    f"- {existing_session} → {current_session}"
                )
        else:
            latest_papers[key] = assessment
        
        # Track the latest exam (for exam metadata on the PDF)
        if assessment.exam:
            if latest_exam is None:
                latest_exam = assessment.exam
            elif (assessment.exam.session or '') > (latest_exam.session or ''):
                latest_exam = assessment.exam
    
    assessments_list = sorted(
        latest_papers.values(),
        key=lambda a: a.paper_code or ''
    )
    
    return assessments_list, latest_exam


def get_center_info_for_student(student, exam):
    """
    Get the examination center information for a student from LLBExamCenterMapping.
    Works with LLB's M2M mapping structure (exams and attached_colleges).
    
    Args:
        student: LLBStudentProfile instance
        exam: LLBExam instance
    
    Returns:
        dict: Center information with uid, name, etc. or just name string
    """
    from ..models import LLBExamCenterMapping
    
    if not student.college:
        # LLBExam doesn't have centre_name field, return None
        return None
    
    # Find mapping where exam is in the exams M2M and student's college is in attached_colleges
    mapping = LLBExamCenterMapping.objects.filter(
        exams=exam,
        attached_colleges=student.college
    ).select_related('center').first()
    
    if mapping:
        # Priority: center college > exam.centre_name
        if mapping.center:
            return {
                'uid': str(mapping.center.uid),
                'name': mapping.center.name,
                'college_code': mapping.center.college_code,
                'short_name': mapping.center.short_name,
                'address': mapping.center.address,
            }
    
    # LLBExam doesn't have centre_name field, no fallback
    return None
