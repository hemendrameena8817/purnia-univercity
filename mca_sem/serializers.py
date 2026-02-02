from rest_framework import serializers
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCASubject, MCAExam, MCAResult, MCAResultDetail
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

class MCAStudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='user.get_full_name')
    course_name = serializers.ReadOnlyField(source='course.name')
    college_name = serializers.ReadOnlyField(source='college.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')

    class Meta:
        model = MCAStudentProfile
        fields = '__all__'

class MCAResultDetailSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    paper_code = serializers.ReadOnlyField(source='subject.paper_code')
    full_marks = serializers.ReadOnlyField(source='subject.full_marks')
    pass_marks = serializers.ReadOnlyField(source='subject.pass_marks')

    class Meta:
        model = MCAResultDetail
        fields = '__all__'

class MCAResultSerializer(serializers.ModelSerializer):
    details = MCAResultDetailSerializer(many=True, read_only=True)
    student_details = MCAStudentProfileSerializer(source='student', read_only=True)
    exam_details = MCAExamSerializer(source='exam', read_only=True)

    class Meta:
        model = MCAResult
        fields = '__all__'
