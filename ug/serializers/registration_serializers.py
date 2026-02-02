"""
Semester Registration Serializers
"""
from rest_framework import serializers


class CourseOptionSerializer(serializers.Serializer):
    """Serializer for course option"""
    code = serializers.CharField()
    name = serializers.CharField()
    course_type = serializers.CharField()
    credit = serializers.IntegerField()
    marks = serializers.FloatField()
    department = serializers.CharField(required=False, allow_null=True)
    auto_assigned = serializers.BooleanField(required=False, default=False)


class CourseGroupSerializer(serializers.Serializer):
    """Serializer for a group of courses"""
    type = serializers.CharField()
    description = serializers.CharField()
    required_count = serializers.IntegerField()
    auto_assigned = serializers.BooleanField()
    options = CourseOptionSerializer(many=True, required=False)
    selected = CourseOptionSerializer(many=True, required=False)


class RegistrationWindowSerializer(serializers.Serializer):
    """Serializer for registration window details"""
    start_date = serializers.CharField(allow_null=True)
    end_date = serializers.CharField(allow_null=True)
    is_open = serializers.BooleanField()


class EligibilityResponseSerializer(serializers.Serializer):
    """Serializer for eligibility check response"""
    eligible = serializers.BooleanField()
    current_semester = serializers.IntegerField()
    next_semester = serializers.IntegerField()
    semester_result = serializers.CharField(required=False, allow_null=True)
    registration_open = serializers.BooleanField(required=False)
    registration_window = RegistrationWindowSerializer(required=False, allow_null=True)
    message = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)


class AvailableCoursesResponseSerializer(serializers.Serializer):
    """Serializer for available courses response"""
    semester = serializers.CharField()
    session = serializers.CharField()
    courses = serializers.DictField(child=CourseGroupSerializer())


class CourseSelectionRequestSerializer(serializers.Serializer):
    """Serializer for course selection request"""
    semester = serializers.CharField()
    session = serializers.CharField()
    selections = serializers.DictField()
    
    def validate_selections(self, value):
        """Validate selections structure"""
        if not value:
            raise serializers.ValidationError("Selections cannot be empty")
        
        # Validate that each selection is a list
        for key, val in value.items():
            if not isinstance(val, list):
                raise serializers.ValidationError(f"{key} must be a list of course codes")
        
        return value


class RegisteredCourseSerializer(serializers.Serializer):
    """Serializer for a registered course"""
    code = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    auto_assigned = serializers.BooleanField()


class RegistrationResponseSerializer(serializers.Serializer):
    """Serializer for registration submission response"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    registered_courses = RegisteredCourseSerializer(many=True)
    total_credits = serializers.IntegerField()
    total_courses = serializers.IntegerField()
