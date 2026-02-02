from rest_framework import serializers
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCASubject, MCAExam, MCAExamSchedule, MCAStudentAssessment, 
    MCASemesterResult, MCASemesterRegistration, MCAExamRegistration
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

class MCASubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCASubject
        fields = '__all__'

class MCAExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCAExam
        fields = '__all__'

class MCAExamScheduleSerializer(serializers.ModelSerializer):
    subject_details = MCASubjectSerializer(source='subject', read_only=True)
    class Meta:
        model = MCAExamSchedule
        fields = '__all__'

class MCAStudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='user.get_full_name')
    course_name = serializers.ReadOnlyField(source='course.name')
    college_name = serializers.ReadOnlyField(source='college.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')

    class Meta:
        model = MCAStudentProfile
        fields = '__all__'

class MCAStudentAssessmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    paper_code = serializers.ReadOnlyField(source='subject.paper_code')
    
    class Meta:
        model = MCAStudentAssessment
        fields = '__all__'

class MCASemesterResultSerializer(serializers.ModelSerializer):
    student_details = MCAStudentProfileSerializer(source='student', read_only=True)
    class Meta:
        model = MCASemesterResult
        fields = '__all__'

class MCASemesterRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCASemesterRegistration
        fields = '__all__'

class MCAExamRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCAExamRegistration
        fields = '__all__'
