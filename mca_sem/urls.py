from django.urls import path
from .views import (
    MCACourseListView, MCACourseDetailView,
    MCASessionListView, MCASessionDetailView,
    MCABatchListView, MCABatchDetailView,
    MCAStudentProfileListView, MCAStudentProfileCreateView, MCAStudentProfileDetailView,
    MCASubjectListView, MCASubjectDetailView,
    MCAExamListView, MCAExamDetailView,
    MCAResultListView, MCAResultCreateView, MCAResultDetailView,
    MCAResultMarksListView, MCAResultMarksDetailView
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

    # Results
    path('results/', MCAResultListView.as_view(), name='mca-result-list'),
    path('results/create/', MCAResultCreateView.as_view(), name='mca-result-create'),
    path('results/<int:pk>/', MCAResultDetailView.as_view(), name='mca-result-detail'),

    # Result Marks
    path('result-marks/', MCAResultMarksListView.as_view(), name='mca-result-marks-list'),
    path('result-marks/<int:pk>/', MCAResultMarksDetailView.as_view(), name='mca-result-marks-detail'),
]
