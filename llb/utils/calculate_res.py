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
            'is_pass': bool,
            'ese_full_marks': int,
            'ese_obtained_marks': int,
            'cia_full_marks': int,
            'cia_obtained_marks': int
        }
    """
    total_full_marks = 0
    total_pass_marks = 0
    total_obtained_marks = 0
    failed_subjects = []
    
    # ESE and CIA totals (for 2nd semester)
    ese_full_marks = 0
    ese_obtained_marks = 0
    cia_full_marks = 0
    cia_obtained_marks = 0
    
    for assessment in assessments:
        # Get marks from course structure
        full_marks = assessment.course_structure.full_marks if assessment.course_structure else 0
        pass_marks = assessment.course_structure.pass_marks if assessment.course_structure else 0
        obtained_marks = float(assessment.ind_marks_obtained or 0)
        
        total_full_marks += full_marks
        total_pass_marks += pass_marks
        total_obtained_marks += obtained_marks
        
        # Calculate ESE and CIA totals based on status
        if assessment.course_structure:
            if assessment.course_structure.status == 'ESE':
                ese_full_marks += full_marks
                ese_obtained_marks += int(obtained_marks)
            elif assessment.course_structure.status == 'CIA':
                cia_full_marks += full_marks
                cia_obtained_marks += int(obtained_marks)
        
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
        'total_obtained_marks': int(total_obtained_marks),
        'result_status': result_status,
        'result_display': result_display,
        'percentage': round(percentage, 2),
        'failed_subjects': failed_subjects,
        'is_pass': is_pass,
        'aggregate_pass_marks': aggregate_pass_marks,
        # ESE and CIA totals (for 2nd semester template)
        'ese_full_marks': ese_full_marks,
        'ese_obtained_marks': ese_obtained_marks,
        'cia_full_marks': cia_full_marks,
        'cia_obtained_marks': cia_obtained_marks
    }


def calculate_llb_result_semester_3(assessments):
    result_stats = calculate_llb_result(assessments)

    part_groups = {
        '1': {'full_marks': 0, 'pass_marks': 0, 'obtained_marks': 0},
        '2': {'full_marks': 0, 'pass_marks': 0, 'obtained_marks': 0},
        '3': {'full_marks': 0, 'pass_marks': 0, 'obtained_marks': 0},
    }

    for assessment in assessments:
        course_structure = getattr(assessment, 'course_structure', None)
        if not course_structure:
            continue

        semester = (getattr(assessment, 'semester', '') or '').upper()
        part_key = None
        if semester.startswith('1'):
            part_key = '1'
        elif semester.startswith('2'):
            part_key = '2'
        elif semester.startswith('3'):
            part_key = '3'

        if part_key not in part_groups:
            continue

        part_groups[part_key]['full_marks'] += course_structure.full_marks or 0
        part_groups[part_key]['pass_marks'] += course_structure.pass_marks or 0
        part_groups[part_key]['obtained_marks'] += int(assessment.ind_marks_obtained or 0)

    return {
        **result_stats,
        'part1_full_marks': part_groups['1']['full_marks'],
        'part1_pass_marks': part_groups['1']['pass_marks'],
        'part1_obtained_marks': part_groups['1']['obtained_marks'],
        'part2_full_marks': part_groups['2']['full_marks'],
        'part2_pass_marks': part_groups['2']['pass_marks'],
        'part2_obtained_marks': part_groups['2']['obtained_marks'],
        'part3_full_marks': part_groups['3']['full_marks'],
        'part3_pass_marks': part_groups['3']['pass_marks'],
        'part3_obtained_marks': part_groups['3']['obtained_marks'],
    }
