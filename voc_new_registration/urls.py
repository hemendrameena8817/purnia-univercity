from django.urls import path
from .views import (
    VocNewRegistrationListView,
    VocNewRegistrationCreateView,
    VocNewRegistrationDetailView,
    VocNewRegistrationBulkCreateView,
)

urlpatterns = [
    # List all registrations
    path('', VocNewRegistrationListView.as_view(), name='voc-registration-list'),
    
    # Create a new registration
    path('create/', VocNewRegistrationCreateView.as_view(), name='voc-registration-create'),
    
    # Bulk create
    path('bulk-create/', VocNewRegistrationBulkCreateView.as_view(), name='voc-registration-bulk-create'),
    
    # Retrieve, update, delete (by Aadhaar)
    path('<str:aadhaar_no>/', VocNewRegistrationDetailView.as_view(), name='voc-registration-detail'),
]
