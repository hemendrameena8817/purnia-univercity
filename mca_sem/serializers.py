from rest_framework import serializers
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCACourseStructure, MCACommonCourseStructure,
    MCAExam, MCAExamSchedule, MCASemesterRegistration, 
    MCAExamRegistration, MCAStudentAssessment, MCAExamResult
)

class MCACourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCACourse
        fields = '__all__'

class MCASessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCASession
        fields = '__all__'

class MCABatchSerializer(serializers.ModelSerializer):
    session_name = serializers.ReadOnlyField(source='session.name')
    class Meta:
        model = MCABatch
        fields = '__all__'

class MCACourseStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCACourseStructure
        fields = '__all__'

class MCACommonCourseStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCACommonCourseStructure
        fields = '__all__'

class MCAExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCAExam
        fields = '__all__'

class MCAExamScheduleSerializer(serializers.ModelSerializer):
    course_details = MCACourseStructureSerializer(source='course_structure', read_only=True)
    class Meta:
        model = MCAExamSchedule
        fields = '__all__'

class MCAStudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='get_full_name')
    college_name = serializers.ReadOnlyField(source='college.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')

    class Meta:
        model = MCAStudentProfile
        fields = '__all__'

class MCAStudentAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCAStudentAssessment
        fields = '__all__'

class MCAExamResultSerializer(serializers.ModelSerializer):
    student_details = MCAStudentProfileSerializer(source='student', read_only=True)
    class Meta:
        model = MCAExamResult
        fields = '__all__'

class MCASemesterRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCASemesterRegistration
        fields = '__all__'

class MCAExamRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCAExamRegistration
        fields = '__all__'
