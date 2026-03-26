"""
UG App URL Configuration for Semester Registration
"""
from django.urls import path
from ug.api.semester_registration import (
    RegistrationEligibilityView,
    AvailableCoursesView,
    SubmitRegistrationView,
    RegistrationCardView,
    UGExamRegistrationDetailView,
    UGStudentUploadView
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
    UGExamRegistrationCardPDFView,
)
from .views import (
    UGAdmitCardPDFView, UGBulkAdmitCardPDFView, UGAdmitCardTestView, 
    UGRollSheetPDFView, UGExamListView
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
    path(
        'exam-registration/',
        UGExamRegistrationDetailView.as_view(),
        name='ug-exam-registration'
    ),
    path(
        'student-image-upload/',
        UGStudentUploadView.as_view(),
        name='ug-student-image-upload'
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

    # Exam Registration Card
    path('exam-registration/card/', UGExamRegistrationCardPDFView.as_view(), name='ug-exam-registration-card'),

    # Admit Card APIs
    path('admit-card/pdf/', UGAdmitCardPDFView.as_view(), name='ug-admit-card-pdf'),
    path('bulk-admit-card/pdf/', UGBulkAdmitCardPDFView.as_view(), name='ug-bulk-admit-card-pdf'),
    path('admit-card/test/', UGAdmitCardTestView.as_view(), name='ug-admit-card-test'),
    # Roll Sheet
    path('roll-sheet/pdf/', UGRollSheetPDFView.as_view(), name='ug-roll-sheet-pdf'),
    # UG Exams List
    path('exams/', UGExamListView.as_view(), name='ug-exam-list'),
]
