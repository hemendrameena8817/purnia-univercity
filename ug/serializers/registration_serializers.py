"""
Semester Registration Serializers
"""
from rest_framework import serializers

from ug.models import StudentCourseAssessment, ExamRegistration
from ug.base_serializers import UGStudentProfileSerializer



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


class SubmitRegistrationSerializer(serializers.Serializer):
    """
    Handles multipart/form-data for semester registration
    """
    semester = serializers.CharField(required=True)
    assessment_uids = serializers.JSONField(required=True)
    profile_image = serializers.ImageField(required=True)
    signature = serializers.ImageField(required=True)
    gender = serializers.CharField(required=True)
    
    def validate_assessment_uids(self, value):
        if not value:
             raise serializers.ValidationError("Must be a non-empty list of UIDs.")
        if not isinstance(value, list):
             raise serializers.ValidationError("Must be a list.")
        return value


class CourseSelectionRequestSerializer(serializers.Serializer):
    semester = serializers.CharField()
    session = serializers.CharField()
    selections = serializers.DictField()
    profile_image = serializers.ImageField(required=True)
    signature = serializers.ImageField(required=True)
    
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
    profile_image = serializers.CharField(required=False, allow_null=True)
    signature = serializers.CharField(required=False, allow_null=True)


class AssessmentDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for assessment details in college students view.
    """
    class Meta:
        model = StudentCourseAssessment
        fields = [
            'uid', 'semester', 'session', 'paper_code', 
            'course_name'
        ]


class UGExamRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for UG Exam Registration.
    Includes student profile and assessment details.
    """
    student = UGStudentProfileSerializer(read_only=True)
    assessments = serializers.SerializerMethodField()

    class Meta:
        model = ExamRegistration
        fields = [
            'uid', 'student', 'sem', 'session', 'exam_type', 
            'status', 'fees', 'is_open', 'assessments'
        ]

    def get_assessments(self, obj):
        """
        Fetch UG Student Course Assessments matching the exact registration logic
        """
        sem_str = str(obj.sem) if obj.sem else ""

        # Using similar logic as used in printing the registration card
        semester_num = obj.sem
        suffixes = {1: 'ST', 2: 'ND', 3: 'RD'}
        suffix = suffixes.get(semester_num, 'TH') if isinstance(semester_num, int) else ""
        semester_text = f"{semester_num}{suffix}" if isinstance(semester_num, int) else str(semester_num).upper()

        exam_type = (obj.exam_type or 'REGULAR').upper()

        assessments = StudentCourseAssessment.objects.filter(
            student=obj.student,
            semester__in=[str(semester_num), semester_text],
            session=obj.session,
            exam_type=exam_type,
            label__startswith='ESE'
        ).order_by('course_type', 'paper_code')

        # Deduplicate so paper does not repeat if it has both ESE-Theory and ESE-Practical
        seen_codes = set()
        unique_assessments = []
        for a in assessments:
            code = a.paper_code or a.course_code or ''
            if code not in seen_codes:
                seen_codes.add(code)
                unique_assessments.append(a)

        return AssessmentDetailSerializer(unique_assessments, many=True).data
