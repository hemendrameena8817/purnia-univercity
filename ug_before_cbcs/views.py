from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
import os

from .models import (
    UGBeforeCBCSStudentProfile,

    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult,
)
from .serializers import (
    UGBeforeCBCSStudentProfileSerializer,

    UGBeforeCBCSExamSerializer,
    UGBeforeCBCSStudentResultSerializer,

    MarksheetDataSerializer
)

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


# Marksheet PDF View 
class UGOldMarksheetPDFView(View):
    """
    Generates and returns the Marksheet PDF for Part I, II, or III.
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        part = request.GET.get("part")
        exam_type = request.GET.get("exam_type")

        if not registration_no or not part or not exam_type:
            return HttpResponse("registration_no, part, and exam_type are required", status=400)
 
        student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        
        # Call the PDF generator utility
        from .utils.pdf_generator import generate_ug_old_ba_hons_marksheet_pdf
        pdf_content = generate_ug_old_ba_hons_marksheet_pdf(student, part, exam_type=exam_type)
        
        if not pdf_content:
             return HttpResponse(f"Marksheet data not found for {student.student_name} ({part}).", status=404, content_type='text/plain')

        response = HttpResponse(pdf_content, content_type="application/pdf")
        filename = f"Marksheet_{student.registration_no}_{part}.pdf"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


class UGOldMarksheetJSONView(APIView):
    """
    Returns the Marksheet data in JSON format for Part I, II, or III.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        registration_no = request.query_params.get("registration_no")
        part = request.query_params.get("part")
        exam_type = request.query_params.get("exam_type")

        if not registration_no or not part:
            return Response(
                {"error": "registration_no and part are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
 
        student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        
        # Get marksheet context data
        from .utils.pdf_generator import get_ug_old_ba_hons_marksheet_context
        context_data = get_ug_old_ba_hons_marksheet_context(student, part, exam_type=exam_type)
        
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
                'course_code': student_obj.course_code,
                'discipline_code': student_obj.discipline_code,
            }
        
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
