from django.urls import path
from .views import (
    MCACourseListView, MCACourseDetailView,
    MCASessionListView, MCASessionDetailView,
    MCABatchListView, MCABatchDetailView,
    MCAStudentProfileListView, MCAStudentProfileCreateView, MCAStudentProfileDetailView,
    MCASubjectListView, MCASubjectDetailView,
    MCAExamListView, MCAExamDetailView,
    MCAExamScheduleListView, MCAExamScheduleDetailView,
    MCAStudentAssessmentListView, MCAStudentAssessmentDetailView,
    MCASemesterResultListView, MCASemesterResultDetailView,
    MCASemesterRegistrationListView, MCAExamRegistrationListView
)

urlpatterns = [
    # Courses
    path('courses/', MCACourseListView.as_view(), name='mca-course-list'),
    path('courses/<int:pk>/', MCACourseDetailView.as_view(), name='mca-course-detail'),

    # Sessions
    path('sessions/', MCASessionListView.as_view(), name='mca-session-list'),
    path('sessions/<int:pk>/', MCASessionDetailView.as_view(), name='mca-session-detail'),

    # Batches
    path('batches/', MCABatchListView.as_view(), name='mca-batch-list'),
    path('batches/<int:pk>/', MCABatchDetailView.as_view(), name='mca-batch-detail'),

    # Student Profiles
    path('students/', MCAStudentProfileListView.as_view(), name='mca-student-list'),
    path('students/create/', MCAStudentProfileCreateView.as_view(), name='mca-student-create'),
    path('students/<str:roll_no>/', MCAStudentProfileDetailView.as_view(), name='mca-student-detail'),

    # Subjects
    path('subjects/', MCASubjectListView.as_view(), name='mca-subject-list'),
    path('subjects/<int:pk>/', MCASubjectDetailView.as_view(), name='mca-subject-detail'),

    # Exams
    path('exams/', MCAExamListView.as_view(), name='mca-exam-list'),
    path('exams/<int:pk>/', MCAExamDetailView.as_view(), name='mca-exam-detail'),

    # Exam Schedules (Routines)
    path('exam-schedules/', MCAExamScheduleListView.as_view(), name='mca-exam-schedule-list'),
    path('exam-schedules/<int:pk>/', MCAExamScheduleDetailView.as_view(), name='mca-exam-schedule-detail'),

    # Assessments (Marks)
    path('assessments/', MCAStudentAssessmentListView.as_view(), name='mca-assessment-list'),
    path('assessments/<int:pk>/', MCAStudentAssessmentDetailView.as_view(), name='mca-assessment-detail'),

    # Semester Results
    path('semester-results/', MCASemesterResultListView.as_view(), name='mca-sem-result-list'),
    path('semester-results/<int:pk>/', MCASemesterResultDetailView.as_view(), name='mca-sem-result-detail'),

    # Registrations
    path('semester-registrations/', MCASemesterRegistrationListView.as_view(), name='mca-sem-reg-list'),
    path('exam-registrations/', MCAExamRegistrationListView.as_view(), name='mca-exam-reg-list'),
]
