from django.urls import path
from .views import (
    BTechCourseListView, BTechCourseDetailView,
    BTechSessionListView, BTechSessionDetailView,
    BTechBatchListView, BTechBatchDetailView,
    BTechStudentProfileListView, BTechStudentProfileCreateView, BTechStudentProfileDetailView,
    BTechCourseStructureListView, BTechCourseStructureDetailView,
    BTechExamListView, BTechExamDetailView,
    BTechExamScheduleListView, BTechExamScheduleDetailView,
    BTechStudentAssessmentListView, BTechStudentAssessmentDetailView,
    BTechExamResultListView, BTechExamResultDetailView,
    BTechSemesterRegistrationListView, BTechExamRegistrationListView,
    BTechAdmitCardPDFView, BTechBulkAdmitCardPDFView
)

urlpatterns = [
    # Courses
    path('courses/', BTechCourseListView.as_view(), name='btech-course-list'),
    path('courses/<uuid:uid>/', BTechCourseDetailView.as_view(), name='btech-course-detail'),

    # Sessions
    path('sessions/', BTechSessionListView.as_view(), name='btech-session-list'),
    path('sessions/<uuid:uid>/', BTechSessionDetailView.as_view(), name='btech-session-detail'),

    # Batches
    path('batches/', BTechBatchListView.as_view(), name='btech-batch-list'),
    path('batches/<uuid:uid>/', BTechBatchDetailView.as_view(), name='btech-batch-detail'),

    # Student Profiles
    path('students/', BTechStudentProfileListView.as_view(), name='btech-student-list'),
    path('students/create/', BTechStudentProfileCreateView.as_view(), name='btech-student-create'),
    path('students/<str:roll_no>/', BTechStudentProfileDetailView.as_view(), name='btech-student-detail'),

    # Course Structure (Subjects master)
    path('course-structures/', BTechCourseStructureListView.as_view(), name='btech-course-structure-list'),
    path('course-structures/<uuid:uid>/', BTechCourseStructureDetailView.as_view(), name='btech-course-structure-detail'),

    # Exams
    path('exams/', BTechExamListView.as_view(), name='btech-exam-list'),
    path('exams/<uuid:uid>/', BTechExamDetailView.as_view(), name='btech-exam-detail'),

    # Exam Schedules (Routines)
    path('exam-schedules/', BTechExamScheduleListView.as_view(), name='btech-exam-schedule-list'),
    path('exam-schedules/<uuid:uid>/', BTechExamScheduleDetailView.as_view(), name='btech-exam-schedule-detail'),

    # Assessments (Marks)
    path('assessments/', BTechStudentAssessmentListView.as_view(), name='btech-assessment-list'),
    path('assessments/<uuid:uid>/', BTechStudentAssessmentDetailView.as_view(), name='btech-assessment-detail'),

    # Exam Results
    path('exam-results/', BTechExamResultListView.as_view(), name='btech-exam-result-list'),
    path('exam-results/<uuid:uid>/', BTechExamResultDetailView.as_view(), name='btech-exam-result-detail'),

    # Registrations
    path('semester-registrations/', BTechSemesterRegistrationListView.as_view(), name='btech-sem-reg-list'),
    path('exam-registrations/', BTechExamRegistrationListView.as_view(), name='btech-exam-reg-list'),

    # Admit Card
    path('admit-card/pdf/', BTechAdmitCardPDFView.as_view(), name='btech-admit-card-pdf'),
    path('bulk-admit-card/pdf/', BTechBulkAdmitCardPDFView.as_view(), name='btech-bulk-admit-card-pdf'),
]
