from django.urls import path
from . import views

urlpatterns = [
    path('subjects/', views.SubjectLV.as_view(), name='subject-list'),
    path('subjects/<uuid:uid>/', views.SubjectDV.as_view(), name='subject-detail'),
    path('students/', views.StudentProfileLV.as_view(), name='student-list'),
    path('students/<uuid:uid>/', views.StudentProfileDV.as_view(), name='student-detail'),
    path('exams/', views.ExamLV.as_view(), name='exam-list'),
    path('exams/<uuid:uid>/', views.ExamDV.as_view(), name='exam-detail'),
    path('results/', views.StudentResultLV.as_view(), name='result-list'),
    path('summaries/', views.ExamSummaryLV.as_view(), name='summary-list'),
    path('marksheet/pdf/', views.UGOldMarksheetPDFView.as_view(), name='ug-old-marksheet-pdf'),
]
