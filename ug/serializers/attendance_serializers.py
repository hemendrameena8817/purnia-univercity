from rest_framework import serializers
from ..models import UGStudentProfile, StudentCourseAssessment, UGExam
from colleges.models import College

class UGAttendanceStudentSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for each student's ESE assessment entry
    returned in the attendance list API (GET /student-attendance/list/).
    """
    assessment_uid  = serializers.UUIDField(source='uid', read_only=True)
    name            = serializers.SerializerMethodField()
    roll_no         = serializers.SerializerMethodField()
    registration_no = serializers.SerializerMethodField()
    photo_url       = serializers.SerializerMethodField()
    student_uid     = serializers.UUIDField(source='student.uid', read_only=True)
    is_absent       = serializers.BooleanField(source='ind_is_absent', read_only=True)

    class Meta:
        model  = StudentCourseAssessment
        fields = [
            'assessment_uid',
            'student_uid',
            'name',
            'roll_no',
            'registration_no',
            'photo_url',
            'course_code',
            'course_name',
            'is_absent',
        ]

    def get_name(self, obj):
        if not obj.student:
            return '-'
        return f"{obj.student.first_name} {obj.student.last_name or ''}".strip()

    def get_roll_no(self, obj):
        return obj.student.roll_no or 'N/A' if obj.student else 'N/A'

    def get_registration_no(self, obj):
        return obj.student.registration_no or 'N/A' if obj.student else 'N/A'

    def get_photo_url(self, obj):
        if obj.student and obj.student.profile_image:
            try:
                return obj.student.profile_image.url
            except Exception:
                return None
        return None


class UGAttendanceMarkSerializer(serializers.Serializer):
    """
    Write serializer for the attendance mark API (POST /student-attendance/mark/).
    """
    assessment_uid = serializers.UUIDField()
    is_absent      = serializers.BooleanField()

    def validate_assessment_uid(self, value):
        if not StudentCourseAssessment.objects.filter(uid=value).exists():
            raise serializers.ValidationError("Assessment not found.")
        return value


class UGExamDropSerializer(serializers.ModelSerializer):
     class Meta:
        model = UGExam
        fields = ['uid', 'name', 'semester', 'session', 'exam_month_year']
        read_only_fields = ['uid']
