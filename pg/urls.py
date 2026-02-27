from django.urls import path
from .views import (
    PGCIAMarksEntryView, 
    PGCollegeStudentsView, 
    PGDepartmentDropdownView,
    PGSubjectDropdownView,
    PGStudentFilterView,
    PGExamRegistrationDetailView,
    PGAdmitCardPDFView,
    PGPaymentInfoView,
    PGInitiatePaymentView,
    PGPaymentResponseView,
    PGStudentUploadView,
    PGRegistrationStatusView,
    PGRegistrationCardPDFView,
    PGRollSheetPDFView,
)

urlpatterns = [
    path('cia-marks/entry/', PGCIAMarksEntryView.as_view(), name='cia-marks-entry'),
    path('college-students/', PGCollegeStudentsView.as_view(), name='college-students'),
    path('departments/', PGDepartmentDropdownView.as_view(), name='departments'),
    path('subjects/', PGSubjectDropdownView.as_view(), name='subjects'),
    path('students/filter/', PGStudentFilterView.as_view(), name='pg-student-filter'),
    path('exam-registration/', PGExamRegistrationDetailView.as_view(), name='pg-exam-registration'),
    path('admit-card/', PGAdmitCardPDFView.as_view(), name='pg-admit-card'),
    path('registration-card/', PGRegistrationCardPDFView.as_view(), name='pg-registration-card'),
    # Payment (CC Avenue)
    path('payment-info/', PGPaymentInfoView.as_view(), name='pg-payment-info'),
    path('initiate-payment/', PGInitiatePaymentView.as_view(), name='pg-initiate-payment'),
    path('payment-response/', PGPaymentResponseView.as_view(), name='pg-payment-response'),
    #inside thsi api ther is uploading profile and signature of student
    path('student-image-upload/', PGStudentUploadView.as_view(), name='pg-student-image-upload'),
    # Registration status (public — used after CC Avenue redirect)
    path('<uuid:uid>/status/', PGRegistrationStatusView.as_view(), name='pg-registration-status'),
    path('roll-sheet/pdf/', PGRollSheetPDFView.as_view(), name='pg-roll-sheet-pdf'),
]
