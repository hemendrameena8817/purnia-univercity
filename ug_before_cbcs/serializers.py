"""Serializers for UG Before CBCS - Simplified Models"""
from rest_framework import serializers
from .models import (
    UGBeforeCBCSStudentProfile,
    UGBeforeCBCSSubject,
    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult,
    UGBeforeCBCSExamSummary
)


class UGBeforeCBCSStudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for Student Profile"""
    college_name = serializers.ReadOnlyField(source='college.name')
    user_username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = UGBeforeCBCSStudentProfile
        fields = '__all__'
        read_only_fields = ('uid', 'created_at', 'updated_at')


class UGBeforeCBCSSubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject"""
    
    class Meta:
        model = UGBeforeCBCSSubject
        fields = '__all__'
        read_only_fields = ('uid', 'created_at', 'updated_at')


class UGBeforeCBCSExamSerializer(serializers.ModelSerializer):
    """Serializer for Exam"""
    
    class Meta:
        model = UGBeforeCBCSExam
        fields = '__all__'
        read_only_fields = ('uid', 'created_at', 'updated_at')


class UGBeforeCBCSStudentResultSerializer(serializers.ModelSerializer):
    """Serializer for Student Result"""
    student_name = serializers.ReadOnlyField(source='student.student_name')
    student_registration_no = serializers.ReadOnlyField(source='student.registration_no')
    exam_name = serializers.ReadOnlyField(source='exam.name')
    exam_code = serializers.ReadOnlyField(source='exam.exam_code')
    subject_name = serializers.ReadOnlyField(source='subject.subject_name')
    subject_paper_code = serializers.ReadOnlyField(source='subject.paper_code')
    
    class Meta:
        model = UGBeforeCBCSStudentResult
        fields = '__all__'
        read_only_fields = ('uid', 'created_at', 'updated_at')


class UGBeforeCBCSExamSummarySerializer(serializers.ModelSerializer):
    """Serializer for Exam Summary"""
    student_name = serializers.ReadOnlyField(source='student.student_name')
    student_registration_no = serializers.ReadOnlyField(source='student.registration_no')
    exam_name = serializers.ReadOnlyField(source='exam.name')
    exam_code = serializers.ReadOnlyField(source='exam.exam_code')
    
    class Meta:
        model = UGBeforeCBCSExamSummary
        fields = '__all__'
        read_only_fields = ('uid', 'created_at', 'updated_at')
