from django.http import JsonResponse
from django.views import View
from rest_framework.permissions import AllowAny
from .options import GENDER_CHOICES, CASTE_CHOICES


class CommonOptionsView(View):
    """Common options endpoint for use throughout the app"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return all common choices"""
        options = {
            'gender': [
                {'value': choice[0], 'label': choice[1]} 
                for choice in GENDER_CHOICES
            ],
            'caste': [
                {'value': choice[0], 'label': choice[1]} 
                for choice in CASTE_CHOICES
            ]
        }
        return JsonResponse(options)
