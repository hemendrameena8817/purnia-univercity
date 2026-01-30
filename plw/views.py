from rest_framework import generics
from .models import (
    PLWCourse, PLWSession, PLWBatch, PLWStudentProfile, 
    PLWSubject, PLWExam, PLWResult, PLWResultDetail
)
from .serializers import (
    PLWCourseSerializer, PLWSessionSerializer, PLWBatchSerializer,
    PLWStudentProfileSerializer, PLWSubjectSerializer, PLWExamSerializer,
    PLWResultSerializer, PLWResultDetailSerializer
)

# Course Views
class PLWCourseListView(generics.ListCreateAPIView):
    queryset = PLWCourse.objects.all()
    serializer_class = PLWCourseSerializer

class PLWCourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWCourse.objects.all()
    serializer_class = PLWCourseSerializer

# Session Views
class PLWSessionListView(generics.ListCreateAPIView):
    queryset = PLWSession.objects.all()
    serializer_class = PLWSessionSerializer

class PLWSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWSession.objects.all()
    serializer_class = PLWSessionSerializer

# Batch Views
class PLWBatchListView(generics.ListCreateAPIView):
    queryset = PLWBatch.objects.all()
    serializer_class = PLWBatchSerializer

class PLWBatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWBatch.objects.all()
    serializer_class = PLWBatchSerializer

# Student Profile Views
class PLWStudentProfileListView(generics.ListAPIView):
    serializer_class = PLWStudentProfileSerializer
    
    def get_queryset(self):
        queryset = PLWStudentProfile.objects.all()
        
        roll_no = self.request.query_params.get('roll_no')
        if roll_no:
            queryset = queryset.filter(roll_no=roll_no)
            
        registration_no = self.request.query_params.get('registration_no')
        if registration_no:
            queryset = queryset.filter(registration_no=registration_no)
            
        batch = self.request.query_params.get('batch')
        if batch:
            queryset = queryset.filter(batch_id=batch)
            
        course = self.request.query_params.get('course')
        if course:
            queryset = queryset.filter(course_id=course)
            
        return queryset

class PLWStudentProfileCreateView(generics.CreateAPIView):
    queryset = PLWStudentProfile.objects.all()
    serializer_class = PLWStudentProfileSerializer

class PLWStudentProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWStudentProfile.objects.all()
    serializer_class = PLWStudentProfileSerializer
    lookup_field = 'roll_no'

# Subject Views
class PLWSubjectListView(generics.ListCreateAPIView):
    queryset = PLWSubject.objects.all()
    serializer_class = PLWSubjectSerializer

class PLWSubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWSubject.objects.all()
    serializer_class = PLWSubjectSerializer

# Exam Views
class PLWExamListView(generics.ListCreateAPIView):
    queryset = PLWExam.objects.all()
    serializer_class = PLWExamSerializer

class PLWExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWExam.objects.all()
    serializer_class = PLWExamSerializer

# Result Views
class PLWResultListView(generics.ListAPIView):
    serializer_class = PLWResultSerializer
    
    def get_queryset(self):
        queryset = PLWResult.objects.all()
        
        student = self.request.query_params.get('student')
        if student:
            queryset = queryset.filter(student_id=student)
            
        exam = self.request.query_params.get('exam')
        if exam:
            queryset = queryset.filter(exam_id=exam)
            
        status = self.request.query_params.get('result_status')
        if status:
            queryset = queryset.filter(result_status=status)
            
        return queryset

class PLWResultCreateView(generics.CreateAPIView):
    queryset = PLWResult.objects.all()
    serializer_class = PLWResultSerializer

class PLWResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWResult.objects.all()
    serializer_class = PLWResultSerializer

# Result Detail (Marks) Views
class PLWResultMarksListView(generics.ListCreateAPIView):
    serializer_class = PLWResultDetailSerializer
    
    def get_queryset(self):
        queryset = PLWResultDetail.objects.all()
        result_id = self.request.query_params.get('result')
        if result_id:
            queryset = queryset.filter(result_id=result_id)
        return queryset

class PLWResultMarksDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PLWResultDetail.objects.all()
    serializer_class = PLWResultDetailSerializer

import os
from django.conf import settings
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.text import slugify
from .utils.pdf_generator import generate_marksheet_pdf
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404

class PLWResultPDFView(View):
    """
    Generates and returns a single PDF marksheet for viewing/downloading.
    URL: /results/<registration_no>/pdf/
    Example: /results/1946B370095/pdf/
    """
    def get(self, request, registration_no):
        result = get_object_or_404(
            PLWResult.objects.select_related(
                'student', 'student__user', 'student__course', 'student__college', 'exam'
            ).prefetch_related('details', 'details__subject'), 
            student__registration_no=registration_no
        )
        
        pdf_content = generate_marksheet_pdf(result)
        
        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500, content_type='text/plain')
             
        response = HttpResponse(pdf_content, content_type='application/pdf')
        session_formatted = result.exam.session.replace('-', '_')
        filename = f"MARKSHEET_{result.student.registration_no}_PLW_{session_formatted}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

class PLWBulkMarksheetGenerateView(APIView):
    """
    Generates PDF marksheets for all filtered filtered filtered results and saves them locally.
    Query Params: exam_id (required)
    """
    def post(self, request):
        exam_id = request.data.get('exam_id')
        exam_uid = request.data.get('exam_uid')
        
        try:
            results = PLWResult.objects.select_related(
                'student', 'student__user', 'student__course', 'student__college', 'exam'
            ).prefetch_related('details', 'details__subject')
            
            if exam_id or exam_uid:
                if exam_id:
                    results = results.filter(exam_id=exam_id)
                else:
                    results = results.filter(exam__uid=exam_uid)
                
                if not results.exists():
                    identifier = exam_id if exam_id else exam_uid
                    return Response({"error": f"No results found for identifier: {identifier}"}, status=status.HTTP_404_NOT_FOUND)
                
                exam = results.first().exam
                exam_name = exam.name
                # Use uid for folder name if id is not available or if uid was provided
                folder_id = exam_id if exam_id else exam_uid
                folder_name = f"plw_marksheets_{slugify(exam_name)}_{folder_id}"
            else:
                if not results.exists():
                    return Response({"error": "No results found"}, status=status.HTTP_404_NOT_FOUND)
                folder_name = "plw_marksheets_all"

            save_path = os.path.join(settings.MEDIA_ROOT, folder_name)
            os.makedirs(save_path, exist_ok=True)
            
            generated_count = 0
            
            for result in results:
                pdf_content = generate_marksheet_pdf(result)
                if pdf_content:
                    session_formatted = result.exam.session.replace('-', '_')
                    filename = f"MARKSHEET_{result.student.registration_no}_PLW_{session_formatted}.pdf"
                    file_path = os.path.join(save_path, filename)
                    with open(file_path, 'wb') as f:
                        f.write(pdf_content)
                    generated_count += 1
            
            return Response({
                "message": f"Successfully generated {generated_count} marksheets.",
                "directory": save_path
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
