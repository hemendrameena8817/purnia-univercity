from django.urls import path
from .views import *


urlpatterns = [
    # Courses
    path('courses/', MBACourseListView.as_view(), name='mba-course-list'),
    path('courses/<uuid:uid>/', MBACourseDetailView.as_view(), name='mca-course-detail'),

    # Sessions
    path('sessions/', MBASessionListView.as_view(), name='mba-session-list'),
    path('sessions/<uuid:uid>/', MBASessionDetailView.as_view(), name='mba-session-detail'),

    # Batches
    path('batches/', MBABatchListView.as_view(), name='mba-batch-list'),
    path('batches/<uuid:uid>/', MBABatchDetailView.as_view(), name='mba-batch-detail'),

    # Student Profiles
    path('students/', MBAStudentProfileListView.as_view(), name='mba-student-list'),
    path('students/create/', MBAStudentProfileCreateView.as_view(), name='mba-student-create'),
    path('students/<str:roll_no>/', MBAStudentProfileDetailView.as_view(), name='mba-student-detail'),

    # Course Structure (Subjects master)
    path('course-structures/', MBACourseStructureListView.as_view(), name='mba-course-structure-list'),
    path('course-structures/<uuid:uid>/', MBACourseStructureDetailView.as_view(), name='mba-course-structure-detail'),

    # Exams
    path('exams/', MBAExamListView.as_view(), name='mba-exam-list'),
    path('exams/<uuid:uid>/', MBAExamDetailView.as_view(), name='mba-exam-detail'),

    # Exam Schedules (Routines)
    path('exam-schedules/', MBAExamScheduleListView.as_view(), name='mba-exam-schedule-list'),
    path('exam-schedules/<uuid:uid>/', MBAExamScheduleDetailView.as_view(), name='mba-exam-schedule-detail'),

    # Assessments (Marks)
    path('assessments/', MBAStudentAssessmentListView.as_view(), name='mba-assessment-list'),
    path('assessments/<uuid:uid>/', MBAStudentAssessmentDetailView.as_view(), name='mba-assessment-detail'),

    # Exam Results
    path('exam-results/', MBAExamResultListView.as_view(), name='mba-exam-result-list'),
    path('exam-results/<uuid:uid>/', MBAExamResultDetailView.as_view(), name='mba-bexam-result-detail'),

    # Registrations
    path('semester-registrations/', MBASemesterRegistrationListView.as_view(), name='mba-sem-reg-list'),
    path('exam-registrations/', MBAExamRegistrationListView.as_view(), name='mba-exam-reg-list'),

    # Admit Card
    path('admit-card/pdf/', MBAAdmitCardPDFView.as_view(), name='mba-admit-card-pdf'),
    path('bulk-admit-card/pdf/', MBABulkAdmitCardPDFView.as_view(), name='mba-bulk-admit-card-pdf'),
    path('roll-sheet/pdf/', MBARollSheetPDFView.as_view(), name='mba-roll-sheet-pdf'),
    path('mba/attendance-sheet/pdf/', MBAAttendanceSheetPDFView.as_view(),name='mba-attendance-sheet-pdf'),
    path('mba/result/',MBAResultSheetPDFView.as_view(),name="mba-result-sheet-pdf"),

    path('mba-department/', MBACourseGetAPI.as_view(), name='mba-courses-department'),
    path("course-subjects/", CourseSubjectsViaRegistrationAPIView.as_view(),name="course-subjects-via-registration"),
    path("college-students/",MBACollegeStudentsView.as_view(),name="mba-college-students"),
    path("marks-entry/",MBAMarksEntryView.as_view(),name="mba-marks-entry"),
    path("student-assessments/",MBAStudentCourseAssessmentAPIView.as_view(),name="mba-student-assessments"),
]   
