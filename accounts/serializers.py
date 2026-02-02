from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from .models import CollegeUserProfile
from .utils.user_profile import get_ug_profile_data, get_pg_profile_data, get_current_profile as get_user_current_profile

User = get_user_model()




class LoginSerializer(serializers.Serializer):
    """
    Login serializer compatible with dj-rest-auth.
    """
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'), 
                                username=username, password=password)
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


# class LoginUserSerializer(serializers.ModelSerializer):
#     """
#     Simple user serializer for login response - NO profiles.
#     """
#     class Meta:
#         model = User
#         fields = [
#             'uid', 'email', 'username', 'first_name', 'last_name',
#             'phone', 'user_type', 'is_verified', 'is_active', 'created_at'
#         ]
#         read_only_fields = ['uid', 'email', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer with UG, PG student profiles and college profile.
    Optimized for login response with minimal queries.
    """

    
    class Meta:
        model = User
        fields = [
            'uid', 'email', 'username', 'first_name', 'last_name',
            'phone', 'user_type', 'current_profile', 'is_verified', 'is_active', 
            'created_at'
        ]
        read_only_fields = ['uid', 'email', 'created_at']


class CollegeUserProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True)
    college_code = serializers.CharField(source='college.college_code', read_only=True)
    
    class Meta:
        model = CollegeUserProfile
        fields = [
            'uid', 'user_email', 'user_name', 'college_name', 'college_code',
            'designation', 'can_manage_students', 'can_manage_marks',
            'can_manage_results', 'can_verify_data', 'can_approve_certificates',
            'is_active', 'created_at'
        ]
        read_only_fields = ['uid', 'created_at']

class ProfileSerializer(serializers.ModelSerializer):
    """
    Profile serializer with UG, PG student profiles and college profile.
    Used for /profile/ endpoint.
    """
    college_profile = CollegeUserProfileSerializer(read_only=True)
    ug_profile = serializers.SerializerMethodField()
    pg_profile = serializers.SerializerMethodField()
    calculated_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'uid', 'email', 'username', 'first_name', 'last_name',
            'phone', 'user_type', 'current_profile', 'is_verified', 'is_active', 
            'created_at', 'college_profile', 'ug_profile', 'pg_profile', 'calculated_profile'
        ]
        read_only_fields = ['uid', 'email', 'created_at']


    def get_ug_profile(self, obj):
        """Get UG student profile data."""
        return get_ug_profile_data(obj)

    def get_pg_profile(self, obj):
        """Get PG student profile data."""
        return get_pg_profile_data(obj)

    def get_calculated_profile(self, obj):
        """Get current course name (UG/PG) calculation."""
        return get_user_current_profile(obj)


class CollegeUserCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new college user.
    """
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    college_code = serializers.CharField(max_length=50)
    designation = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_college_code(self, value):
        from colleges.models import College
        if not College.objects.filter(college_code=value).exists():
            raise serializers.ValidationError(f"College with code '{value}' does not exist.")
        return value

    def create(self, validated_data):
        from colleges.models import College
        
        # Create user account
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            user_type="college_user",  # Simplified type
        )
        
        # Create college profile
        college = College.objects.get(college_code=validated_data['college_code'])
        
        college_profile = CollegeUserProfile.objects.create(
            user=user,
            college=college,
            designation=validated_data.get('designation', ''),
        )
        
        return user
