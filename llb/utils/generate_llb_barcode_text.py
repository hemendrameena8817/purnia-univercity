from llb.utils.calculate_res import calculate_llb_result

def generate_llb_barcode_text(result=None, semester=None, student=None, exam=None, assessments=None, total_marks=None):
    student = student or getattr(result, 'student', None)
    exam = exam or getattr(result, 'exam', None)
    if assessments is None:
        if result is not None and hasattr(result, '_filtered_assessments'):
            assessments = result._filtered_assessments
        elif student is not None and exam is not None:
            if semester:
                assessments = student.course_assessments.filter(exam=exam, semester=semester)
            else:
                assessments = student.course_assessments.filter(exam=exam)
        else:
            assessments = []
    result_data = calculate_llb_result(assessments)
    marks_obtained = result_data['total_obtained_marks']
    total_marks = total_marks if total_marks is not None else getattr(result, 'total_marks', result_data['total_full_marks'])

    return (
        f"MSNO.: {getattr(exam, 'session', '')}-{student.roll_no} | "
        f"Course : {student.course.name} | "
        f"Name : {student.user.get_full_name()} | "
        f"Roll No: {student.roll_no} | "
        f"Registration No. : {student.registration_no} | "
        f"Total Mark : {total_marks} | "
        f"Marks Obtained : {marks_obtained}"
    )
