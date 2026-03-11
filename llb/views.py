from rest_framework import generics
from .models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile, 
    LLBCourseStructure, LLBExam, LLBStudentExamResult, LLBStudentAssessment
)
from .serializers import (
    LLBCourseSerializer, LLBSessionSerializer, LLBBatchSerializer,
    LLBStudentProfileSerializer, LLBCourseStructureSerializer, LLBExamSerializer,
    LLBStudentExamResultSerializer, LLBStudentAssessmentSerializer
)

# Course Views
class LLBCourseListView(generics.ListCreateAPIView):
    queryset = LLBCourse.objects.all()
    serializer_class = LLBCourseSerializer

class LLBCourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBCourse.objects.all()
    serializer_class = LLBCourseSerializer

# Session Views
class LLBSessionListView(generics.ListCreateAPIView):
    queryset = LLBSession.objects.all()
    serializer_class = LLBSessionSerializer

class LLBSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBSession.objects.all()
    serializer_class = LLBSessionSerializer

# Batch Views
class LLBBatchListView(generics.ListCreateAPIView):
    queryset = LLBBatch.objects.all()
    serializer_class = LLBBatchSerializer

class LLBBatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBBatch.objects.all()
    serializer_class = LLBBatchSerializer

# Student Profile Views
class LLBStudentProfileListView(generics.ListAPIView):
    serializer_class = LLBStudentProfileSerializer
    
    def get_queryset(self):
        queryset = LLBStudentProfile.objects.all()
        
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

class LLBStudentProfileCreateView(generics.CreateAPIView):
    queryset = LLBStudentProfile.objects.all()
    serializer_class = LLBStudentProfileSerializer

class LLBStudentProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBStudentProfile.objects.all()
    serializer_class = LLBStudentProfileSerializer
    lookup_field = 'roll_no'

# Course Structure Views
class LLBCourseStructureListView(generics.ListCreateAPIView):
    queryset = LLBCourseStructure.objects.all()
    serializer_class = LLBCourseStructureSerializer

class LLBCourseStructureDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBCourseStructure.objects.all()
    serializer_class = LLBCourseStructureSerializer

# Exam Views
class LLBExamListView(generics.ListCreateAPIView):
    queryset = LLBExam.objects.all()
    serializer_class = LLBExamSerializer

class LLBExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBExam.objects.all()
    serializer_class = LLBExamSerializer

# Exam Result Views
class LLBStudentExamResultListView(generics.ListAPIView):
    serializer_class = LLBStudentExamResultSerializer
    
    def get_queryset(self):
        queryset = LLBStudentExamResult.objects.all()
        
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

class LLBStudentExamResultCreateView(generics.CreateAPIView):
    queryset = LLBStudentExamResult.objects.all()
    serializer_class = LLBStudentExamResultSerializer

class LLBStudentExamResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBStudentExamResult.objects.all()
    serializer_class = LLBStudentExamResultSerializer

# Assessment (Marks) Views
class LLBStudentAssessmentListView(generics.ListCreateAPIView):
    serializer_class = LLBStudentAssessmentSerializer
    
    def get_queryset(self):
        queryset = LLBStudentAssessment.objects.all()
        exam_result_id = self.request.query_params.get('exam_result')
        if exam_result_id:
            queryset = queryset.filter(exam_result_id=exam_result_id)
        return queryset

class LLBStudentAssessmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBStudentAssessment.objects.all()
    serializer_class = LLBStudentAssessmentSerializer

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

class LLBResultPDFView(View):
    """
    Generates and returns a single PDF marksheet for viewing/downloading.
    URL: /results/<registration_no>/pdf/?part=1
    Example: /results/1946B370095/pdf/?part=1
    part parameter specifies which result to return (1=latest, 2=second latest, etc.)
    """
    def get(self, request, registration_no):
        # Get part parameter, default to 1 (latest)
        part = request.GET.get('part', '1')
        try:
            part = int(part)
            if part < 1:
                part = 1
        except ValueError:
            part = 1
        
        results = LLBStudentExamResult.objects.select_related(
            'student', 'student__user', 'student__course', 'student__college', 'exam'
        ).prefetch_related('assessments', 'assessments__subject').filter(
            student__registration_no=registration_no
        ).order_by('-created_at')
        
        if not results.exists():
            raise Http404(f"No results found for registration number: {registration_no}")
        
        # Check if requested part exists
        if results.count() < part:
            raise Http404(f"Only {results.count()} result(s) found for registration number: {registration_no}. Requested part: {part}")
        
        result = results[part - 1]  # Get the requested result (0-indexed)
        
        pdf_content = generate_marksheet_pdf(result)
        
        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500, content_type='text/plain')
             
        response = HttpResponse(pdf_content, content_type='application/pdf')
        session_formatted = result.exam.session.replace('-', '_')
        filename = f"MARKSHEET_{result.student.registration_no}_LLB_{session_formatted}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

class LLBBulkMarksheetGenerateView(APIView):
    """
    Generates PDF marksheets for all filtered filtered filtered results and saves them locally.
    Query Params: exam_id (required)
    """
    def post(self, request):
        exam_uid = request.data.get('exam_uid') or request.query_params.get('exam_uid')
        
        try:
            results = LLBStudentExamResult.objects.select_related(
                'student', 'student__user', 'student__course', 'student__college', 'exam'
            ).prefetch_related('assessments', 'assessments__subject')
            
            # 1. Filter results based on provided UID
            if exam_uid:
                results = results.filter(exam__uid=exam_uid)
                if not results.exists():
                    return Response({"error": f"No results found for exam_uid: {exam_uid}"}, status=status.HTTP_404_NOT_FOUND)
                
                exam = results.first().exam
                folder_name = f"Marksheets_{slugify(exam.name)}_{exam_uid}"
            else:
                # 2. If no UID provided, check if any results exist at all (fallback to "all")
                if not results.exists():
                    return Response({"error": "No results found in the system"}, status=status.HTTP_404_NOT_FOUND)
                folder_name = "Marksheets_all"

            save_path = os.path.join(settings.MEDIA_ROOT, folder_name)
            os.makedirs(save_path, exist_ok=True)
            
            generated_count = 0
            
            for result in results:
                pdf_content = generate_marksheet_pdf(result)
                if pdf_content:
                    session_formatted = result.exam.session.replace('-', '_')
                    filename = f"MARKSHEET_{result.student.registration_no}_LLB_{session_formatted}.pdf"
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
