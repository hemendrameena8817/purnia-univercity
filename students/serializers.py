from rest_framework import serializers
from .models import Student
from accounts.models import UserAccount


class StudentCreateSerializer(serializers.ModelSerializer):
    # UserAccount fields
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, min_length=6, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta:
        model = Student
        fields = [
            # User fields
            'email', 'password',

            # Student personal info
            'first_name', 'last_name', 'json_data',
            'registration_no', 'address', 'admission_date',
            'date_of_birth', 'gender', 'enrollment_date',
            'enrollment_no', 'roll_no', 'batch',

            # Family info
            'father_name', 'mother_name',

            # Academic info
            'current_semester', 'session', 'status',

            # Relations
            'college', 'department', 'program',

            # Documents
            'profile_image', 'signature'
        ]

    def validate_email(self, value):
        if UserAccount.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')

        # Generate username
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while UserAccount.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create UserAccount
        user = UserAccount.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type='student'
        )

        # Create Student
        student = Student.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            **validated_data
        )

        return student
