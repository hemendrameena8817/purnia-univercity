from django.urls import path
from .views import (
    VocNewRegistrationListView,
    VocNewRegistrationCreateView,
    VocNewRegistrationDetailView,
    VocNewRegistrationBulkCreateView,
    VocRegistrationOptionsView,
)

urlpatterns = [
    # List all registrations
    path('', VocNewRegistrationListView.as_view(), name='voc-registration-list'),
    
    # Registration options (gender, caste)
    path('options/', VocRegistrationOptionsView.as_view(), name='voc-registration-options'),
    
    # Create a new registration
    path('create/', VocNewRegistrationCreateView.as_view(), name='voc-registration-create'),
    
    # Bulk create
    path('bulk-create/', VocNewRegistrationBulkCreateView.as_view(), name='voc-registration-bulk-create'),
    
    # Retrieve, Update, Delete (by Aadhaar)
    path('<str:aadhaar_no>/', VocNewRegistrationDetailView.as_view(), name='voc-registration-detail'),
    
    
]
