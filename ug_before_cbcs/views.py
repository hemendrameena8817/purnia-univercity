from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from accounts.permissions import IsUniversityAdmin
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from weasyprint import HTML
import os

from .models import (
    UGBeforeCBCSStudentProfile,
    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult,
    UGBeforeCBCSStatistics,
)
from django.db import models
from django.db.models import Count, F
from .serializers import (
    UGBeforeCBCSStudentProfileSerializer,
    UGBeforeCBCSExamSerializer,
    UGBeforeCBCSStudentResultSerializer,
    MarksheetDataSerializer
)
from .utils.pdf_generator import get_ug_old_ba_hons_part1_latest_context
from .utils.validation import validate_marksheet_context

class BaseUGLV(APIView):
    model = None
    serializer_class = None
    def get(self, request):
        queryset = self.model.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BaseUGDV(APIView):
    model = None
    serializer_class = None
    def get_object(self, uid):
        return get_object_or_404(self.model, uid=uid)
    def get(self, request, uid):
        obj = self.get_object(uid)
        serializer = self.serializer_class(obj)
        return Response(serializer.data)
    def put(self, request, uid):
        obj = self.get_object(uid)
        serializer = self.serializer_class(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, uid):
        obj = self.get_object(uid)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




class StudentProfileLV(APIView):
    def get(self, request):
        queryset = UGBeforeCBCSStudentProfile.objects.all()
        reg_no = request.query_params.get('registration_no')
        roll_no = request.query_params.get('roll_no')
        if reg_no: queryset = queryset.filter(registration_no=reg_no)
        if roll_no: queryset = queryset.filter(roll_no=roll_no)
        serializer = UGBeforeCBCSStudentProfileSerializer(queryset, many=True)
        return Response(serializer.data)

class StudentProfileDV(BaseUGDV): 
    model = UGBeforeCBCSStudentProfile
    serializer_class = UGBeforeCBCSStudentProfileSerializer

class ExamLV(BaseUGLV): 
    model = UGBeforeCBCSExam
    serializer_class = UGBeforeCBCSExamSerializer

class ExamDV(BaseUGDV): 
    model = UGBeforeCBCSExam
    serializer_class = UGBeforeCBCSExamSerializer

class StudentResultLV(BaseUGLV): 
    model = UGBeforeCBCSStudentResult
    serializer_class = UGBeforeCBCSStudentResultSerializer


class BatchOptionLV(APIView):
    """
    Returns a unique list of sessions/batches from UGBeforeCBCSExam.
    Format: [{"uid": "...", "name": "2022-25"}, ...]
    """
    permission_classes = [AllowAny]
    def get(self, request):
        course_code = request.query_params.get("course_code")
        
        queryset = UGBeforeCBCSExam.objects.all()
        if course_code:
            queryset = queryset.filter(course_code__iexact=course_code)
            
        # Get unique session codes
        # We use session_code for the 'name' (e.g., 2022-25)
        exams = queryset.exclude(session_code__isnull=True).exclude(session_code='').values('uid', 'session_code').order_by('-session_code')
        
        # Filter for distinct session names, keeping the first UID found for each
        seen_sessions = set()
        unique_batches = []
        for item in exams:
            session_name = item['session_code']
            if session_name not in seen_sessions:
                unique_batches.append({
                    "uid": item['uid'],
                    "name": session_name
                })
                seen_sessions.add(session_name)
                
        return Response(unique_batches)


# Marksheet PDF View 
@method_decorator(csrf_exempt, name='dispatch')
class UGOldMarksheetPDFView(View):
    """
    Generates and returns the Marksheet PDF for Part I, II, or III.
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        roll_no = request.GET.get("roll_no")
        part = request.GET.get("part")
        course_code = request.GET.get("course_code")
        batch_code = request.GET.get("batch_code")
        session_code = request.GET.get("session_code")

        # Validation
        if not (registration_no or roll_no) or not part or not course_code:
            return HttpResponse("registration_no/roll_no, part, and course_code are required", status=400)
 
        if registration_no:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, roll_no=roll_no)
        
        # Check if it's BA Hons Part 1 or 2 by looking at their results
        # (BA students with HON/HONS papers)
        from .models import UGBeforeCBCSStudentResult
        
        has_honours_papers = UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam__part=f"PART{part}",
            paper_type_code__iexact='HON'
        ).exists() or UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam__part=f"PART{part}",
            paper_type_code__iexact='HONS'
        ).exists()

        is_ug_old_hons_part_1_or_2 = (
            (str(part) == '1' or str(part) == '2') and 
            has_honours_papers
        )

        if not is_ug_old_hons_part_1_or_2:
             return HttpResponse("Invalid course_code or part", status=400)

        # Call the appropriate PDF generator
        # Always use the latest context with session_code support
        
        # Get latest consolidated context (or specific session if session_code provided)
        context = get_ug_old_ba_hons_part1_latest_context(
            student, exam_part=part, course_code=course_code, session_code=session_code
        )
        
        if not context:
            return HttpResponse(f"Marksheet data not found for {student.student_name} ({part}).", status=404, content_type='text/plain')
        
        # Validate before generating PDF
        is_valid, error_messages = validate_marksheet_context(student, part, context, course_code, batch_code, session_code)
        if not is_valid:
            error_detail = "; ".join(error_messages)
            return HttpResponse(error_detail, status=422, content_type='text/plain')
        
        # Generate PDF
        template_name = f"ug_before_cbcs/ba_hons_marksheet_part1.html"
        html_string = get_template(template_name).render(context)
        
        try:
            pdf_content = HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf()
        except Exception as e:
            return HttpResponse(f"PDF generation error: {str(e)}", status=500, content_type='text/plain')

        response = HttpResponse(pdf_content, content_type="application/pdf")
        filename = f"Marksheet_{student.registration_no}_{part}.pdf"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


@method_decorator(csrf_exempt, name='dispatch')
class UGOldMarksheetJSONView(APIView):
    """
    Returns the Marksheet data in JSON format for Part I, II, or III.
    """
    permission_classes = [IsUniversityAdmin]
    
    def get(self, request):
        registration_no = request.query_params.get("registration_no")
        roll_no = request.query_params.get("roll_no")
        part = request.query_params.get("part")
        course_code = request.query_params.get("course_code")
        batch_code = request.query_params.get("batch_code")
        session_code = request.query_params.get("session_code")

        # Validation
        if not (registration_no or roll_no) or not part or not course_code:
            return Response(
                {"error": "registration_no/roll_no, part, and course_code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
 
        if registration_no:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, roll_no=roll_no)
        
        # Check if it's BA Hons Part 1 or 2 by looking at their results
        # (BA students with HON/HONS papers)
        from .models import UGBeforeCBCSStudentResult
        
        has_honours_papers = UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam__part=f"PART{part}",
            paper_type_code__iexact='HON'
        ).exists()

        if not has_honours_papers:
            return Response(
                {"error": "Invalid course_code or part"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get marksheet context data
        # Always use the latest context with session_code support
        context_data = get_ug_old_ba_hons_part1_latest_context(
            student, exam_part=part, course_code=course_code, session_code=session_code
        )
        
        if not context_data:
            return Response(
                {"error": f"Marksheet data not found for {student.student_name} ({part})."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize the student object to make it JSON-serializable
        if 'student' in context_data:
            student_obj = context_data['student']
            context_data['student'] = {
                'uid': student_obj.uid,
                'registration_no': student_obj.registration_no,
                'roll_no': student_obj.roll_no,
                'student_name': student_obj.student_name,
                'student_name_hindi': student_obj.student_name_hindi,
                'fathers_name': student_obj.fathers_name,
                'mothers_name': student_obj.mothers_name,
                'gender': student_obj.gender,
                'dob': student_obj.dob,
                'course_code': course_code,
                'discipline_code': student_obj.discipline_code,
                'college_name': student_obj.college.name if student_obj.college else None,
            }
        
        # Add metadata fields
        context_data['part'] = part
        context_data['session_code'] = session_code
        
        # Remove non-serializable items (base64 images, QR codes)
        context_data.pop('university_logo', None)
        context_data.pop('watermark_logo', None)
        context_data.pop('controller_signature', None)
        context_data.pop('qr_code', None)

        # Use serializer to validate and serialize the data
        serializer = MarksheetDataSerializer(data=context_data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # If serializer validation fails, return raw data (fallback)
            return Response(context_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class UGOldMarksheetProgressiveView(APIView):
    """
    Returns year-by-year progressive marksheet data for BACK papers.
    Shows how BACK papers progressively override REGULAR papers over the years.
    """
    permission_classes = [IsUniversityAdmin]
    
    def get(self, request):
        registration_no = request.query_params.get("registration_no")
        roll_no = request.query_params.get("roll_no")
        part = request.query_params.get("part")
        course_code = request.query_params.get("course_code")
        batch_code = request.query_params.get("batch_code")

        if not (registration_no or roll_no) or not part or not course_code:
            return Response(
                {"error": "registration_no/roll_no, part, and course_code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
 
        if registration_no:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, roll_no=roll_no)
        
        from .utils.pdf_generator import get_ug_old_ba_hons_part1_progressive_contexts
        
        # Get progressive contexts
        progressive_data = get_ug_old_ba_hons_part1_progressive_contexts(
            student, exam_part=part, course_code=course_code, batch_code=batch_code
        )
        
        if not progressive_data or not progressive_data.get('results'):
            return Response(
                {"error": f"No marksheet data found for {student.student_name} (Part {part})."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Add student info
        response_data = {
            'student': {
                'uid': str(student.uid),
                'registration_no': student.registration_no,
                'roll_no': student.roll_no,
                'student_name': student.student_name,
                'fathers_name': student.fathers_name,
                'mothers_name': student.mothers_name,
                'college_name': student.college.name if student.college else None,
                'course_code': course_code,
            },
            'part': part,
            'available_sessions': progressive_data.get('available_sessions', []),
            'results': progressive_data.get('results', [])
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class UGOldMarksheetUpdateView(APIView):
    """
    Updates Marksheet data (Exam details and Student marks).
    Restricted to University Admins.
    """
    permission_classes = [IsUniversityAdmin]

    def post(self, request):
        registration_no = request.data.get("registration_no")
        roll_no = request.data.get("roll_no")
        part = request.data.get("part")
        
        if not (registration_no or roll_no) or not part:
            return Response(
                {"error": "registration_no/roll_no and part are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        part_code = f"PART{part}"
        if registration_no:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, roll_no=roll_no)
        
        # Get the results to identify the exam
        results = UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam__part=part_code
        )
        
        exam_type = request.data.get("exam_type")
        session_code = request.data.get("session_code")
        
        if exam_type:
            results = results.filter(exam_type__iexact=exam_type)
        if session_code:
            results = results.filter(exam__session_code=session_code)
            
        first_result = results.select_related('exam').first()
        if not first_result:
            return Response({"error": "No marksheet data found"}, status=status.HTTP_404_NOT_FOUND)
            
        exam = first_result.exam
        
        # Update Exam details (if provided)
        exam_name = request.data.get("exam_name")
        exam_month_year = request.data.get("exam_month_year")
        publication_date = request.data.get("publication_date")
        centre_name = request.data.get("center_name") or request.data.get("centre_name")
        exam_year = request.data.get("exam_year")
        
        if exam_name:
            exam.name = exam_name
        if exam_month_year:
            exam.exam_month_year = exam_month_year
        if publication_date:
            exam.publication_date = publication_date
        if exam_year:
            exam.exam_year = exam_year            
        if exam_name or exam_month_year or publication_date or exam_year:
            exam.save()
            
        # Update Center Name (Using the new mapping approach)
        center_college_uid = request.data.get("center_college_uid")
        
        if centre_name or center_college_uid:
            from .models import UGBeforeCBCSExamCenterMapping
            from colleges.models import College
            
            defaults = {}
            if centre_name:
                defaults['center_name'] = centre_name
            
            if center_college_uid:
                try:
                    center_col = College.objects.get(uid=center_college_uid)
                    defaults['center_college'] = center_col
                    # If we have a formal college, sync its name as backup
                    defaults['center_name'] = center_col.name
                except College.DoesNotExist:
                    pass

            # Update for ALL students of THIS college in THIS exam
            UGBeforeCBCSExamCenterMapping.objects.update_or_create(
                exam=exam,
                student_college=student.college,
                defaults=defaults
            )
            
        # Update Student details (if provided)
        student_name = request.data.get("student_name")
        father_name = request.data.get("fathers_name") 
        mother_name = request.data.get("mothers_name")
        
        student_updated = False
        if student_name: 
            student.student_name = student_name
            student_updated = True
        if father_name: 
            student.fathers_name = father_name
            student_updated = True
        if mother_name: 
            student.mothers_name = mother_name
            student_updated = True
        
        if student_updated:
            student.save()
            
        # Update Marks
        marks_data = request.data.get("marks", [])
        for mark_item in marks_data:
            res_uid = mark_item.get("uid")
            paper_code = mark_item.get("paper_code")
            status_field = mark_item.get("status")
            obtained = mark_item.get("obtained")
            
            res_obj = None
            if res_uid:
                res_obj = results.filter(uid=res_uid).first()
            elif paper_code:
                # Match by both paper_code and status to get the correct paper
                if status_field:
                    res_obj = results.filter(paper_code=paper_code, status=status_field).first()
                else:
                    res_obj = results.filter(paper_code=paper_code).first()

            if res_obj:
                if obtained is not None:
                    # Validation: obtained <= maximum_mark
                    try:
                        # Convert to float for comparison, handle digits or decimal strings
                        max_mark_str = str(res_obj.maximum_mark)
                        obt_str = str(obtained)
                        
                        # Only validate numerically if both can be converted
                        if obt_str.replace('.', '', 1).isdigit() and max_mark_str.replace('.', '', 1).isdigit():
                            obt_val = float(obt_str)
                            max_mark_val = float(max_mark_str)
                            
                            if obt_val > max_mark_val:
                                return Response(
                                    {"error": f"Mark {obt_val} for {res_obj.paper_code} exceeds maximum mark {max_mark_val}"},
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                    except (ValueError, TypeError):
                        # If conversion fails (e.g. 'ABS'), skip numerical validation
                        pass
                    
                    res_obj.mark_secured = obtained
                    
                if "status" in mark_item: 
                    res_obj.status = mark_item["status"]
                if "subject_name" in mark_item: 
                    res_obj.subject_name = mark_item["subject_name"]
                res_obj.save()
                
        # Update Summary fields (final_result, total_secured_mark)
        # These fields are denormalized on ALL StudentResult records for that student/exam
        final_result = request.data.get("final_result")
        total_secured_mark = request.data.get("total_secured_mark")
        agreegate = request.data.get("agreegate")
        
        if final_result or total_secured_mark or agreegate:
            update_fields = {}
            if final_result: update_fields["final_result"] = final_result
            if total_secured_mark: update_fields["total_secured_mark"] = total_secured_mark
            if agreegate: update_fields["agreegate"] = agreegate
            
            UGBeforeCBCSStudentResult.objects.filter(student=student, exam=exam).update(**update_fields)

        return Response({"message": "Marksheet updated successfully"}, status=status.HTTP_200_OK)

class UGBeforeCBCSOverviewView(APIView):
    """
    Returns pre-calculated statistical overview of UG Before CBCS data.
    This is very lightweight as it reads from a cache model.
    """
    permission_classes = [IsUniversityAdmin]

    def get(self, request):
        stats_obj = UGBeforeCBCSStatistics.objects.order_by('-last_updated').first()
        if not stats_obj:
            return Response(
                {"error": "Statistics not yet calculated. Please hit the refresh endpoint."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(stats_obj.data)

from .utils.stats import calculate_and_save_ug_before_cbcs_stats

class UGBeforeCBCSOverviewRefreshView(APIView):
    """
    Heavy API that recalculates all statistics and saves them to the cache model.
    Restricted to University Admins.
    """
    permission_classes = [IsUniversityAdmin]

    def post(self, request):
        stats_obj = calculate_and_save_ug_before_cbcs_stats()
        return Response(stats_obj.data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class UGOldResultCreateView(APIView):
    """
    Create individual paper/result entry for a student.
    Allows adding subject-wise entries one at a time.
    """
    permission_classes = [IsUniversityAdmin]
    
    def post(self, request):
        # Required fields
        registration_no = request.data.get("registration_no")
        roll_no = request.data.get("roll_no")
        exam_code = request.data.get("exam_code")
        paper_code = request.data.get("paper_code")
        subject_name = request.data.get("subject_name")
        
        # Validate required fields
        if not (registration_no or roll_no):
            return Response(
                {"error": "registration_no or roll_no is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not exam_code:
            return Response(
                {"error": "exam_code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not paper_code:
            return Response(
                {"error": "paper_code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get student
        if registration_no:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(UGBeforeCBCSStudentProfile, roll_no=roll_no)
        
        # Get exam
        exam = get_object_or_404(UGBeforeCBCSExam, exam_code=exam_code)
        
        # Optional fields
        status_field = request.data.get("status", "END_TERM")
        exam_type = request.data.get("exam_type", "REGULAR")
        paper_type_code = request.data.get("paper_type_code")
        
        # Marks fields
        theory = request.data.get("theory")
        practical = request.data.get("practical")
        sessional = request.data.get("sessional")
        mark_secured = request.data.get("mark_secured")
        maximum_mark = request.data.get("maximum_mark", "100")
        pass_mark = request.data.get("pass_mark", "33")
        
        # Check for duplicate entry
        existing = UGBeforeCBCSStudentResult.objects.filter(
            student=student,
            exam=exam,
            paper_code=paper_code,
            status=status_field
        ).first()
        
        if existing:
            return Response(
                {
                    "error": "Result entry already exists for this student, exam, paper_code, and status",
                    "existing_uid": str(existing.uid)
                },
                status=status.HTTP_409_CONFLICT
            )
        
        # Create new result entry
        result = UGBeforeCBCSStudentResult.objects.create(
            student=student,
            exam=exam,
            paper_code=paper_code,
            subject_name=subject_name,
            status=status_field,
            exam_type=exam_type,
            paper_type_code=paper_type_code,
            theory=theory,
            practical=practical,
            sessional=sessional,
            mark_secured=mark_secured,
            maximum_mark=maximum_mark,
            pass_mark=pass_mark,
            subject_code=request.data.get("subject_code"),
            temp_paper_code=request.data.get("temp_paper_code"),
            paper_code_correction=request.data.get("paper_code_correction"),
            subject_code_correction=request.data.get("subject_code_correction"),
            exam_type_his=request.data.get("exam_type_his"),
            is_ex_regular=request.data.get("is_ex_regular", False),
            mark_secured_history=request.data.get("mark_secured_history"),
            subject_total_mark=request.data.get("subject_total_mark"),
            subject_result=request.data.get("subject_result"),
        )
        
        return Response(
            {
                "message": "Result entry created successfully",
                "uid": str(result.uid),
                "student": {
                    "registration_no": student.registration_no,
                    "roll_no": student.roll_no,
                    "student_name": student.student_name
                },
                "exam": {
                    "exam_code": exam.exam_code,
                    "name": exam.name,
                    "session_code": exam.session_code
                },
                "result": {
                    "paper_code": result.paper_code,
                    "subject_name": result.subject_name,
                    "status": result.status,
                    "exam_type": result.exam_type,
                    "mark_secured": result.mark_secured,
                    "maximum_mark": result.maximum_mark
                }
            },
            status=status.HTTP_201_CREATED
        )


@method_decorator(csrf_exempt, name='dispatch')
class UGOldResultDeleteView(APIView):
    """
    Delete individual paper/result entry for a student.
    Allows deleting subject-wise entries one at a time.
    """
    permission_classes = [IsUniversityAdmin]
    
    def delete(self, request, uid):
        """
        Delete a result entry by UID
        """
        try:
            result = UGBeforeCBCSStudentResult.objects.get(uid=uid)
            result.delete()
            return Response(
                {
                    "message": "Result entry deleted successfully",
                    "deleted_entry": {
                        "uid": str(result.uid),
                        "paper_code": result.paper_code,
                        "subject_name": result.subject_name,
                        "status": result.status,
                        "exam_type": result.exam_type,
                        "mark_secured": result.mark_secured
                    }
                },
                status=status.HTTP_200_OK
            )
        except UGBeforeCBCSStudentResult.DoesNotExist:
            return Response(
                {"error": "Result entry not found"},
                status=status.HTTP_404_NOT_FOUND
            )
