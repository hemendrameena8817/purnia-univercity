from rest_framework import serializers
from .models import (
    UGBeforeCBCSCourse, UGBeforeCBCSDiscipline, UGBeforeCBCSSession,
    UGBeforeCBCSBatch, UGBeforeCBCSSubject, UGBeforeCBCSCourseStructure,
    UGBeforeCBCSStudentProfile, UGBeforeCBCSExam, UGBeforeCBCSExamRegistration,
    UGBeforeCBCSStudentAssessment, UGBeforeCBCSExamResult
)

class UGBeforeCBCSCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UGBeforeCBCSCourse
        fields = '__all__'

class UGBeforeCBCSDisciplineSerializer(serializers.ModelSerializer):
    course_name = serializers.ReadOnlyField(source='course.name')
    class Meta:
        model = UGBeforeCBCSDiscipline
        fields = '__all__'

class UGBeforeCBCSSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UGBeforeCBCSSession
        fields = '__all__'

class UGBeforeCBCSBatchSerializer(serializers.ModelSerializer):
    session_name = serializers.ReadOnlyField(source='session.name')
    class Meta:
        model = UGBeforeCBCSBatch
        fields = '__all__'

class UGBeforeCBCSSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = UGBeforeCBCSSubject
        fields = '__all__'

class UGBeforeCBCSCourseStructureSerializer(serializers.ModelSerializer):
    discipline_name = serializers.ReadOnlyField(source='discipline.name')
    subject_name = serializers.ReadOnlyField(source='subject.name')
    class Meta:
        model = UGBeforeCBCSCourseStructure
        fields = '__all__'

class UGBeforeCBCSStudentProfileSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source='college.name')
    course_name = serializers.ReadOnlyField(source='course.name')
    discipline_name = serializers.ReadOnlyField(source='discipline.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')
    session_name = serializers.ReadOnlyField(source='session.name')
    
    class Meta:
        model = UGBeforeCBCSStudentProfile
        fields = '__all__'

class UGBeforeCBCSExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = UGBeforeCBCSExam
        fields = '__all__'

class UGBeforeCBCSExamRegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.student_name')
    exam_name = serializers.ReadOnlyField(source='exam.name')
    class Meta:
        model = UGBeforeCBCSExamRegistration
        fields = '__all__'

class UGBeforeCBCSStudentAssessmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    class Meta:
        model = UGBeforeCBCSStudentAssessment
        fields = '__all__'

class UGBeforeCBCSExamResultSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='registration.student.student_name')
    class Meta:
        model = UGBeforeCBCSExamResult
        fields = '__all__'
