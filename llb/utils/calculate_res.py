def calculate_llb_result(assessments):
    """
    Calculate LLB result based on assessments.
    
    Args:
        assessments: QuerySet or list of LLBStudentCourseAssessment objects
    
    Returns:
        dict: {
            'total_full_marks': int,
            'total_pass_marks': float,
            'total_obtained_marks': float,
            'result_status': str (PASS/FAIL),
            'percentage': float,
            'division': str,
            'failed_subjects': list,
            'is_pass': bool
        }
    """
    total_full_marks = 0
    total_pass_marks = 0
    total_obtained_marks = 0
    failed_subjects = []
    
    for assessment in assessments:
        # Get marks from course structure
        full_marks = assessment.course_structure.full_marks if assessment.course_structure else 0
        pass_marks = assessment.course_structure.pass_marks if assessment.course_structure else 0
        obtained_marks = float(assessment.ind_marks_obtained or 0)
        
        total_full_marks += full_marks
        total_pass_marks += pass_marks
        total_obtained_marks += obtained_marks
        
        # Check if student failed in this subject (less than 33% in each paper)
        if full_marks > 0:
            subject_pass_marks = pass_marks if pass_marks else (full_marks * 0.33)
            if obtained_marks < subject_pass_marks or assessment.ind_is_absent:
                failed_subjects.append({
                    'name': assessment.course_structure.name if assessment.course_structure else 'Unknown',
                    'paper_code': assessment.paper_code,
                    'obtained': obtained_marks,
                    'required': subject_pass_marks
                })
    
    # Calculate percentage
    percentage = (total_obtained_marks / total_full_marks * 100) if total_full_marks > 0 else 0
    
    # Calculate aggregate pass marks (45% of total)
    aggregate_pass_marks = total_full_marks * 0.45
    
    # Determine result status
    # Pass conditions:
    # 1. Must score 33% in each paper
    # 2. Must score 45% in aggregate
    is_pass = len(failed_subjects) == 0 and total_obtained_marks >= aggregate_pass_marks
    result_status = 'PASS' if is_pass else 'FAIL'
    
    # Determine result display
    # If 1st class (>=65%), show "1ST CLASS"
    # Otherwise, just show "PASS" or "FAIL"
    if is_pass:
        if percentage >= 65:
            result_display = '1ST CLASS'
        else:
            result_display = 'PASS'
    else:
        result_display = 'FAIL'
    
    return {
        'total_full_marks': total_full_marks,
        'total_pass_marks': total_pass_marks,
        'total_obtained_marks': round(total_obtained_marks, 2),
        'result_status': result_status,
        'result_display': result_display,
        'percentage': round(percentage, 2),
        'failed_subjects': failed_subjects,
        'is_pass': is_pass,
        'aggregate_pass_marks': aggregate_pass_marks
    }
