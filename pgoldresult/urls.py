from django.urls import path
from .views import PGOldResultAPIView, PGResultCalculatorView, generate_marksheet_pdf, PGOldStudentProfileAPIView

urlpatterns = [
    path('result/', PGOldResultAPIView.as_view(), name='pg_old_result_api'),
    path('calculate/', PGResultCalculatorView.as_view(), name='pg_result_calculator'),
    path('generate-pdf/', generate_marksheet_pdf, name='pg_generate_marksheet_pdf'),
    path('profile/', PGOldStudentProfileAPIView.as_view(), name='pg_student_profile'),
]
