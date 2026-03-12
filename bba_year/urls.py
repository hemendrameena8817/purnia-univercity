from django.urls import path
from .views import (
    BBA3rdYearTRView, 
    BBAResultDeclarationPDFView,
    BBAMarksheetPDFView,
    BBAMarksheetJSONView
)

app_name = 'bba_year'

urlpatterns = [
    path('tr/', BBA3rdYearTRView.as_view(), name='bba-3rd-year-tr'),
    path('tr/result-declaration/pdf/', BBAResultDeclarationPDFView.as_view(), name="bba-result-declaration-pdf"),
    path('marksheet/pdf/', BBAMarksheetPDFView.as_view(), name='bba-marksheet-pdf'),
    path('marksheet/json/', BBAMarksheetJSONView.as_view(), name='bba-marksheet-json'),
]
