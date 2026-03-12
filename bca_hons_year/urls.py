from django.urls import path
from .views import (
    BCAHons3rdYearTRView, 
    BCAHonsResultDeclarationPDFView,
    BCAHons3rdYearStaticTRView,
    BCAHonsMarksheetPDFView,
    BCAHonsMarksheetJSONView
)

app_name = 'bca_hons_year'

urlpatterns = [
    path('tr/', BCAHons3rdYearTRView.as_view(), name='bca-hons-3rd-year-tr'),
    path('tr/static/', BCAHons3rdYearStaticTRView.as_view(), name='bca-hons-3rd-year-static-tr'),
    path('tr/result-declaration/pdf/', BCAHonsResultDeclarationPDFView.as_view(), name='bca-hons-result-declaration-pdf'),
    path('marksheet/pdf/', BCAHonsMarksheetPDFView.as_view(), name='bca-hons-marksheet-pdf'),
    path('marksheet/json/', BCAHonsMarksheetJSONView.as_view(), name='bca-hons-marksheet-json'),
]
