from dj_rest_auth.views import LoginView as DjRestAuthLoginView
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from .serializers import (
    LoginSerializer, 
    UserProfileSerializer,
    CollegeUserCreateSerializer
)
from .permissions import IsUniversityAdmin, IsCollegeUser




class LoginView(DjRestAuthLoginView):
    """
    Unified Login endpoint using dj-rest-auth.
    Authenticates user via username/password and returns user profile.
    """
    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=request.data)
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
    Get current user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
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
