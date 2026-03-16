from django.urls import path
from . import views

urlpatterns = [
    # Student Profile endpoints
    path('students/', views.LLBStudentProfileListView.as_view(), name='llb-student-list'),
    path('students/<uuid:uid>/', views.LLBStudentProfileDetailView.as_view(), name='llb-student-detail'),
    
    # Exam endpoints
    path('exams/', views.LLBExamListView.as_view(), name='llb-exam-list'),
    path('exams/<uuid:uid>/', views.LLBExamDetailView.as_view(), name='llb-exam-detail'),
    
    # Assessment endpoints
    path('assessments/', views.LLBStudentCourseAssessmentListView.as_view(), name='llb-assessment-list'),
    path('assessments/create/', views.LLBStudentCourseAssessmentCreateView.as_view(), name='llb-assessment-create'),
    path('assessments/<uuid:uid>/', views.LLBStudentCourseAssessmentDetailView.as_view(), name='llb-assessment-detail'),
    path('assessments/<uuid:uid>/delete/', views.LLBStudentCourseAssessmentDeleteView.as_view(), name='llb-assessment-delete'),
    
    # Marksheet endpoints
    path('marksheet/json/', views.LLBMarksheetJSONView.as_view(), name='llb-marksheet-json'),
    path('marksheet/progressive/', views.LLBMarksheetProgressiveView.as_view(), name='llb-marksheet-progressive'),
    path('marksheet/update/', views.LLBMarksheetUpdateView.as_view(), name='llb-marksheet-update'),
    
    # PDF generation endpoints (existing - kept untouched)
    path('results/generate-bulk-pdf/', views.LLBBulkMarksheetGenerateView.as_view(), name='llb-result-bulk-pdf'),
    path('results/<str:registration_no>/pdf/', views.LLBResultPDFView.as_view(), name='llb-result-pdf'),
    
    # Debug endpoint for center mapping
    # path('debug/center-mapping/', views.debug_center_mapping, name='llb-debug-center-mapping'),
]
