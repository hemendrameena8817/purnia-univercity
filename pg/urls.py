from django.urls import path
from .views import (
    PGCIAMarksEntryView, 
    PGCollegeStudentsView, 
    PGDepartmentDropdownView,
    PGBatchDropdownView,
    PGSubjectDropdownView
)

urlpatterns = [
    path('cia-marks/entry/', PGCIAMarksEntryView.as_view(), name='cia-marks-entry'),
    path('college-students/', PGCollegeStudentsView.as_view(), name='college-students'),
    path('departments/', PGDepartmentDropdownView.as_view(), name='departments'),
    path('batches/', PGBatchDropdownView.as_view(), name='batches'),
    path('subjects/', PGSubjectDropdownView.as_view(), name='subjects'),
]
