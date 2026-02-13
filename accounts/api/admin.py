"""
Admin APIs for University Management
"""
import logging
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count

from accounts.permissions import IsUniversityAdmin
from accounts.models import UserAccount

logger = logging.getLogger(__name__)


class RegistrationWindowControlView(APIView):
    """
    University Admin API to control registration windows for all profile types.
    
    GET /api/admin/registration-window/
        Query params: profile_type (optional: 'ug', 'pg', 'mca_sem', 'plw')
    
    POST /api/admin/registration-window/
    {
        "profile_type": "ug",           # Required: 'ug', 'pg', 'mca_sem', 'plw'
        "action": "open" | "close",     # Required
        "semester": 3,                  # Optional: specific semester
        "batch": "2024-28",             # Optional: specific batch
        "start_date": "2025-01-01",     # Optional: set start date
        "end_date": "2025-01-31"        # Optional: set end date
    }
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    
    # Model mapping for each profile type
    REGISTRATION_MODELS = {
        'ug': 'ug.models.SemesterRegistration',
        'pg': 'pg.models.PGSemesterRegistration',  # Adjust if different name
        # Add more as needed
    }
    
    def _get_model(self, profile_type):
        """Get the registration model for a profile type"""
        model_path = self.REGISTRATION_MODELS.get(profile_type)
        if not model_path:
            return None
        
        try:
            module_path, model_name = model_path.rsplit('.', 1)
            from importlib import import_module
            module = import_module(module_path)
            return getattr(module, model_name)
        except (ImportError, AttributeError):
            return None
    
    def get(self, request):
        """Get current registration window status summary"""
        profile_type = request.GET.get('profile_type')
        valid_profiles = [choice[0] for choice in UserAccount.PROFILE_TYPE_CHOICES]
        
        result = {
            'success': True,
            'profiles': {}
        }
        
        profiles_to_check = [profile_type] if profile_type else valid_profiles
        
        for pt in profiles_to_check:
            model = self._get_model(pt)
            if model:
                try:
                    summary = model.objects.values('sem', 'is_open').annotate(
                        count=Count('id')
                    ).order_by('sem', 'is_open')
                    
                    result['profiles'][pt] = {
                        'available': True,
                        'summary': list(summary),
                        'total_open': model.objects.filter(is_open=True).count(),
                        'total_closed': model.objects.filter(is_open=False).count(),
                    }
                except Exception as e:
                    result['profiles'][pt] = {
                        'available': False,
                        'error': str(e)
                    }
            else:
                result['profiles'][pt] = {
                    'available': False,
                    'error': 'Registration model not configured'
                }
        
        return Response(result, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Open or close registration windows"""
        profile_type = request.data.get('profile_type')
        action = request.data.get('action')
        semester = request.data.get('semester')
        batch = request.data.get('batch')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        valid_profiles = [choice[0] for choice in UserAccount.PROFILE_TYPE_CHOICES]
        
        # Validation
        if not profile_type:
            return Response(
                {'success': False, 'error': 'profile_type is required', 'valid_options': valid_profiles},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if profile_type not in valid_profiles:
            return Response(
                {'success': False, 'error': f'Invalid profile_type. Must be one of: {valid_profiles}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if action not in ['open', 'close']:
            return Response(
                {'success': False, 'error': 'action must be "open" or "close"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get model
        model = self._get_model(profile_type)
        if not model:
            return Response(
                {'success': False, 'error': f'Registration model not configured for {profile_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Build queryset
            queryset = model.objects.all()
            
            if semester:
                queryset = queryset.filter(sem=semester)
            if batch:
                queryset = queryset.filter(student__batch__name=batch)
            
            # Prepare update data
            update_data = {'is_open': action == 'open'}
            
            if start_date:
                update_data['start_date'] = datetime.fromisoformat(start_date)
            if end_date:
                update_data['end_date'] = datetime.fromisoformat(end_date)
            
            # Perform update
            updated_count = queryset.update(**update_data)
            
            logger.info(f"Registration window {action}ed for {profile_type}: {updated_count} records by user {request.user.id}")
            
            return Response({
                'success': True,
                'profile_type': profile_type,
                'action': action,
                'updated_count': updated_count,
                'filters': {
                    'semester': semester,
                    'batch': batch,
                },
                'message': f"Registration window {'opened' if action == 'open' else 'closed'} for {updated_count} students"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Error controlling registration window: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
