from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from colleges.models import College
from .models import BBAExam, BBAStudentProfile, BBABatch
from bba_year.utils.tr.tr_3rd_year import generate_bba_3rd_year_tr_pdf

class BBA3rdYearTRView(View):
    """
    Returns the BBA 3rd Year TR as a PDF.
    Dynamic content is generated based on college_uid, batch_uid, and year.
    """
    def get(self, request):
        college_uid = request.GET.get(  "college_uid")
        batch_uid = request.GET.get("batch_uid")
        year_val = request.GET.get("year", "3") # Expected values might be "1", "2", "3"

        if not college_uid or not batch_uid:
            return HttpResponse(
                "college_uid and batch_uid are required parameters.",
                status=400,
                content_type='text/plain'
            )

        college = get_object_or_404(College, uid=college_uid)
        batch = get_object_or_404(BBABatch, uid=batch_uid)

        # Filter students belonging to this college and batch
        students = BBAStudentProfile.objects.filter(
            college=college,
            batch=batch
        ).distinct().order_by("roll_no")
        print(f"{students = }")

        # Optionally fetch an exam name if available for some context
        exam = BBAExam.objects.filter(year=year_val).last()

        # Construct dynamic exam name: (Exam Name) Batch: XXX
        base_name = exam.name if exam else f"BBA Part III Examination"
        exam_name = f"{base_name}"
        if exam and exam.exam_month_year:
            exam_name += f", held in the month of {exam.exam_month_year}"

        # Generate the dynamic PDF (restricted to columns A-M)
        pdf_content = generate_bba_3rd_year_tr_pdf(
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
        filename = f"BBA_TR_Year{year_val}_{safe_college_code}.pdf"

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        
        return response

class BBAResultDeclarationPDFView(View):
    """
    Generates a result declaration PDF for BBA showing roll numbers of pass/fail students.
    REQUIRED Query params: college_uid, exam_uid
    """
    def get(self, request):
        from bba_year.utils.pdf_generator import generate_bba_result_declaration_pdf
        from colleges.models import College
        from .models import BBAExam

        college_uid = request.GET.get("college_uid")
        exam_uid = request.GET.get("exam_uid")
        batch_uid = request.GET.get("batch_uid")

        if not college_uid or not exam_uid:
            return HttpResponse("college_uid and exam_uid are required!", status=400)

        college = College.objects.filter(uid=college_uid).last()
        if not college:
            return HttpResponse("Invalid College UID!", status=400)

        exam = BBAExam.objects.filter(uid=exam_uid).last()
        if not exam:
            return HttpResponse("Examination not found!", status=404)

        pdf_content = generate_bba_result_declaration_pdf(
            exam, college, batch_uid=batch_uid
        )

        if not pdf_content:
            return HttpResponse("PDF generation failed or no data found", status=500)

        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        safe_exam_name = "".join(c if c.isalnum() else "_" for c in str(exam.name))
        filename = f"BBA_Result_Declaration_{college.college_code}_{safe_exam_name}.pdf"

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response


class BBAMarksheetPDFView(View):
    """
    Generates and returns the BBA Marksheet PDF for Part III (includes Part I & II).
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        roll_no = request.GET.get("roll_no")
        student_uid = request.GET.get("student_uid")
        year = request.GET.get("year", "3")

        if not (registration_no or roll_no or student_uid):
            return HttpResponse("registration_no, roll_no or student_uid is required", status=400)

        if student_uid:
            student = get_object_or_404(BBAStudentProfile, uid=student_uid)
        elif registration_no:
            student = get_object_or_404(BBAStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(BBAStudentProfile, roll_no=roll_no)

        from bba_year.utils.marksheet_generator import generate_bba_marksheet_pdf
        pdf_content = generate_bba_marksheet_pdf(student, exam_val=year)

        if not pdf_content:
            return HttpResponse(f"Marksheet data not found for {student.get_full_name()} (Year {year}).", status=404, content_type='text/plain')

        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'
        
        response = HttpResponse(pdf_content, content_type="application/pdf")
        filename = f"BBA_Marksheet_{student.registration_no}_Year{year}.pdf"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response

class BBAMarksheetJSONView(View):
    """
    Returns the BBA Marksheet context data in JSON format.
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
            student = get_object_or_404(BBAStudentProfile, uid=student_uid)
        elif registration_no:
            student = get_object_or_404(BBAStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(BBAStudentProfile, roll_no=roll_no)

        from bba_year.utils.marksheet_generator import get_bba_marksheet_context
        context = get_bba_marksheet_context(student, exam_val=year)

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
