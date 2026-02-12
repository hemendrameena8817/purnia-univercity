from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.CourseLV.as_view(), name='course-list'),
    path('courses/<uuid:uid>/', views.CourseDV.as_view(), name='course-detail'),
    
    path('disciplines/', views.DisciplineLV.as_view(), name='discipline-list'),
    path('disciplines/<uuid:uid>/', views.DisciplineDV.as_view(), name='discipline-detail'),
    
    path('sessions/', views.SessionLV.as_view(), name='session-list'),
    path('sessions/<uuid:uid>/', views.SessionDV.as_view(), name='session-detail'),
    
    path('batches/', views.BatchLV.as_view(), name='batch-list'),
    path('batches/<uuid:uid>/', views.BatchDV.as_view(), name='batch-detail'),
    
    path('subjects/', views.SubjectLV.as_view(), name='subject-list'),
    path('subjects/<uuid:uid>/', views.SubjectDV.as_view(), name='subject-detail'),
    
    path('students/', views.StudentProfileLV.as_view(), name='student-list'),
    path('students/<uuid:uid>/', views.StudentProfileDV.as_view(), name='student-detail'),
    
    path('exams/', views.ExamLV.as_view(), name='exam-list'),
    path('exams/<uuid:uid>/', views.ExamDV.as_view(), name='exam-detail'),
    
    path('registrations/', views.ExamRegistrationLV.as_view(), name='registration-list'),
    path('results/', views.ExamResultLV.as_view(), name='result-list'),
    
    # Marksheet PDF
    path('marksheet/pdf/', views.UGOldMarksheetPDFView.as_view(), name='ug-old-marksheet-pdf'),
]
