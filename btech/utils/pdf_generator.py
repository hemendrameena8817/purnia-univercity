def generate_btech_admit_card_pdf(student, exam):
    from weasyprint import HTML, CSS
    import io, base64, os
    from django.conf import settings
    from django.template.loader import get_template
    from btech.models import BTechExamCenterMapping, BTechExamSchedule, BTechExamRegistration
    from pup_umis_backend.utils.file_utils import image_to_base64
    import logging

    logger = logging.getLogger(__name__)

    # Get exam center mapping
    exam_center = None
    if student.college:
        mapping = BTechExamCenterMapping.objects.filter(
            exams=exam,
            attached_colleges=student.college
        ).first()
        if mapping:
            exam_center = mapping.center
    
    # Get the latest exam registration for this student and exam
    registration = BTechExamRegistration.objects.filter(
        student=student,
        exam=exam
    ).order_by('-created_at').first()

    # Get exam schedules
    schedules_query = BTechExamSchedule.objects.filter(
        exam=exam
    ).select_related('common_course_structure')

    if registration and registration.exam_type in ['BACK', 'IMPROVEMENT']:
        # Filter schedules to only include subjects selected for backlog/improvement
        backlog_ids = registration.backlog_subjects.values_list('id', flat=True)
        schedules = schedules_query.filter(common_course_structure_id__in=backlog_ids)
    else:
        # Default behavior: show all schedules for the exam
        schedules = schedules_query


    # Prepare context for template
    context = {
        "exam": exam,
        "student": student,
        "registration": registration,
        "exam_type": registration.exam_type if registration else "REGULAR",
        "center_mapping": mapping,
        "center_name": exam_center.name if exam_center else "-",
        "center_code": exam_center.center_code if exam_center else "-",
        "schedules": schedules,
        "university_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "watermark_logo": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")),
        "student_photo": image_to_base64(student.profile_image.path if student.profile_image else None),
        "student_sig": image_to_base64(student.signature.path if student.signature else None),
        "controller_signature": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
    }

    # Render HTML template
    html_string = get_template("btech/admit_card.html").render(context)

    try:
        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        
        logger.info(f"PDF generated successfully using WeasyPrint, size: {len(pdf_file)} bytes")
        return pdf_file
        
    except Exception as e:
        logger.error(f"PDF generation failed with WeasyPrint: {str(e)}")
        return None

def generate_btech_roll_sheet_pdf(exam, college, branch):
    from weasyprint import HTML
    from django.conf import settings
    from django.template.loader import get_template
    from btech.models import (
        BTechExamRegistration, 
        BTechExamSchedule,
        BTechCommonCourseStructure
    )
    from pup_umis_backend.utils.file_utils import image_to_base64
    import os
    import logging

    logger = logging.getLogger(__name__)

    # 1. Get all students registered for this exam in this college and branch
    registrations = BTechExamRegistration.objects.filter(
        exam=exam,
        student__college=college,
        student__branch=branch
    ).select_related('student', 'student__batch').order_by('student__roll_no', 'student__registration_no')

    if not registrations.exists():
        logger.warning(f"No registrations found for Exam: {exam.name}, College: {college.name}, Branch: {branch.name}")
        return None

    # Get exam center mapping for this college
    from btech.models import BTechExamCenterMapping
    center_name = "-"
    center_mapping = BTechExamCenterMapping.objects.filter(
        exams=exam,
        attached_colleges=college
    ).first()
    if center_mapping and center_mapping.center:
        center_name = center_mapping.center.name

    # 2. Get the subjects (schedules) for this exam and branch
    # Note: BTechExamSchedule points to BTechCommonCourseStructure
    schedules = BTechExamSchedule.objects.filter(
        exam=exam,
        common_course_structure__branch=branch
    ).select_related('common_course_structure').order_by('exam_date', 'exam_time')

    subjects = []
    for s in schedules:
        if s.common_course_structure:
            subjects.append({
                'id': s.common_course_structure.id,
                'code': s.common_course_structure.code,
                'course_name': s.common_course_structure.course_name
            })

    # 3. Prepare student data rows
    student_data = []
    for reg in registrations:
        student = reg.student
        
        # Determine which subjects this student is registered for
        if reg.exam_type == 'REGULAR':
            # Regular students take all subjects scheduled for this branch/exam
            student_subject_ids = [s['id'] for s in subjects]
        else:
            # Backlog/Improvement students take only their specific subjects
            student_subject_ids = list(reg.backlog_subjects.values_list('id', flat=True))
        
        student_data.append({
            'name': student.get_full_name(),
            'roll_no': student.roll_no or "-",
            'registration_no': student.registration_no or "-",
            'subject_ids': student_subject_ids
        })

    # 4. Prepare Context
    context = {
        "exam": exam,
        "college": college,
        "branch": branch,
        "course_name": branch.course.name,
        "branch_name": branch.name or "-",
        "batch_name": exam.batch or "-",
        "session_name": exam.session or "-",
        "college_name": college.name or "-",
        "center_name": center_name or "-",
        "year": f"{exam.year}th" if exam.year else "-", 
        "syllabus": "-",
        "subjects": subjects,
        "student_data": student_data,
        "controller_signature": image_to_base64(os.path.join(settings.MEDIA_ROOT, "common/controller-of-examination-signature.png")),
    }

    # Render HTML template
    html_string = get_template("btech/roll_sheet.html").render(context)

    try:
        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        return pdf_file
    except Exception as e:
        logger.error(f"Roll Sheet PDF generation failed: {str(e)}")
        return None


def generate_btech_attendance_sheet_pdf(exam, college, branch):
    """
    Generate student-wise attendance sheets for BTech students.
    Each student gets their own sheet with their exam schedule.
    """
    from weasyprint import HTML, CSS
    from django.conf import settings
    from django.template.loader import get_template
    from btech.models import (
        BTechExamRegistration, 
        BTechExamSchedule,
        BTechExamCenterMapping
    )
    from pup_umis_backend.utils.file_utils import image_to_base64, generate_barcode_base64
    import os
    import base64
    import logging
    from django.db.models import Q

    logger = logging.getLogger(__name__)

    # Get all students registered for this exam from the specified college and branch
    registrations = BTechExamRegistration.objects.filter(
        exam=exam,
        student__college=college,
        student__branch=branch
    ).select_related('student').order_by('student__roll_no')
    
    if not registrations.exists():
        logger.warning(f"No registrations found for Exam: {exam.name}, "
                     f"College: {college.name}, Branch: {branch.name}")
        return None

    # Get exam center mapping
    exam_center = None
    mapping = BTechExamCenterMapping.objects.filter(
        exams=exam,
        attached_colleges=college
    ).first()
    
    if mapping and hasattr(mapping, 'center'):
        exam_center = mapping.center
    
    # Get university logo
    logo_path = os.path.join(settings.MEDIA_ROOT, "common/purnea-logo.png")
    university_logo = image_to_base64(logo_path) if os.path.exists(logo_path) else None

    # Get exam schedules for this branch
    schedules = BTechExamSchedule.objects.filter(
        exam=exam,
        common_course_structure__branch=branch
    ).select_related('common_course_structure').order_by('exam_date', 'exam_time')
    
    # Prepare attendance data for each student
    attendance_data = []
    for reg in registrations:
        student = reg.student
        
        # Generate barcode for student's registration number
        barcode_text = f"Roll:{student.roll_no or ''}, Reg:{student.registration_no or ''}, Name:{student.get_full_name()}, Branch:{branch.name}"
        barcode_bytes = generate_barcode_base64(barcode_text)
        barcode_base64 = barcode_bytes if barcode_bytes else None
        
        # Get student photo
        photo_base64 = None
        if hasattr(student, 'profile_image') and student.profile_image:
            try:
                photo_base64 = image_to_base64(student.profile_image.path)
            except Exception as e:
                logger.error(f"Error reading photo for {student.registration_no}: {str(e)}")
        
        # Prepare student schedules
        student_schedules = []
        for schedule in schedules:
            # Check if this schedule is relevant for the student's registration
            if reg.exam_type == 'REGULAR' or \
               (hasattr(reg, 'backlog_subjects') and 
                schedule.common_course_structure in reg.backlog_subjects.all()):
                student_schedules.append({
                    'date': schedule.exam_date.strftime('%d-%m-%Y') if schedule.exam_date else 'TBD',
                    'sitting': schedule.sitting,
                    'subject_name': schedule.common_course_structure.course_name if schedule.common_course_structure else 'N/A',
                    'subject_code': schedule.common_course_structure.code if schedule.common_course_structure else 'N/A',
                })
        
        attendance_data.append({
            'name': student.get_full_name() if hasattr(student, 'get_full_name') else student.name,
            'roll_no': student.roll_no or 'N/A',
            'registration_no': student.registration_no or 'N/A',
            'photo': photo_base64,
            'college_name': college.name,
            'barcode': barcode_base64,
            'schedules': student_schedules
        })
    
    # Prepare context for the template
    context = {
        'attendance_data': attendance_data,
        'university_logo': university_logo,
        'exam_header': f"{exam.name}",
        'center_name': f"{exam_center.center_code} - {exam_center.name}" if exam_center else "Not Assigned"
    }
    
    # Render HTML
    html_string = get_template('btech/attendance_sheet.html').render(context)
    
    try:
        # Generate PDF
        html = HTML(string=html_string, base_url=settings.MEDIA_ROOT)
        pdf = html.write_pdf()
        return pdf
    except Exception as e:
        logger.error(f"Attendance Sheet PDF generation failed: {str(e)}")
        return None
