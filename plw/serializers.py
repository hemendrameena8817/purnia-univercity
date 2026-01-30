from rest_framework import serializers
from .models import (
    PLWCourse, PLWSession, PLWBatch, PLWStudentProfile, 
    PLWSubject, PLWExam, PLWResult, PLWResultDetail
)
from .utils.generate_plw_barcode_text import generate_plw_barcode_text

class PLWCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PLWCourse
        fields = '__all__'

class PLWSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PLWSession
        fields = '__all__'

class PLWBatchSerializer(serializers.ModelSerializer):
    session_name = serializers.ReadOnlyField(source='session.name')
    class Meta:
        model = PLWBatch
        fields = '__all__'

class PLWSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = PLWSubject
        fields = '__all__'

class PLWExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = PLWExam
        fields = '__all__'

class PLWStudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='user.get_full_name')
    course_name = serializers.ReadOnlyField(source='course.name')
    college_name = serializers.ReadOnlyField(source='college.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')

    class Meta:
        model = PLWStudentProfile
        fields = '__all__'

class PLWResultDetailSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    paper_code = serializers.ReadOnlyField(source='subject.paper_code')
    full_marks = serializers.ReadOnlyField(source='subject.full_marks')
    pass_marks = serializers.ReadOnlyField(source='subject.pass_marks')

    class Meta:
        model = PLWResultDetail
        fields = '__all__'

class PLWResultSerializer(serializers.ModelSerializer):
    details = PLWResultDetailSerializer(many=True, read_only=True)
    student_details = PLWStudentProfileSerializer(source='student', read_only=True)
    exam_details = PLWExamSerializer(source='exam', read_only=True)
    barcode_text = serializers.SerializerMethodField()

    class Meta:
        model = PLWResult
        fields = '__all__'

    def get_barcode_text(self, obj):
        return generate_plw_barcode_text(obj)
