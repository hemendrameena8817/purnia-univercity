from llb.models import LLBStudentExamResult

def generate_llb_barcode_text(result: LLBStudentExamResult):
    student = result.student
    return (
        f"MSNO.: {student.roll_no} | "
        f"Course : {student.course.name} | "
        f"Name : {student.user.get_full_name()} | "
        f"Roll No: {student.roll_no} | "
        f"Registration No. : {student.registration_no} | "
        f"Total Mark : {result.total_marks}"
    )
