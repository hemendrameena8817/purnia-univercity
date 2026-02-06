"""
UG App URL Configuration for Semester Registration
"""
from django.urls import path
from ug.api.semester_registration import (
    RegistrationEligibilityView,
    AvailableCoursesView,
    SubmitRegistrationView
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
]
