import qrcode
import io
import base64


def generate_qr_code_base64(data_text):
    """
    Generate a QR code from text and return as base64 encoded string.
    
    Args:
        data_text (str): Text data to encode in QR code
        
    Returns:
        str: Base64 encoded PNG image of QR code
    """
    if not data_text:
        return ""
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add data and generate
    qr.add_data(data_text)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return qr_code_base64


def generate_ug_marksheet_qr_text(student, exam, grand_total):
    """
    Generate QR code text for UG Before CBCS marksheet.
    
    Args:
        student: UGBeforeCBCSStudentProfile instance
        exam: UGBeforeCBCSExam instance
        grand_total: Total marks obtained
        
    Returns:
        str: Formatted text for QR code
    """
    return (
        f"MSNO.: {exam.exam_year or 'N/A'}-{student.roll_no} | "
        f"Roll No: {student.roll_no} | "
        f"Registration No.: {student.registration_no} | "
        f"Name: {student.student_name} | "
        f"Exam: {exam.name} | "
        f"Total Marks: {grand_total}"
    )
