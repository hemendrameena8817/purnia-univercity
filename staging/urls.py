from django.urls import path
from .views import UGSemResultUpdateView

urlpatterns = [
    path('ug-result/update/', UGSemResultUpdateView.as_view(), name='ug-result-update'),
]
