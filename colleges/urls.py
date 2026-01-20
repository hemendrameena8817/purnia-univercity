from django.urls import path
from .views import (
    CollegeListView,
    CollegeCreateView,
    CollegeDetailView,
    CollegeBulkUploadView,
    CollegeStatsView,
)

urlpatterns = [
    # List all colleges
    path('', CollegeListView.as_view(), name='college-list'),
    
    # Create a new college
    path('create/', CollegeCreateView.as_view(), name='college-create'),
    
    # Bulk upload colleges via CSV
    path('bulk-upload/', CollegeBulkUploadView.as_view(), name='college-bulk-upload'),
    
    # Get college statistics
    path('stats/', CollegeStatsView.as_view(), name='college-stats'),
    
    # Retrieve, update, or delete a specific college (by ID or UID)
    path('<str:identifier>/', CollegeDetailView.as_view(), name='college-detail'),
]
