from django.urls import path
from .views import OMRUploadView, OMRBulkUploadView, OMRDetailView, OMRListView, OMRUpdateView

urlpatterns = [
    path("upload/", OMRUploadView.as_view(), name="omr-upload"),
    path("bulk-upload/", OMRBulkUploadView.as_view(), name="omr-bulk-upload"),
    path("<uuid:uid>/update/", OMRUpdateView.as_view(), name="omr-update"),
    path("<uuid:uid>/", OMRDetailView.as_view(), name="omr-detail"),
    path("", OMRListView.as_view(), name="omr-list"),
]
