from django.urls import path
from .views import (
    NewRegistrationListView,
    NewRegistrationCreateView,
    NewRegistrationDetailView,
    NewRegistrationBulkCreateView,
    RegistrationOptionsView,
    InitiatePaymentView,
    PaymentResponseView,
    RegistrationStatusView,
    CaptchaView,
    PaymentInfoView,
    CheckRegistrationWindowView
)

urlpatterns = [
    # Captcha generation
    path('captcha/', CaptchaView.as_view(), name='registration-captcha'),
    
    # Check registration window
    path('check-window/', CheckRegistrationWindowView.as_view(), name='check-registration-window'),

    # List all registrations
    path('', NewRegistrationListView.as_view(), name='registration-list'),
    
    # Registration options (gender, caste, lookups)
    path('options/', RegistrationOptionsView.as_view(), name='registration-options'),
    
    # Create a new registration
    path('create/', NewRegistrationCreateView.as_view(), name='registration-create'),
    
    # Bulk create
    path('bulk-create/', NewRegistrationBulkCreateView.as_view(), name='registration-bulk-create'),
    
    # Payment Info (Pre-check)
    path('payment-info/', PaymentInfoView.as_view(), name='registration-payment-info'),

    # Payment response (CC Avenue redirect)
    path('payment-response/', PaymentResponseView.as_view(), name='registration-payment-response'),

    # Registration status check
    path('<uuid:uid>/status/', RegistrationStatusView.as_view(), name='registration-status'),

    # Payment initiation
    path('<str:aadhaar_no>/initiate-payment/', InitiatePaymentView.as_view(), name='registration-payment-initiate'),

    # Retrieve, Update, Delete (by Aadhaar) - MUST BE LAST
    path('<str:aadhaar_no>/', NewRegistrationDetailView.as_view(), name='registration-detail'),
]
