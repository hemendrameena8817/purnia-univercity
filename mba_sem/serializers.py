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
