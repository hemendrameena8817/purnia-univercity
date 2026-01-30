from plw.models import PLWResult

def generate_plw_barcode_text(result: PLWResult):
    student = result.student
    return (
        f"MSNO.: {result.exam.session}-{student.roll_no} | "
        f"Course : {student.course.name} | "
        f"Name : {student.user.get_full_name()} | "
        f"Roll No: {student.roll_no} | "
        f"Registration No. : {student.registration_no} | "
        f"Total Mark : {result.total_marks}"
    )
