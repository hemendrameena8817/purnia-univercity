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
            'sr_no',
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
        read_only_fields = ['uid', 'created_at', 'updated_at', 'college_details', 'batch_details', 'session_details', 'course_details', 'registration_number', 'sr_no']
    
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
            'sr_no',
            'created_at',
        ]
        read_only_fields = ['uid', 'created_at', 'college_name', 'sr_no']


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
            'sr_no',
        ]
        read_only_fields = ['registration_number', 'is_registration_completed', 'sr_no']

    def validate_dob(self, value):
        """Handle empty string dob sending from frontend as null"""
        if value == "" or value == "null":
            return None
        return value

    def validate(self, data):
        """
        Validate registration data:
        1. Prevent frontend from setting is_registration_completed
        2. Require old_registration_no for non-migrated students
        3. Check for duplicate old_registration_no and clear it from existing records
        """
        # Remove is_registration_completed from data if present (frontend should not set this)
        if 'is_registration_completed' in data:
            data.pop('is_registration_completed')
        
        # Check if migrated_from_other_university is being set to False
        is_migrated = data.get('migrated_from_other_university')
        if is_migrated is not None and is_migrated is False:
            # For non-migrated students, old_registration_no is required
            old_reg_no = data.get('old_registration_no')
            if not old_reg_no:
                # Check if instance already has old_registration_no
                if not (hasattr(self, 'instance') and self.instance and self.instance.old_registration_no):
                    raise serializers.ValidationError({
                        'old_registration_no': 'This field is required for non-migrated students.'
                    })
        
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
        - sr_no is a global university-wide counter for both types
        - is_registration_completed is automatically set based on registration_number.
        """
        # Update instance with validated data first
        updated_instance = super().update(instance, validated_data)
        
        # For non-migrated students, use old_registration_no as registration_number
        # This happens AFTER the update so we have the latest data
        if not updated_instance.migrated_from_other_university and updated_instance.old_registration_no:
            # Only set if registration not already completed
            if not updated_instance.registration_number:
                # Set registration_number from old_registration_no
                updated_instance.registration_number = updated_instance.old_registration_no
                
                # Generate global sr_no (university-wide counter)
                from .models import NewRegistration
                last_global_reg = NewRegistration.objects.filter(
                    sr_no__isnull=False
                ).order_by('-sr_no').only('sr_no').first()
                
                if last_global_reg and last_global_reg.sr_no:
                    updated_instance.sr_no = last_global_reg.sr_no + 1
                else:
                    updated_instance.sr_no = 1
                
                # Mark as completed
                updated_instance.is_registration_completed = True
                updated_instance.save(update_fields=['registration_number', 'sr_no', 'is_registration_completed'])
        else:
            # For other cases, set is_registration_completed based on registration_number
            if updated_instance.registration_number:
                updated_instance.is_registration_completed = True
            else:
                updated_instance.is_registration_completed = False
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
