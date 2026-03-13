from rest_framework import serializers
from .models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile, 
    LLBCourseStructure, LLBExam, LLBStudentCourseAssessment
)

class LLBCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLBCourse
        fields = '__all__'

class LLBSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLBSession
        fields = '__all__'

class LLBBatchSerializer(serializers.ModelSerializer):
    session_name = serializers.ReadOnlyField(source='session.name')
    class Meta:
        model = LLBBatch
        fields = '__all__'

class LLBCourseStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLBCourseStructure
        fields = '__all__'

class LLBExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLBExam
        fields = '__all__'

class LLBStudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='user.get_full_name')
    course_name = serializers.ReadOnlyField(source='course.name')
    college_name = serializers.ReadOnlyField(source='college.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')

    class Meta:
        model = LLBStudentProfile
        fields = '__all__'

class LLBStudentCourseAssessmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='course_structure.name')
    full_marks = serializers.ReadOnlyField(source='course_structure.full_marks')
    pass_marks = serializers.ReadOnlyField(source='course_structure.pass_marks')
    course_name = serializers.ReadOnlyField(source='course.name')
    student_details = LLBStudentProfileSerializer(source='student', read_only=True)
    exam_details = LLBExamSerializer(source='exam', read_only=True)

    class Meta:
        model = LLBStudentCourseAssessment
        fields = '__all__'
