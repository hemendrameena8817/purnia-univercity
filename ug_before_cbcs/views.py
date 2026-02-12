from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os

from .models import (
    UGBeforeCBCSCourse, UGBeforeCBCSDiscipline, UGBeforeCBCSSession,
    UGBeforeCBCSBatch, UGBeforeCBCSSubject, UGBeforeCBCSCourseStructure,
    UGBeforeCBCSStudentProfile, UGBeforeCBCSExam, UGBeforeCBCSExamRegistration,
    UGBeforeCBCSStudentAssessment, UGBeforeCBCSExamResult
)
from .serializers import (
    UGBeforeCBCSCourseSerializer, UGBeforeCBCSDisciplineSerializer,
    UGBeforeCBCSSessionSerializer, UGBeforeCBCSBatchSerializer,
    UGBeforeCBCSSubjectSerializer, UGBeforeCBCSCourseStructureSerializer,
    UGBeforeCBCSStudentProfileSerializer, UGBeforeCBCSExamSerializer,
    UGBeforeCBCSExamRegistrationSerializer, UGBeforeCBCSStudentAssessmentSerializer,
    UGBeforeCBCSExamResultSerializer
)

# Base API Views (List & Detail)
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

# Specific Views
class CourseLV(BaseUGLV): model = UGBeforeCBCSCourse; serializer_class = UGBeforeCBCSCourseSerializer
class CourseDV(BaseUGDV): model = UGBeforeCBCSCourse; serializer_class = UGBeforeCBCSCourseSerializer

class DisciplineLV(BaseUGLV): model = UGBeforeCBCSDiscipline; serializer_class = UGBeforeCBCSDisciplineSerializer
class DisciplineDV(BaseUGDV): model = UGBeforeCBCSDiscipline; serializer_class = UGBeforeCBCSDisciplineSerializer

class SessionLV(BaseUGLV): model = UGBeforeCBCSSession; serializer_class = UGBeforeCBCSSessionSerializer
class SessionDV(BaseUGDV): model = UGBeforeCBCSSession; serializer_class = UGBeforeCBCSSessionSerializer

class BatchLV(BaseUGLV): model = UGBeforeCBCSBatch; serializer_class = UGBeforeCBCSBatchSerializer
class BatchDV(BaseUGDV): model = UGBeforeCBCSBatch; serializer_class = UGBeforeCBCSBatchSerializer

class SubjectLV(BaseUGLV): model = UGBeforeCBCSSubject; serializer_class = UGBeforeCBCSSubjectSerializer
class SubjectDV(BaseUGDV): model = UGBeforeCBCSSubject; serializer_class = UGBeforeCBCSSubjectSerializer

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
    model = UGBeforeCBCSStudentProfile; serializer_class = UGBeforeCBCSStudentProfileSerializer

class ExamLV(BaseUGLV): model = UGBeforeCBCSExam; serializer_class = UGBeforeCBCSExamSerializer
class ExamDV(BaseUGDV): model = UGBeforeCBCSExam; serializer_class = UGBeforeCBCSExamSerializer

class ExamRegistrationLV(BaseUGLV): model = UGBeforeCBCSExamRegistration; serializer_class = UGBeforeCBCSExamRegistrationSerializer
class ExamResultLV(BaseUGLV): model = UGBeforeCBCSExamResult; serializer_class = UGBeforeCBCSExamResultSerializer

# Marksheet PDF View (Skeleton)
class UGOldMarksheetPDFView(View):
    """
    Generates and returns the Marksheet PDF for Part I, II, or III.
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        part = request.GET.get("part") # PART1, PART2, PART3

        if not registration_no or not part:
            return HttpResponse("registration_no and part are required", status=400)

        student = get_object_or_404(UGBeforeCBCSStudentProfile, registration_no=registration_no)
        
        # Call the PDF generator utility
        from .utils.pdf_generator import generate_ug_old_marksheet_pdf
        pdf_content = generate_ug_old_marksheet_pdf(student, part)
        
        if not pdf_content:
             return HttpResponse(f"Marksheet data not found for {student.student_name} ({part}).", status=404, content_type='text/plain')

        response = HttpResponse(pdf_content, content_type="application/pdf")
        filename = f"Marksheet_{student.registration_no}_{part}.pdf"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
