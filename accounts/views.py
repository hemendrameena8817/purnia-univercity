from dj_rest_auth.views import LoginView as DjRestAuthLoginView
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from captcha.models import CaptchaStore

from .serializers import (
    LoginSerializer, 
    UserProfileSerializer,
    ProfileSerializer,
    CollegeUserCreateSerializer
)
from .permissions import IsUniversityAdmin, IsCollegeUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import UserAccount
from .services import DashboardService
import logging

logger = logging.getLogger(__name__)



class LoginView(DjRestAuthLoginView):
    """
    Unified Login endpoint using dj-rest-auth.
    Authenticates user via username/password and returns user profile.
    """
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=request.data)
        
        # CAPTCHA verification from query parameters
        captcha_key = request.query_params.get('captcha_key')
        captcha_value = request.query_params.get('captcha_value')
        
        if not captcha_key or not captcha_value:
            return Response({"error": "Captcha required for security"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            CaptchaStore.objects.get(hashkey=captcha_key, response=captcha_value.lower()).delete()
        except CaptchaStore.DoesNotExist:
            return Response({"error": "Invalid or expired captcha"}, status=status.HTTP_400_BAD_REQUEST)

        self.serializer.is_valid(raise_exception=True)
        
        self.login()
        response = self.get_response()
        
        # Explicitly ensure refresh token is in response body
        if hasattr(self, 'refresh_token') and self.refresh_token:
            # If dj-rest-auth suppressed it (due to cookie logic), put it back
            response.data['refresh'] = str(self.refresh_token)
        
        return response



class ProfileView(APIView):
    """
    Get current user's profile with UG, PG and college profiles.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = ProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateCollegeUserView(APIView):
    """
    Create a new college user (admin or staff).
    Only university admins and college admins can create college users.
    """
    permission_classes = [IsAuthenticated, IsUniversityAdmin | IsCollegeUser]

    def post(self, request):
        serializer = CollegeUserCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # If requester is college user, check if they are admin and restrict to own college
            if request.user.user_type == "college_user":
                # Check if they have admin role
                if not (hasattr(request.user, 'college_profile') and 
                        request.user.college_profile.role in ['principal', 'admin']):
                    return Response(
                        {"error": "Only college principals or admins can create users."},
                        status=status.HTTP_403_FORBIDDEN
                    )

                user_college = request.user.get_college()
                requested_college_code = serializer.validated_data.get('college_code')
                
                if user_college and user_college.college_code != requested_college_code:
                    return Response(
                        {"error": "You can only create users for your own college."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            user = serializer.save()
            
            return Response(
                UserProfileSerializer(user).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(APIView):
    """
    Common Dashboard API for all student types.
    
    GET /api/accounts/dashboard/?current_profile=ug
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        current_profile = request.GET.get('current_profile')
        valid_profiles = [choice[0] for choice in UserAccount.PROFILE_TYPE_CHOICES]
        
        # Validation
        if not current_profile:
            return Response(
                {'success': False, 'error': 'current_profile parameter is required', 'valid_options': valid_profiles},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if current_profile not in valid_profiles:
            return Response(
                {'success': False, 'error': f'Invalid profile type. Must be one of: {valid_profiles}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get data from service
            data = DashboardService.get_dashboard_data(user, current_profile)
            
            return Response({
                'success': True,
                'profile_type': current_profile,
                'user': {
                    'uid': str(user.uid),
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'email': user.email,
                },
                **data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"Dashboard error for user {user.id}, profile {current_profile}")
            error_msg = f'{current_profile.upper()} profile not found' if 'DoesNotExist' in str(type(e).__name__) else 'An unexpected error occurred'
            status_code = status.HTTP_404_NOT_FOUND if 'DoesNotExist' in str(type(e).__name__) else status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response({'success': False, 'error': error_msg}, status=status_code)
