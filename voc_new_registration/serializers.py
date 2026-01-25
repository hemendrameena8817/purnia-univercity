from rest_framework import serializers
from .models import VocNewRegistration
from colleges.models import College


from academics.models import Course, Batch, Session


class SessionMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['uid', 'name', 'is_current']


class BatchMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['uid', 'name', 'is_active']


class CourseMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['uid', 'name', 'code']


class CollegeMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ['uid', 'name', 'short_name', 'college_code']


class VocNewRegistrationGetSerializer(serializers.ModelSerializer):
    """
    Serializer for VOC New Registration model.
    """
    # Use nested serializers for detail view (READ)
    college_details = CollegeMinimalSerializer(source='college', read_only=True)
    batch_details = BatchMinimalSerializer(source='batch', read_only=True)
    session_details = SessionMinimalSerializer(source='session', read_only=True)
    course_details = CourseMinimalSerializer(source='course', read_only=True)
    
    class Meta:
        model = VocNewRegistration
        fields = [
            'uid',
            'student_name',
            'student_name_hindi',
            'father_name',
            'mother_name',
            'gender',
            'caste',
            'dob',
            'mobile_no',
            'aadhaar_no',
            'email',
            'migration_submitted',
            'migrated_from_other_university',
            'is_account_created',
            'is_registration_completed',
            'last_attended_university',
            'college_details',
            'course_details',
            'batch_details',
            'session_details',
            'profile_picture',
            'signature',
            'json_data',
            'apaar_no',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uid', 'created_at', 'updated_at', 'college_details', 'batch_details', 'session_details', 'course_details']
    
    def validate_aadhaar_no(self, value):
        """Validate Aadhaar number format"""
        if value and len(value) != 12:
            raise serializers.ValidationError("Aadhaar number must be exactly 12 digits")
        if value and not value.isdigit():
            raise serializers.ValidationError("Aadhaar number must contain only digits")
        return value
    
    def validate_mobile_no(self, value):
        """Validate mobile number format"""
        if value and len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits")
        if value and not value.isdigit():
            raise serializers.ValidationError("Mobile number must contain only digits")
        return value


class VocNewRegistrationListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing VOC New Registrations (minimal fields).
    """
    college_name = serializers.CharField(source='college.name', read_only=True)
    
    class Meta:
        model = VocNewRegistration
        fields = [
            'uid',
            'student_name',
            'course',
            'batch',
            'gender',
            'caste',
            'dob',
            'mobile_no',
            'email',
            'college_name',
            'migration_submitted',
            'created_at',
        ]
        read_only_fields = ['uid', 'created_at', 'college_name']


class VocNewRegistrationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating VOC New Registration entries.
    Used for bulk import from Excel.
    """
    college_code = serializers.CharField(write_only=True, required=False)
    college_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = VocNewRegistration
        fields = [
            'student_name',
            'student_name_hindi',
            'father_name',
            'mother_name',
            'course',
            'batch',
            'session',
            'gender',
            'caste',
            'dob',
            'mobile_no',
            'aadhaar_no',
            'email',
            'migration_submitted',
            'migrated_from_other_university',
            'last_attended_university',
            'profile_picture',
            'signature',
            'college',
            'college_code',
            'college_name',
            'json_data',
        ]
    
    def create(self, validated_data):
        """
        Create a new registration entry.
        Handle college lookup by code or name if college ID not provided.
        """
        college_code = validated_data.pop('college_code', None)
        college_name = validated_data.pop('college_name', None)
        
        # If college not directly provided, try to find it by code or name
        if 'college' not in validated_data:
            found_college = None
            if college_code:
                try:
                    found_college = College.objects.get(college_code=college_code)
                except College.DoesNotExist:
                    pass
            elif college_name:
                try:
                    found_college = College.objects.get(name=college_name)
                except (College.DoesNotExist, College.MultipleObjectsReturned):
                    pass
            
            validated_data['college'] = found_college
            # Note: college is optional now, so None is fine if not required by API logic
        
        return super().create(validated_data)
