from django.urls import path
from .views import (
    PLWBulkMarksheetGenerateView,
    PLWResultPDFView
)

urlpatterns = [
    path('results/generate-bulk-pdf/', PLWBulkMarksheetGenerateView.as_view(), name='plw-result-bulk-pdf'),
    path('results/<str:registration_no>/pdf/', PLWResultPDFView.as_view(), name='plw-result-pdf'),
]
