from django.urls import path
from .views import (
    GrievanceListCreateView,
    GrievanceDetailView,
    GrievanceCommentView,
    GrievanceStatsView,
    GrievanceCategoryListView,
    GrievanceAttachmentUploadView,
)

urlpatterns = [
    # List all grievances or create new one
    path('', GrievanceListCreateView.as_view(), name='grievance-list-create'),
    
    # Upload attachment before creating grievance
    path('upload-attachment/', GrievanceAttachmentUploadView.as_view(), name='grievance-upload-attachment'),
    
    # Get all active categories
    path('categories/', GrievanceCategoryListView.as_view(), name='grievance-categories'),
    
    # Get grievance statistics
    path('stats/', GrievanceStatsView.as_view(), name='grievance-stats'),
    
    # Retrieve or update a specific grievance (by ID or grievance_number)
    path('<str:identifier>/', GrievanceDetailView.as_view(), name='grievance-detail'),
    
    # Add comment to a grievance
    path('<str:identifier>/comments/', GrievanceCommentView.as_view(), name='grievance-comment'),
]
