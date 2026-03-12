from rest_framework import generics
from django.db.models import Prefetch
from .models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile, 
    LLBCourseStructure, LLBExam, LLBStudentExamResult, LLBStudentCourseAssessment
)
from .serializers import (
    LLBCourseSerializer, LLBSessionSerializer, LLBBatchSerializer,
    LLBStudentProfileSerializer, LLBCourseStructureSerializer, LLBExamSerializer,
    LLBStudentExamResultSerializer, LLBStudentCourseAssessmentSerializer
)

def normalize_semester(semester):
    """Convert semester names to consistent format (1ST, 2ND, etc.)"""
    semester_mapping = {
        '1st': '1ST', 'first': '1ST', '1': '1ST',
        '2nd': '2ND', 'second': '2ND', '2': '2ND', 
        '3rd': '3RD', 'third': '3RD', '3': '3RD',
        '4th': '4TH', 'fourth': '4TH', '4': '4TH',
        '5th': '5TH', 'fifth': '5TH', '5': '5TH',
        '6th': '6TH', 'sixth': '6TH', '6': '6TH'
    }
    return semester_mapping.get(semester.lower(), semester.upper())

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
            
        semester = self.request.query_params.get('semester')
        if semester:
            semester_normalized = normalize_semester(semester)
            queryset = queryset.filter(course_assessments__semester=semester_normalized).distinct()
            
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
    serializer_class = LLBExamSerializer
    
    def get_queryset(self):
        queryset = LLBExam.objects.all()
        
        semester = self.request.query_params.get('semester')
        if semester:
            semester_normalized = normalize_semester(semester)
            queryset = queryset.filter(semester=semester_normalized)
            
        session = self.request.query_params.get('session')
        if session:
            queryset = queryset.filter(session__icontains=session)
            
        batch = self.request.query_params.get('batch')
        if batch:
            queryset = queryset.filter(batch_id=batch)
            
        return queryset

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
            
        semester = self.request.query_params.get('semester')
        if semester:
            semester_normalized = normalize_semester(semester)
            queryset = queryset.filter(exam__semester=semester_normalized)
            
        return queryset

class LLBStudentExamResultCreateView(generics.CreateAPIView):
    queryset = LLBStudentExamResult.objects.all()
    serializer_class = LLBStudentExamResultSerializer

class LLBStudentExamResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBStudentExamResult.objects.all()
    serializer_class = LLBStudentExamResultSerializer

# Assessment (Marks) Views
class LLBStudentCourseAssessmentListView(generics.ListCreateAPIView):
    serializer_class = LLBStudentCourseAssessmentSerializer
    
    def get_queryset(self):
        queryset = LLBStudentCourseAssessment.objects.all()
        
        exam_result_id = self.request.query_params.get('exam_result')
        if exam_result_id:
            queryset = queryset.filter(exam_result_id=exam_result_id)
            
        semester = self.request.query_params.get('semester')
        if semester:
            semester_normalized = normalize_semester(semester)
            queryset = queryset.filter(semester=semester_normalized)
            
        student = self.request.query_params.get('student')
        if student:
            queryset = queryset.filter(student_id=student)
            
        exam = self.request.query_params.get('exam')
        if exam:
            queryset = queryset.filter(exam_id=exam)
            
        label = self.request.query_params.get('label')
        if label:
            queryset = queryset.filter(label__icontains=label)
            
        return queryset

class LLBStudentCourseAssessmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBStudentCourseAssessment.objects.all()
    serializer_class = LLBStudentCourseAssessmentSerializer

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
    URL: /results/<registration_no>/pdf/?semester=1ST&type=regular
    Examples: 
        - /results/1946B370095/pdf/?semester=1ST (all exam types)
        - /results/1946B370095/pdf/?semester=1ST&type=regular (Regular exams only)
        - /results/1946B370095/pdf/?semester=1ST&type=back (Back/Backlog exams only)
    
    Query Parameters:
        - semester: Semester to return (1ST, 2ND, 3RD, etc.)
        - type: Optional. When set to 'regular' or 'back', filters for that exam type only
    """
    def get(self, request, registration_no):
        semester = request.GET.get('semester', '1')
        semester_normalized = normalize_semester(semester)
        exam_type = request.GET.get('type', None)  # Get exam type from query params
        
        # Build filter for results
        result_filters = {
            'student__registration_no': registration_no,
            'student_assessments_result__semester': semester_normalized
        }
        
        # Add exam_type filter if type parameter is provided
        exam_type_value = None
        if exam_type:
            exam_type_lower = exam_type.lower()
            if exam_type_lower == 'regular':
                exam_type_value = 'Regular'
                result_filters['student_assessments_result__exam_type__iexact'] = exam_type_value
            elif exam_type_lower == 'back':
                exam_type_value = 'Back'
                result_filters['student_assessments_result__exam_type__iexact'] = exam_type_value
        
        results = LLBStudentExamResult.objects.select_related(
            'student', 'student__user', 'student__course', 'student__college', 'exam'
        ).filter(**result_filters).distinct().order_by('-created_at')
        
        if not results.exists():
            exam_type_msg = f" ({exam_type_value})" if exam_type_value else ""
            raise Http404(f"No results found for registration number: {registration_no} in semester {semester_normalized}{exam_type_msg}")
        
        # Get the latest result for that semester
        result = results.first()
        
        # Manually filter assessments by semester and exam_type
        assessment_filters = {'semester': semester_normalized}
        if exam_type_value:
            assessment_filters['exam_type__iexact'] = exam_type_value
        
        filtered_assessments = result.student_assessments_result.filter(**assessment_filters).select_related('course_structure').order_by('paper_code')
        
        # Temporarily override the assessments with filtered ones
        result._filtered_assessments = filtered_assessments
        
        pdf_content = generate_marksheet_pdf(result, semester=semester_normalized)
        
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
            ).prefetch_related('student_assessments_result', 'student_assessments_result__course_structure')
            
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
