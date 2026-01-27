from rest_framework import serializers
from .models import PGStudentProfile, PGDepartment, PGDegree, PGProgram
from colleges.models import College


class PGCollegeSerializer(serializers.ModelSerializer):
    """Lightweight College serializer for nested use."""
    class Meta:
        model = College
        fields = ['uid', 'name', 'short_name', 'college_code']


class PGDepartmentSerializer(serializers.ModelSerializer):
    """Lightweight Department serializer for nested use."""
    class Meta:
        model = PGDepartment
        fields = ['uid', 'name', 'code']


class PGDegreeSerializer(serializers.ModelSerializer):
    """Lightweight Degree serializer for nested use."""
    class Meta:
        model = PGDegree
        fields = ['uid', 'name', 'short_name', 'total_semesters', 'total_years']


class PGProgramSerializer(serializers.ModelSerializer):
    """Lightweight Program serializer for nested use."""
    class Meta:
        model = PGProgram
        fields = ['uid', 'name', 'short_name']


class PGStudentProfileSerializer(serializers.ModelSerializer):
    """
    PG Student Profile serializer for login response.
    Optimized with nested serializers for related objects.
    """
    department = PGDepartmentSerializer(read_only=True)
    degree = PGDegreeSerializer(read_only=True)
    program = PGProgramSerializer(read_only=True)
    college = PGCollegeSerializer(read_only=True)

    class Meta:
        model = PGStudentProfile
        fields = [
            'uid',
            'registration_no', 'roll_no',
            'father_name', 'mother_name',
            'date_of_birth', 'gender', 'caste',
            'mobile_no', 'aadhar_no', 'address',
            'college',
            'department', 'degree', 'program',
            'status', 'session', 'batch', 'is_active'
        ]
        read_only_fields = ['uid']
