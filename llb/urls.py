from django.urls import path
from . import views

urlpatterns = [
    path('results/generate-bulk-pdf/', views.LLBBulkMarksheetGenerateView.as_view(), name='llb-result-bulk-pdf'),
    path('results/<str:registration_no>/pdf/', views.LLBResultPDFView.as_view(), name='llb-result-pdf'),
]
