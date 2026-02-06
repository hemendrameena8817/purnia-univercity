from django.urls import path
from .views import PGCIAMarksEntryView

urlpatterns = [
    path('cia-marks/entry/', PGCIAMarksEntryView.as_view(), name='cia-marks-entry'),
]
