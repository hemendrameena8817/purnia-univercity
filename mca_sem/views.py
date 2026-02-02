from rest_framework import generics
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCACourseStructure, MCACommonCourseStructure,
    MCAExam, MCAExamSchedule, MCASemesterRegistration, 
    MCAExamRegistration, MCAStudentAssessment, MCAExamResult
)
from .serializers import (
    MCACourseSerializer, MCASessionSerializer,
    MCABatchSerializer, MCAStudentProfileSerializer,
    MCACourseStructureSerializer, MCACommonCourseStructureSerializer,
    MCAExamSerializer, MCAExamScheduleSerializer, 
    MCASemesterRegistrationSerializer, MCAExamRegistrationSerializer,
    MCAStudentAssessmentSerializer, MCAExamResultSerializer
)

# Course Views
class MCACourseListView(generics.ListCreateAPIView):
    queryset = MCACourse.objects.all()
    serializer_class = MCACourseSerializer

class MCACourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCACourse.objects.all()
    serializer_class = MCACourseSerializer
    lookup_field = 'uid'

# Session Views
class MCASessionListView(generics.ListCreateAPIView):
    queryset = MCASession.objects.all()
    serializer_class = MCASessionSerializer

class MCASessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCASession.objects.all()
    serializer_class = MCASessionSerializer
    lookup_field = 'uid'

# Batch Views
class MCABatchListView(generics.ListCreateAPIView):
    queryset = MCABatch.objects.all()
    serializer_class = MCABatchSerializer

class MCABatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCABatch.objects.all()
    serializer_class = MCABatchSerializer
    lookup_field = 'uid'

# Student Profile Views
class MCAStudentProfileListView(generics.ListAPIView):
    serializer_class = MCAStudentProfileSerializer
    def get_queryset(self):
        queryset = MCAStudentProfile.objects.all()
        roll_no = self.request.query_params.get('roll_no')
        if roll_no: queryset = queryset.filter(roll_no=roll_no)
        reg_no = self.request.query_params.get('registration_no')
        if reg_no: queryset = queryset.filter(registration_no=reg_no)
        return queryset

class MCAStudentProfileCreateView(generics.CreateAPIView):
    queryset = MCAStudentProfile.objects.all()
    serializer_class = MCAStudentProfileSerializer

class MCAStudentProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAStudentProfile.objects.all()
    serializer_class = MCAStudentProfileSerializer
    lookup_field = 'roll_no'

# Course Structure Views
class MCACourseStructureListView(generics.ListCreateAPIView):
    queryset = MCACourseStructure.objects.all()
    serializer_class = MCACourseStructureSerializer

class MCACourseStructureDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCACourseStructure.objects.all()
    serializer_class = MCACourseStructureSerializer
    lookup_field = 'uid'

# Exam Views
class MCAExamListView(generics.ListCreateAPIView):
    queryset = MCAExam.objects.all()
    serializer_class = MCAExamSerializer

class MCAExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAExam.objects.all()
    serializer_class = MCAExamSerializer
    lookup_field = 'uid'

# Exam Schedule Views
class MCAExamScheduleListView(generics.ListCreateAPIView):
    serializer_class = MCAExamScheduleSerializer
    def get_queryset(self):
        queryset = MCAExamSchedule.objects.all()
        exam_id = self.request.query_params.get('exam')
        if exam_id: queryset = queryset.filter(exam_id=exam_id)
        return queryset

class MCAExamScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAExamSchedule.objects.all()
    serializer_class = MCAExamScheduleSerializer
    lookup_field = 'uid'

# Assessment Views
class MCAStudentAssessmentListView(generics.ListCreateAPIView):
    serializer_class = MCAStudentAssessmentSerializer
    def get_queryset(self):
        queryset = MCAStudentAssessment.objects.all()
        student = self.request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        return queryset

class MCAStudentAssessmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAStudentAssessment.objects.all()
    serializer_class = MCAStudentAssessmentSerializer
    lookup_field = 'uid'

# Exam Result Views
class MCAExamResultListView(generics.ListCreateAPIView):
    serializer_class = MCAExamResultSerializer
    def get_queryset(self):
        queryset = MCAExamResult.objects.all()
        student = self.request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        return queryset

class MCAExamResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MCAExamResult.objects.all()
    serializer_class = MCAExamResultSerializer
    lookup_field = 'uid'

# Registration Views
class MCASemesterRegistrationListView(generics.ListCreateAPIView):
    queryset = MCASemesterRegistration.objects.all()
    serializer_class = MCASemesterRegistrationSerializer

class MCAExamRegistrationListView(generics.ListCreateAPIView):
    queryset = MCAExamRegistration.objects.all()
    serializer_class = MCAExamRegistrationSerializer
