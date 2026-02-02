from rest_framework import generics
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCASubject, MCAExam, MCAResult, MCAResultDetail
)
from .serializers import (
    MCACourseSerializer, MCASessionSerializer, MCABatchSerializer,
    MCAStudentProfileSerializer, MCASubjectSerializer, MCAExamSerializer,
    MCAResultSerializer, MCAResultDetailSerializer
)

# Course Views
class MCACourseListView(generics.ListCreateAPIView):
    queryset = MCACourse.objects.all()
    serializer_class = MCACourseSerializer

class MCACourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCACourse.objects.all()
    serializer_class = MCACourseSerializer

# Session Views
class MCASessionListView(generics.ListCreateAPIView):
    queryset = MCASession.objects.all()
    serializer_class = MCASessionSerializer

class MCASessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCASession.objects.all()
    serializer_class = MCASessionSerializer

# Batch Views
class MCABatchListView(generics.ListCreateAPIView):
    queryset = MCABatch.objects.all()
    serializer_class = MCABatchSerializer

class MCABatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCABatch.objects.all()
    serializer_class = MCABatchSerializer

# Student Profile Views
class MCAStudentProfileListView(generics.ListAPIView):
    serializer_class = MCAStudentProfileSerializer
    
    def get_queryset(self):
        queryset = MCAStudentProfile.objects.all()
        
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

class MCAStudentProfileCreateView(generics.CreateAPIView):
    queryset = MCAStudentProfile.objects.all()
    serializer_class = MCAStudentProfileSerializer

class MCAStudentProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAStudentProfile.objects.all()
    serializer_class = MCAStudentProfileSerializer
    lookup_field = 'roll_no'

# Subject Views
class MCASubjectListView(generics.ListCreateAPIView):
    queryset = MCASubject.objects.all()
    serializer_class = MCASubjectSerializer

class MCASubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCASubject.objects.all()
    serializer_class = MCASubjectSerializer

# Exam Views
class MCAExamListView(generics.ListCreateAPIView):
    queryset = MCAExam.objects.all()
    serializer_class = MCAExamSerializer

class MCAExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAExam.objects.all()
    serializer_class = MCAExamSerializer

# Result Views
class MCAResultListView(generics.ListAPIView):
    serializer_class = MCAResultSerializer
    
    def get_queryset(self):
        queryset = MCAResult.objects.all()
        
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

class MCAResultCreateView(generics.CreateAPIView):
    queryset = MCAResult.objects.all()
    serializer_class = MCAResultSerializer

class MCAResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAResult.objects.all()
    serializer_class = MCAResultSerializer

# Result Detail (Marks) Views
class MCAResultMarksListView(generics.ListCreateAPIView):
    serializer_class = MCAResultDetailSerializer
    
    def get_queryset(self):
        queryset = MCAResultDetail.objects.all()
        result_id = self.request.query_params.get('result')
        if result_id:
            queryset = queryset.filter(result_id=result_id)
        return queryset

class MCAResultMarksDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAResultDetail.objects.all()
    serializer_class = MCAResultDetailSerializer
