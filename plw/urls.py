from django.urls import path
from .views import (
    PLWCourseListView, PLWCourseDetailView,
    PLWSessionListView, PLWSessionDetailView,
    PLWBatchListView, PLWBatchDetailView,
    PLWStudentProfileListView, PLWStudentProfileCreateView, PLWStudentProfileDetailView,
    PLWSubjectListView, PLWSubjectDetailView,
    PLWExamListView, PLWExamDetailView,
    PLWResultListView, PLWResultCreateView, PLWResultDetailView,
    PLWResultMarksListView, PLWResultMarksDetailView,
    PLWBulkMarksheetGenerateView
)

urlpatterns = [
    path('results/', PLWResultListView.as_view(), name='plw-result-list'),
    path('results/create/', PLWResultCreateView.as_view(), name='plw-result-create'),
    path('results/generate-bulk-pdf/', PLWBulkMarksheetGenerateView.as_view(), name='plw-result-bulk-pdf'),
    path('results/<int:pk>/', PLWResultDetailView.as_view(), name='plw-result-detail'),    
]
