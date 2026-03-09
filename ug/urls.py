"""
UG App URL Configuration for Semester Registration
"""
from django.urls import path
from ug.api.semester_registration import (
    RegistrationEligibilityView,
    AvailableCoursesView,
    SubmitRegistrationView,
    RegistrationCardView
)
from ug.api.cia_marks import (
    UGDepartmentListView,
    CIAStudentListView,
    CIAMarksSaveView,
)
from ug.api.payments import (
    UGPaymentInfoView,
    UGInitiatePaymentView,
    UGPaymentResponseView,
    UGRegistrationStatusView,
)

app_name = 'ug'

urlpatterns = [
    # Semester Registration APIs (Student)
    path(
        'semester-registration/eligibility/',
        RegistrationEligibilityView.as_view(),
        name='registration-eligibility'
    ),
    path(
        'semester-registration/available-courses/',
        AvailableCoursesView.as_view(),
        name='available-courses'
    ),
    path(
        'semester-registration/submit/',
        SubmitRegistrationView.as_view(),
        name='submit-registration'
    ),
    path(
        'semester-registration/card/',
        RegistrationCardView.as_view(),
        name='registration-card'
    ),

    # CIA Marks Entry APIs (College)
    path(
        'cia/departments/',
        UGDepartmentListView.as_view(),
        name='cia-departments'
    ),
    path(
        'cia/students/',
        CIAStudentListView.as_view(),
        name='cia-students'
    ),
    path(
        'cia/marks/',
        CIAMarksSaveView.as_view(),
        name='cia-marks-save'
    ),

    # Payment (CC Avenue)
    path('payment-info/', UGPaymentInfoView.as_view(), name='ug-payment-info'),
    path('initiate-payment/', UGInitiatePaymentView.as_view(), name='ug-initiate-payment'),
    path('payment-response/', UGPaymentResponseView.as_view(), name='ug-payment-response'),
    
    # Registration status (public — used after CC Avenue redirect)
    path('<uuid:uid>/status/', UGRegistrationStatusView.as_view(), name='ug-registration-status'),
]
