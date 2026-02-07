from rest_framework import serializers
from colleges.models import College
from .models import (
    NewRegistration, 
    RegistrationPayment, 
    NewRegistrationCourse, 
    NewRegistrationBatch, 
    NewRegistrationSession
)
from .utils.registration_logic import generate_registration_number


class SessionMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewRegistrationSession
        fields = ['uid', 'name', 'is_active']


class BatchMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewRegistrationBatch
        fields = ['uid', 'name', 'is_active']


class CourseMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewRegistrationCourse
        fields = ['uid', 'name', 'code']


class CollegeMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ['uid', 'name', 'short_name', 'college_code']


class NewRegistrationGetSerializer(serializers.ModelSerializer):
    """
    Serializer for New Registration model.
    """
    # Use nested serializers for detail view (READ)
    college_details = CollegeMinimalSerializer(source='college', read_only=True)
    batch_details = BatchMinimalSerializer(source='batch', read_only=True)
    session_details = SessionMinimalSerializer(source='session', read_only=True)
    course_details = CourseMinimalSerializer(source='course', read_only=True)
    
    class Meta:
        model = NewRegistration
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
            'is_registration_completed',
            'registration_number',
            'last_attended_university',
            'old_registration_no',
            'college_details',
            'course_details',
            'batch_details',
            'session_details',
            'profile_picture',
            'signature',
            'migration_certificate',
            'registration_certificate',
            'json_data',
            'apaar_no',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uid', 'created_at', 'updated_at', 'college_details', 'batch_details', 'session_details', 'course_details', 'registration_number']
    
    def validate_aadhaar_no(self, value):
        """Validate Aadhaar number format"""
        if value and len(value) != 12:
            raise serializers.ValidationError("Aadhaar number must be exactly 12 digits")
        if value and not value.isdigit():
            raise serializers.ValidationError("Aadhaar number must contain only digits")
        return value

    def validate_apaar_no(self, value):
        """Validate Apaar number format"""
        if value and len(value) != 12:
            raise serializers.ValidationError("Apaar number must be exactly 12 digits")
        if value and not value.isdigit():
            raise serializers.ValidationError("Apaar number must contain only digits")
        return value
    
    def validate_mobile_no(self, value):
        """Validate mobile number format"""
        if value and len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits")
        if value and not value.isdigit():
            raise serializers.ValidationError("Mobile number must contain only digits")
        return value


class NewRegistrationListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing New Registrations (minimal fields).
    """
    college_name = serializers.CharField(source='college.name', read_only=True)
    
    class Meta:
        model = NewRegistration
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
            'apaar_no',
            'registration_number',
            'created_at',
        ]
        read_only_fields = ['uid', 'created_at', 'college_name']


class NewRegistrationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating New Registration entries.
    Used for bulk import from Excel.
    """
    college_code = serializers.CharField(write_only=True, required=False)
    college_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = NewRegistration
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
            'old_registration_no',
            'profile_picture',
            'signature',
            'migration_certificate',
            'registration_certificate',
            'college',
            'college_code',
            'college_name',
            'apaar_no',
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


class NewRegistrationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating New Registration entries.
    Handles college, course, batch, and session lookup by UUID (uid).
    Support for profile images and other fields.
    """
    college = serializers.SlugRelatedField(
        slug_field='uid',
        queryset=College.objects.all(),
        required=False
    )
    course = serializers.SlugRelatedField(
        slug_field='uid',
        queryset=NewRegistrationCourse.objects.all(),
        required=False
    )
    batch = serializers.SlugRelatedField(
        slug_field='uid',
        queryset=NewRegistrationBatch.objects.all(),
        required=False
    )
    session = serializers.SlugRelatedField(
        slug_field='uid',
        queryset=NewRegistrationSession.objects.all(),
        required=False
    )
    dob = serializers.DateField(input_formats=['%Y-%m-%d', 'iso-8601'], required=False, allow_null=True)

    class Meta:
        model = NewRegistration
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
            'apaar_no',
            'email',
            'migration_submitted',
            'migrated_from_other_university',
            'last_attended_university',
            'old_registration_no',
            'is_registration_completed',
            'profile_picture',
            'signature',
            'migration_certificate',
            'registration_certificate',
            'college',
            'json_data',
            'registration_number',
        ]
        read_only_fields = ['registration_number', 'is_registration_completed']

    def validate_dob(self, value):
        """Handle empty string dob sending from frontend as null"""
        if value == "" or value == "null":
            return None
        return value

    def validate(self, data):
        """
        Prevent frontend from setting is_registration_completed.
        This field is read-only and set automatically based on registration_number.
        """
        # Remove is_registration_completed from data if present (frontend should not set this)
        if 'is_registration_completed' in data:
            data.pop('is_registration_completed')
        
        return data

    def validate_aadhaar_no(self, value):
        if value and len(value) != 12:
            raise serializers.ValidationError("Aadhaar number must be exactly 12 digits")
        if value and not value.isdigit():
            raise serializers.ValidationError("Aadhaar number must contain only digits")
        return value

    def validate_apaar_no(self, value):
        if value and len(value) != 12:
            raise serializers.ValidationError("Apaar number must be exactly 12 digits")
        if value and not value.isdigit():
            raise serializers.ValidationError("Apaar number must contain only digits")
        return value

    def update(self, instance, validated_data):
        """
        Custom update to handle registration number generation.
        - For non-migrated students: Use old_registration_no as registration_number
        - For migrated students: Registration number generated after payment
        - is_registration_completed is automatically set based on registration_number.
        """
        # Check if student is NOT migrated and has old_registration_no
        is_migrated = validated_data.get('migrated_from_other_university', instance.migrated_from_other_university)
        old_reg_no = validated_data.get('old_registration_no', instance.old_registration_no)
        
        # For non-migrated students, set registration_number from old_registration_no
        if not is_migrated and old_reg_no and not instance.registration_number:
            instance.registration_number = old_reg_no
            instance.save(update_fields=['registration_number'])
        
        # Update instance with validated data
        updated_instance = super().update(instance, validated_data)
        
        # Automatically set is_registration_completed based on registration_number
        # Only mark as completed if registration_number exists
        if updated_instance.registration_number:
            updated_instance.is_registration_completed = True
        else:
            updated_instance.is_registration_completed = False
        
        # Save the updated completion status
        updated_instance.save(update_fields=['is_registration_completed'])
        
        return updated_instance


class RegistrationPaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Registration Payment records.
    """
    class Meta:
        model = RegistrationPayment
        fields = [
            'order_id',
            'tracking_id',
            'amount',
            'payment_status',
            'payment_mode',
            'bank_ref_no',
            'created_at'
        ]
        read_only_fields = ['created_at']
