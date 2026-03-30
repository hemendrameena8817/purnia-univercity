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
    department      = serializers.SerializerMethodField()
    category        = serializers.CharField(source='course_type', read_only=True)

    class Meta:
        model  = StudentCourseAssessment
        fields = [
            'id',
            'assessment_uid',
            'student_uid',
            'name',
            'roll_no',
            'registration_no',
            'photo_url',
            'course_code',
            'course_name',
            'department',
            'category',
            'is_absent',
        ]

    def get_department(self, obj):
        c_type = (obj.course_type or "").upper().strip()
        
        # 1. CBCS Student selections
        if c_type == 'MJC':
            return obj.student.major_course.name if obj.student and obj.student.major_course else "N/A"
        elif c_type == 'MIC':
            return obj.student.minor_course.name if obj.student and obj.student.minor_course else "N/A"
        elif c_type == 'MDC':
            return obj.student.mdc_course.name if obj.student and obj.student.mdc_course else "N/A"
        
        # 3. SEC, AEC: Usually teaching department
        elif c_type in ['SEC', 'AEC', 'VAC']:
            return obj.department.name if obj.department else "N/A"
            
        # 4. Fallback
        if obj.department:
            return obj.department.name
        return obj.student.major_course.name if obj.student and obj.student.major_course else "N/A"

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
