from django.urls import path
from .views import (
    MCACourseListView, MCACourseDetailView,
    MCASessionListView, MCASessionDetailView,
    MCABatchListView, MCABatchDetailView,
    MCAStudentProfileListView, MCAStudentProfileCreateView, MCAStudentProfileDetailView,
    MCACourseStructureListView, MCACourseStructureDetailView,
    MCAExamListView, MCAExamDetailView,
    MCAExamScheduleListView, MCAExamScheduleDetailView,
    MCAStudentAssessmentListView, MCAStudentAssessmentDetailView,
    MCAExamResultListView, MCAExamResultDetailView,
    MCASemesterRegistrationListView, MCAExamRegistrationListView
)

urlpatterns = [
    # Courses
    path('courses/', MCACourseListView.as_view(), name='mca-course-list'),
    path('courses/<uuid:uid>/', MCACourseDetailView.as_view(), name='mca-course-detail'),

    # Sessions
    path('sessions/', MCASessionListView.as_view(), name='mca-session-list'),
    path('sessions/<uuid:uid>/', MCASessionDetailView.as_view(), name='mca-session-detail'),

    # Batches
    path('batches/', MCABatchListView.as_view(), name='mca-batch-list'),
    path('batches/<uuid:uid>/', MCABatchDetailView.as_view(), name='mca-batch-detail'),

    # Student Profiles
    path('students/', MCAStudentProfileListView.as_view(), name='mca-student-list'),
    path('students/create/', MCAStudentProfileCreateView.as_view(), name='mca-student-create'),
    path('students/<str:roll_no>/', MCAStudentProfileDetailView.as_view(), name='mca-student-detail'),

    # Course Structure (Subjects master)
    path('course-structures/', MCACourseStructureListView.as_view(), name='mca-course-structure-list'),
    path('course-structures/<uuid:uid>/', MCACourseStructureDetailView.as_view(), name='mca-course-structure-detail'),

    # Exams
    path('exams/', MCAExamListView.as_view(), name='mca-exam-list'),
    path('exams/<uuid:uid>/', MCAExamDetailView.as_view(), name='mca-exam-detail'),

    # Exam Schedules (Routines)
    path('exam-schedules/', MCAExamScheduleListView.as_view(), name='mca-exam-schedule-list'),
    path('exam-schedules/<uuid:uid>/', MCAExamScheduleDetailView.as_view(), name='mca-exam-schedule-detail'),

    # Assessments (Marks)
    path('assessments/', MCAStudentAssessmentListView.as_view(), name='mca-assessment-list'),
    path('assessments/<uuid:uid>/', MCAStudentAssessmentDetailView.as_view(), name='mca-assessment-detail'),

    # Exam Results
    path('exam-results/', MCAExamResultListView.as_view(), name='mca-exam-result-list'),
    path('exam-results/<uuid:uid>/', MCAExamResultDetailView.as_view(), name='mca-exam-result-detail'),

    # Registrations
    path('semester-registrations/', MCASemesterRegistrationListView.as_view(), name='mca-sem-reg-list'),
    path('exam-registrations/', MCAExamRegistrationListView.as_view(), name='mca-exam-reg-list'),
]
