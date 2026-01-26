from rest_framework import serializers
from .models import PGStudentProfile, PGDepartment, PGDegree, PGProgram


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
    college_name = serializers.CharField(source='college.name', read_only=True, allow_null=True)
    college_code = serializers.CharField(source='college.college_code', read_only=True, allow_null=True)

    class Meta:
        model = PGStudentProfile
        fields = [
            'uid',
            'registration_no', 'roll_no',
            'father_name', 'mother_name',
            'date_of_birth', 'gender', 'caste',
            'mobile_no', 'aadhar_no', 'address',
            'college_name', 'college_code',
            'department', 'degree', 'program',
            'status', 'session', 'batch'
        ]
        read_only_fields = ['uid']
