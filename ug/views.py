from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.template.loader import render_to_string
from io import BytesIO
from weasyprint import HTML
from .models import UGStudentProfile, UGExam
from .utils.admit_card_pdf import generate_ug_admit_card_pdf
import os
import base64
from django.conf import settings

class UGAdmitCardPDFView(View):
    """
    Generates and returns admit card PDF for a single UG student.
    Query params: registration_no, exam_uid
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        exam_uid = request.GET.get("exam_uid")

        if not registration_no or not exam_uid:
            return HttpResponse("Registration number and Exam UID are required", status=400)

        student = get_object_or_404(UGStudentProfile, registration_no=registration_no)
        exam = get_object_or_404(UGExam, uid=exam_uid)

        pdf_content = generate_ug_admit_card_pdf(student, exam)

        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500)

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="admit_card_{registration_no}.pdf"'
        return response

class UGBulkAdmitCardPDFView(APIView):
    """
    Bulk Admit Card PDF Generator for UG Students.
    Similar to MBA Bulk view.
    Query Params:
        exam_uid (required)
        registration_nos (required, comma separated)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        exam_uid = request.GET.get("exam_uid", "").strip()
        reg_nos = request.GET.get("registration_nos", "").strip()

        if not exam_uid or not reg_nos:
            return Response({"error": "exam_uid and registration_nos are required"}, status=status.HTTP_400_BAD_REQUEST)

        exam = get_object_or_404(UGExam, uid=exam_uid)
        reg_no_list = [r.strip() for r in reg_nos.split(",") if r.strip()]

        if not reg_no_list:
            return Response({"error": "No valid registration numbers provided"}, status=status.HTTP_400_BAD_REQUEST)

        students = UGStudentProfile.objects.filter(registration_no__in=reg_no_list, is_active=True)

        if not students.exists():
            return Response({"error": "No students found for given registration numbers"}, status=status.HTTP_404_NOT_FOUND)

        # Create Directory for saving (Optional, based on MBA logic)
        safe_exam_name = "".join(c if c.isalnum() else "_" for c in str(exam.name))
        save_dir = os.path.join(settings.MEDIA_ROOT, "ug_students", "admit_cards", f"{safe_exam_name}_{str(exam_uid)[:8]}")
        os.makedirs(save_dir, exist_ok=True)

        results = []
        for student in students:
            try:
                pdf_content = generate_ug_admit_card_pdf(student, exam)
                if pdf_content:
                    file_name = f"admit_card_{student.registration_no}.pdf"
                    file_path = os.path.join(save_dir, file_name)
                    with open(file_path, "wb") as f:
                        f.write(pdf_content)
                    
                    relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    results.append({
                        "registration_no": student.registration_no,
                        "status": "success",
                        "url": f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                    })
                else:
                    results.append({"registration_no": student.registration_no, "status": "failed", "error": "PDF generation failed"})
            except Exception as e:
                results.append({"registration_no": student.registration_no, "status": "error", "error": str(e)})



from django.template.loader import render_to_string
from io import BytesIO
from weasyprint import HTML

class UGAdmitCardTestView(View):
    """
    Test view with static data to see the Admit Card PDF design.
    """
    def get(self, request):
        # Prepare Base64 Images for Test
        base_static_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images')
        logo_path = os.path.join(base_static_path, 'purnea-logo.png')
        university_logo_b64 = ""
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                university_logo_b64 = base64.b64encode(f.read()).decode('utf-8')

        controller_sig_path = os.path.join(base_static_path, 'controller-of-examination-signature.png')
        controller_sig_b64 = ""
        if os.path.exists(controller_sig_path):
            with open(controller_sig_path, 'rb') as f:
                controller_sig_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Static mock data - MIRROR MCA CONTEXT
        data = {
            'exam': {'name': "UG SEMESTER-I EXAMINATION 2024"},
            'student': {
                'roll_no': "210351234001",
                'registration_no': "211511200100",
                'full_name': "SUMIT KUMAR",
                'father_name': "PANKAJ KUMAR",
                'mother_name': "REKHA DEVI",
                'gender': "MALE",
                'college_name': "PURNEA COLLEGE, PURNIA",
            },
            'status': 'REGULAR',
            'center_code': "1203",
            'center_name': "K.B. JHA COLLEGE, KATIHAR (CENTRE)",
            'student_photo': "", # Keep empty for test if no dummy available
            'student_sig': "",
            'university_logo': university_logo_b64,
            'watermark_logo': university_logo_b64,
            'controller_signature': controller_sig_b64,
            'schedules': [
                {'code': 'MJC-1', 'name': 'PROBLEM SOLVING USING C', 'exam_date': '2024-12-10', 'exam_time': '10:00 AM - 01:00 PM', 'sitting': '1ST SITTING'},
                {'code': 'MIC-1', 'name': 'CALCULUS', 'exam_date': '2024-12-15', 'exam_time': '10:00 AM - 01:00 PM', 'sitting': '1ST SITTING'}
            ]
        }
        
        # Render HTML
        html_string = render_to_string('ug/admit_card.html', data)
        
        # Generate PDF
        buffer = BytesIO()
        HTML(string=html_string).write_pdf(target=buffer)
        
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="test_admit_card.pdf"'
        return response

class UGRollSheetPDFView(View):
    """
    Generates and returns Exam Roll Sheet PDF for UG.
    Query params: exam_uid, college_uid
    """
    def get(self, request):
        from colleges.models import College
        from .models import UGExam
        from .utils.roll_sheet_pdf import generate_ug_roll_sheet_pdf

        exam_uid = request.GET.get("exam_uid")
        college_uid = request.GET.get("college_uid")

        if not all([exam_uid, college_uid]):
            return HttpResponse(
                "exam_uid and college_uid are required",
                status=400,
                content_type="text/plain"
            )

        exam = get_object_or_404(UGExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)

        pdf_content = generate_ug_roll_sheet_pdf(
            exam=exam,
            college=college
        )

        if not pdf_content:
            return HttpResponse(
                f"Failed to generate Roll Sheet for {college.name}. "
                f"Ensure students are registered for this exam.",
                status=404,
                content_type="text/plain"
            )

        # inline / download
        download = request.GET.get("download", "false").lower() == "true"
        disposition = "attachment" if download else "inline"

        response = HttpResponse(pdf_content, content_type="application/pdf")

        safe_college_name = "".join(c if c.isalnum() else "_" for c in college.name)

        response["Content-Disposition"] = (
            f'{disposition}; '
            f'filename="UG_Roll_Sheet_{safe_college_name}_'
            f'{exam.semester}_{exam.session}.pdf"'
        )

        return response


class UGExamListView(APIView):
    """
    List UG Exams (active only) with optional filters: 
    - name (string)
    - semester (string)
    - session (string)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from .base_serializers import UGExamSerializer
        
        exam_uid = request.query_params.get('uid')
        if exam_uid:
            exam = get_object_or_404(UGExam, uid=exam_uid, is_active=True)
            serializer = UGExamSerializer(exam)
            return Response(serializer.data)

        # Only active exams
        queryset = UGExam.objects.filter(is_active=True)

        # Filters
        name = request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        semester = request.query_params.get('semester')
        if semester:
            queryset = queryset.filter(semester__icontains=semester)

        session = request.query_params.get('session')
        if session:
            queryset = queryset.filter(session__icontains=session)

        # Order by most recent
        queryset = queryset.order_by('-created_at')

        serializer = UGExamSerializer(queryset, many=True)
        return Response(serializer.data)

