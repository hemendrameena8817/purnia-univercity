from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Student

User = get_user_model()


class StudentProfileSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='college.name', read_only=True)
    program_name = serializers.CharField(source='program.short_name', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'registration_no', 'roll_no', 'college_name', 'program_name',
            'current_semester', 'session', 'status'
        ]


class StudentCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    username = serializers.CharField()
    
    class Meta:
        model = Student
        fields = [
            'email', 'password', 'username', 'first_name', 'last_name',
            'registration_no', 'roll_no', 'batch', 'father_name', 'mother_name',
            'current_semester', 'session', 'date_of_birth', 'gender', 
            'admission_date', 'enrollment_date', 'address', 'college', 
            'department', 'program'
        ]
        
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
        
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        username = validated_data.pop('username')
        
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            user_type='student',
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        student = Student.objects.create(user=user, **validated_data)
        return student
