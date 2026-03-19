from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from colleges.models import College
from .models import BCAHonsExam, BCAHonsStudentProfile, BCAHonsBatch
from bca_hons_year.utils.tr.tr_3rd_year import (
    generate_bca_hons_3rd_year_tr_pdf,
    generate_static_bca_hons_3rd_year_tr_pdf
)

class BCAHons3rdYearStaticTRView(View):
    """
    Returns the BCA Hons 3rd Year TR template as a PDF.
    Supports ?download=false for browser viewing.
    """
    def get(self, request):
        # Generate the static PDF from the Excel template
        pdf_content = generate_static_bca_hons_3rd_year_tr_pdf()

        if not pdf_content:
            return HttpResponse("Failed to generate PDF from template.", status=500, content_type='text/plain')

        # Check if user wants to force download (default: true for TR sheets usually)
        download = request.GET.get('download', 'true').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="BCA_Hons_TR_Template.pdf"'
        
        return response

class BCAHons3rdYearTRView(View):
    """
    Returns the BCA Hons 3rd Year TR as a PDF.
    Dynamic content is generated based on college_uid, batch_uid, and year.
    """
    def get(self, request):
        college_uid = request.GET.get("college_uid")
        batch_uid = request.GET.get("batch_uid")
        year_val = request.GET.get("year", "3") # Expected values might be "1", "2", "3"

        if not college_uid or not batch_uid:
            return HttpResponse(
                "college_uid and batch_uid are required parameters.",
                status=400,
                content_type='text/plain'
            )

        college = get_object_or_404(College, uid=college_uid)
        batch = get_object_or_404(BCAHonsBatch, uid=batch_uid)

        # Filter students belonging to this college and batch
        students = BCAHonsStudentProfile.objects.filter(
            college=college,
            batch=batch
        ).distinct().order_by("roll_no")

        print(f"length of students = {len(students)}")
        
        # Optionally fetch an exam name if available for some context
        exam = BCAHonsExam.objects.filter(year=year_val).last()

        # Construct dynamic exam name
        exam_name = exam.name if exam else f"BCA Hons Part III Examination"
        if exam and exam.exam_month_year:
            exam_name += f", held in the month of {exam.exam_month_year}"

        # Generate the dynamic PDF
        pdf_content = generate_bca_hons_3rd_year_tr_pdf(
            students=students, 
            college=college, 
            batch_uid=batch.uid, 
            year=year_val,
            exam_name=exam_name
        )

        if not pdf_content:
            return HttpResponse(
                f"No data found for College {college.college_code}, Batch {batch.name}, Year {year_val}.",
                status=404, 
                content_type='text/plain'
            )

        # Download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'
        
        safe_college_code = college.college_code if college.college_code else "COL"
        filename = f"BCA_Hons_TR_Year{year_val}_{safe_college_code}.pdf"

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        
        return response

class BCAHonsResultDeclarationPDFView(View):
    """
    Generates a result declaration PDF for BCA Hons showing roll numbers of pass/fail students.
    REQUIRED Query params: college_uid, exam_uid
    """
    def get(self, request):
        from bca_hons_year.utils.pdf_generator import generate_bca_hons_result_declaration_pdf
        from colleges.models import College
        from .models import BCAHonsExam

        college_uid = request.GET.get("college_uid")
        exam_uid = request.GET.get("exam_uid")
        batch_uid = request.GET.get("batch_uid")

        if not college_uid or not exam_uid:
            return HttpResponse("college_uid and exam_uid are required!", status=400)

        college = College.objects.filter(uid=college_uid).last()
        if not college:
            return HttpResponse("Invalid College UID!", status=400)

        exam = BCAHonsExam.objects.filter(uid=exam_uid).last()
        if not exam:
            return HttpResponse("Examination not found!", status=404)

        pdf_content = generate_bca_hons_result_declaration_pdf(
            exam, college, batch_uid=batch_uid
        )

        if not pdf_content:
            return HttpResponse("PDF generation failed or no data found", status=500)

        download = request.GET.get('download', 'true').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        safe_exam_name = "".join(c if c.isalnum() else "_" for c in str(exam.name))
        filename = f"BCA_Hons_Result_Declaration_{college.college_code}_{safe_exam_name}.pdf"

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response
class BCAHonsMarksheetPDFView(View):
    """
    Generates and returns the BCA Hons Marksheet PDF for Part III.
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        roll_no = request.GET.get("roll_no")
        student_uid = request.GET.get("student_uid")
        year = request.GET.get("year", "3")

        if not (registration_no or roll_no or student_uid):
            return HttpResponse("registration_no, roll_no or student_uid is required", status=400)

        if student_uid:
            student = get_object_or_404(BCAHonsStudentProfile, uid=student_uid)
        elif registration_no:
            student = get_object_or_404(BCAHonsStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(BCAHonsStudentProfile, roll_no=roll_no)

        from bca_hons_year.utils.marksheet_generator import generate_bca_hons_marksheet_pdf
        pdf_content = generate_bca_hons_marksheet_pdf(student, exam_val=year)

        if not pdf_content:
            return HttpResponse(f"Marksheet data not found for {student.get_full_name()} (Year {year}).", status=404, content_type='text/plain')

        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'
        
        response = HttpResponse(pdf_content, content_type="application/pdf")
        filename = f"BCA_Hons_Marksheet_{student.registration_no}_Year{year}.pdf"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response

class BCAHonsMarksheetJSONView(View):
    """
    Returns the BCA Hons Marksheet context data in JSON format.
    """
    def get(self, request):
        from django.http import JsonResponse
        registration_no = request.GET.get("registration_no")
        roll_no = request.GET.get("roll_no")
        student_uid = request.GET.get("student_uid")
        year = request.GET.get("year", "3")

        if not (registration_no or roll_no or student_uid):
            return JsonResponse({"error": "registration_no, roll_no or student_uid is required"}, status=400)

        if student_uid:
            student = get_object_or_404(BCAHonsStudentProfile, uid=student_uid)
        elif registration_no:
            student = get_object_or_404(BCAHonsStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(BCAHonsStudentProfile, roll_no=roll_no)

        from bca_hons_year.utils.marksheet_generator import get_bca_hons_marksheet_context
        context = get_bca_hons_marksheet_context(student, exam_val=year)

        # Clean-up non-serializable objects
        if 'student' in context:
            stud = context['student']
            context['student'] = {
                'registration_no': stud.registration_no,
                'roll_no': stud.roll_no,
                'name': stud.get_full_name(),
                'college': stud.college.name if stud.college else "N/A"
            }
        context.pop('qr_code', None)
        context.pop('university_logo', None)
        context.pop('controller_signature', None)
        
        return JsonResponse(context)
