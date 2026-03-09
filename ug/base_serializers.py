from rest_framework import serializers
from .models import UGStudentProfile, UGDepartment, UGDegree, UGProgram
from colleges.models import College


class UGCollegeSerializer(serializers.ModelSerializer):
    """Lightweight College serializer for nested use."""
    class Meta:
        model = College
        fields = ['uid', 'name', 'short_name', 'college_code']


class UGDepartmentSerializer(serializers.ModelSerializer):
    """Lightweight Department serializer for nested use."""
    class Meta:
        model = UGDepartment
        fields = ['uid', 'name', 'code']


class UGDegreeSerializer(serializers.ModelSerializer):
    """Lightweight Degree serializer for nested use."""
    class Meta:
        model = UGDegree
        fields = ['uid', 'name', 'short_name', 'total_semesters', 'total_years']


class UGProgramSerializer(serializers.ModelSerializer):
    """Lightweight Program serializer for nested use."""
    class Meta:
        model = UGProgram
        fields = ['uid', 'name', 'short_name']


class UGStudentProfileSerializer(serializers.ModelSerializer):
    """
    UG Student Profile serializer for login response.
    Optimized with nested serializers for related objects.
    """
    department = UGDepartmentSerializer(read_only=True)
    degree = UGDegreeSerializer(read_only=True)
    program = UGProgramSerializer(read_only=True)
    college = UGCollegeSerializer(read_only=True)
    batch = serializers.CharField(source='batch.name', read_only=True)
    date_of_birth = serializers.DateField(read_only=True, format='%d-%m-%y')

    class Meta:
        model = UGStudentProfile
        fields = [
            'uid',
            'registration_no', 'roll_no','first_name',
            'father_name', 'mother_name',
            'date_of_birth', 'gender', 'caste',
            'mobile_no', 'aadhar_no', 'address',
            'college', 'profile_image', 'signature',
            'department', 'degree', 'program',
            'status', 'session', 'batch', 'is_active'
        ]
        read_only_fields = ['uid']
    