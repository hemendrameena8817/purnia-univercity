from django.urls import path
from . import views

urlpatterns = [
    path('students/', views.StudentProfileLV.as_view(), name='student-list'),
    path('students/<uuid:uid>/', views.StudentProfileDV.as_view(), name='student-detail'),
    path('exams/', views.ExamLV.as_view(), name='exam-list'),
    path('exams/<uuid:uid>/', views.ExamDV.as_view(), name='exam-detail'),
    path('results/', views.StudentResultLV.as_view(), name='result-list'),
    path('results/create/', views.UGOldResultCreateView.as_view(), name='result-create'),
    path('results/<uuid:uid>/delete/', views.UGOldResultDeleteView.as_view(), name='result-delete'),
    path('marksheet/pdf/', views.UGOldMarksheetPDFView.as_view(), name='ug-old-marksheet-pdf'),
    path('marksheet/json/', views.UGOldMarksheetJSONView.as_view(), name='ug-old-marksheet-json'),
    path('marksheet/progressive/', views.UGOldMarksheetProgressiveView.as_view(), name='ug-old-marksheet-progressive'),
    path('marksheet/update/', views.UGOldMarksheetUpdateView.as_view(), name='ug-old-marksheet-update'),
    path('overview/', views.UGBeforeCBCSOverviewView.as_view(), name='ug-before-cbcs-overview'),
    path('overview/refresh/', views.UGBeforeCBCSOverviewRefreshView.as_view(), name='ug-before-cbcs-overview-refresh'),
]
