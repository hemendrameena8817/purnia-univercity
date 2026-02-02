from rest_framework import generics
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCASubject, MCAExam, MCAExamSchedule, MCAStudentAssessment, 
    MCASemesterResult, MCASemesterRegistration, MCAExamRegistration
)
from .serializers import (
    MCACourseSerializer, MCASessionSerializer, MCABatchSerializer,
    MCAStudentProfileSerializer, MCASubjectSerializer, MCAExamSerializer,
    MCAExamScheduleSerializer, MCAStudentAssessmentSerializer,
    MCASemesterResultSerializer, MCASemesterRegistrationSerializer,
    MCAExamRegistrationSerializer
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

# Exam Schedule Views
class MCAExamScheduleListView(generics.ListCreateAPIView):
    serializer_class = MCAExamScheduleSerializer
    def get_queryset(self):
        queryset = MCAExamSchedule.objects.all()
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            queryset = queryset.filter(exam_id=exam_id)
        return queryset

class MCAExamScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAExamSchedule.objects.all()
    serializer_class = MCAExamScheduleSerializer

# Assessment Views
class MCAStudentAssessmentListView(generics.ListCreateAPIView):
    serializer_class = MCAStudentAssessmentSerializer
    def get_queryset(self):
        queryset = MCAStudentAssessment.objects.all()
        student = self.request.query_params.get('student')
        if student:
            queryset = queryset.filter(student_id=student)
        semester = self.request.query_params.get('semester')
        if semester:
            queryset = queryset.filter(semester=semester)
        return queryset

class MCAStudentAssessmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAStudentAssessment.objects.all()
    serializer_class = MCAStudentAssessmentSerializer

# Semester Result Views
class MCASemesterResultListView(generics.ListCreateAPIView):
    serializer_class = MCASemesterResultSerializer
    def get_queryset(self):
        queryset = MCASemesterResult.objects.all()
        student = self.request.query_params.get('student')
        if student:
            queryset = queryset.filter(student_id=student)
        return queryset

class MCASemesterResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCASemesterResult.objects.all()
    serializer_class = MCASemesterResultSerializer

# Registration Views
class MCASemesterRegistrationListView(generics.ListCreateAPIView):
    queryset = MCASemesterRegistration.objects.all()
    serializer_class = MCASemesterRegistrationSerializer

class MCAExamRegistrationListView(generics.ListCreateAPIView):
    queryset = MCAExamRegistration.objects.all()
    serializer_class = MCAExamRegistrationSerializer
