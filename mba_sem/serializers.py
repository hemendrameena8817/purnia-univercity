from rest_framework import serializers
from .models import *


class MBACourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBACourse
        fields = '__all__'

class MBASessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBASession
        fields = '__all__'

class MBABatchSerializer(serializers.ModelSerializer):
    session_name = serializers.ReadOnlyField(source='session.name')
    class Meta:
        model = MBABatch
        fields = '__all__'

class MBACourseStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBACourseStructure
        fields = '__all__'

# class MCACommonCourseStructureSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MCACommonCourseStructure
#         fields = '__all__'

class MBAExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBAExam
        fields = '__all__'

class MBAExamScheduleSerializer(serializers.ModelSerializer):
    course_details = MBACourseStructureSerializer(source='common_course_structure', read_only=True)
    class Meta:
        model = MBAExamSchedule
        fields = '__all__'

class MBAStudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='get_full_name')
    college_name = serializers.ReadOnlyField(source='college.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')

    class Meta:
        model = MBAStudentProfile
        fields = '__all__'

class MBAStudentAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBAStudentAssessment
        fields = '__all__'

class MBAExamResultSerializer(serializers.ModelSerializer):
    student_details = MBAStudentProfileSerializer(source='student', read_only=True)
    class Meta:
        model = MBAExamResult
        fields = '__all__'

class MBASemesterRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBASemesterRegistration
        fields = '__all__'

class MBAExamRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBAExamRegistration
        fields = '__all__'

class MBAStudentCourseAssessmentSerializer(serializers.ModelSerializer):
    """
    Serializer for MBA CIA/ESE Marks Entry.
    Allows updating marks obtained and absent status.
    """

    class Meta:
        model = MBAStudentCourseAssessment
        fields = [
            'id',
            'student', 'paper_code', 'label',
            'ind_marks_obtained', 'ind_max_marks', 'ind_pass_marks',
            'ind_is_absent', 'ind_is_pass'
        ]
        read_only_fields = [
            'student', 'paper_code', 'label',
            'ind_max_marks', 'ind_pass_marks', 'ind_is_pass'
        ]

    def validate(self, data):
        """
        Check that marks obtained do not exceed max marks.
        """
        instance = self.instance
        if instance:
            max_marks = instance.ind_max_marks
            new_marks = data.get('ind_marks_obtained')

            if new_marks is not None and max_marks is not None:
                if new_marks > max_marks:
                    raise serializers.ValidationError(
                        f"Marks obtained ({new_marks}) cannot exceed max marks ({max_marks})."
                    )

        return data

    def update(self, instance, validated_data):
        """
        Auto-calculate pass status on update.
        """
        instance = super().update(instance, validated_data)

        # Recalculate pass status
        if instance.ind_marks_obtained is not None and instance.ind_pass_marks is not None:
            if instance.ind_is_absent:
                instance.ind_is_pass = False
            else:
                instance.ind_is_pass = (
                    instance.ind_marks_obtained >= instance.ind_pass_marks
                )
        elif instance.ind_is_absent:
            instance.ind_is_pass = False

        instance.save()
        return instance

class MBACommonCourseStructureSerializer(serializers.ModelSerializer):

    class Meta:
        model = MBACommonCourseStructure
        fields = [
            "uid",
            "course_name",
            "course_type",
            "code",
            "semester"
        ]

class MBAExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBAExam
        fields = [
            "uid",
            "name",
            "semester",
            "session",
            "exam_month_year",
            "publication_date"
        ]


class MBACollegeStudentSerializer(serializers.ModelSerializer):

    registration_no = serializers.CharField(source='student.registration_no')
    roll_no = serializers.CharField(source='student.roll_no')
    name = serializers.SerializerMethodField()

    class Meta:
        model = MBAStudentCourseAssessment
        fields = [
            'uid',
            'registration_no',
            'roll_no',
            'name',

            'semester',
            'course_name',

            'exam_type',      # Regular / Back
            'label',          # CIA-Theory / ESE-Practical
            'course_type',    # Theory / Practical

            'ind_max_marks',
            'ind_pass_marks',
            'ind_marks_obtained',
            'ind_is_absent',
            'ind_is_pass',

            'updated_at'
        ]

    def get_name(self, obj):
        return f"{obj.student.first_name or ''} {obj.student.last_name or ''}".strip()

class MBAStudentCourseAssessmentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = MBAStudentCourseAssessment
        fields = [
            "uid",
            "student",

            "course_name",
            "course_short_name",
            "course_type",
            "course_code",
            "paper_code",

            "semester",
            "label",
            "session",
            "exam_type",
            "batch",
            "attendance",

            # Individual Marks
            "ind_max_marks",
            "ind_pass_marks",
            "ind_marks_obtained",
            "ind_is_absent",

            # Optional JSON
            "json_data",
        ]

        read_only_fields = ["uid"]

    def validate(self, data):

        max_marks = data.get("ind_max_marks")
        pass_marks = data.get("ind_pass_marks")
        obtained = data.get("ind_marks_obtained")

        if max_marks is not None and pass_marks is not None:
            if pass_marks > max_marks:
                raise serializers.ValidationError(
                    "Pass marks cannot be greater than max marks."
                )

        if obtained is not None and max_marks is not None:
            if obtained > max_marks:
                raise serializers.ValidationError(
                    "Obtained marks cannot exceed max marks."
                )

        return data

