"""Serializers for UG Before CBCS - Simplified Models"""
from rest_framework import serializers
from .models import (
    UGBeforeCBCSStudentProfile,

    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult,

)


class UGBeforeCBCSStudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for Student Profile"""
    college_name = serializers.ReadOnlyField(source='college.name')
    user_username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = UGBeforeCBCSStudentProfile
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



# Marksheet JSON Serializers
class MarksheetStudentSerializer(serializers.Serializer):
    """Serializer for student data in marksheet JSON response"""
    uid = serializers.UUIDField()
    registration_no = serializers.CharField()
    roll_no = serializers.CharField(allow_null=True)
    student_name = serializers.CharField()
    student_name_hindi = serializers.CharField(allow_null=True)
    fathers_name = serializers.CharField(allow_null=True)
    mothers_name = serializers.CharField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    dob = serializers.DateField(allow_null=True)
    course_code = serializers.CharField(allow_null=True)
    discipline_code = serializers.CharField(allow_null=True)


class MarksheetPaperSerializer(serializers.Serializer):
    """Serializer for individual paper/subject in marksheet"""
    uid = serializers.UUIDField()
    name = serializers.CharField()
    paper_code = serializers.CharField()
    status = serializers.CharField()
    max_marks = serializers.IntegerField()
    pass_marks = serializers.IntegerField()
    obtained = serializers.IntegerField()


class MarksheetSubjectGroupSerializer(serializers.Serializer):
    """Serializer for subject groups (honours, subsidiary, etc.)"""
    name = serializers.CharField()
    papers = MarksheetPaperSerializer(many=True)
    total_max = serializers.IntegerField()
    total_pass = serializers.IntegerField()
    total_obtained = serializers.IntegerField()


class MarksheetDataSerializer(serializers.Serializer):
    """Main serializer for complete marksheet data"""
    is_honours_with_practical = serializers.BooleanField()
    student = MarksheetStudentSerializer()
    exam_name = serializers.CharField()
    exam_month_year = serializers.CharField()
    exam_year = serializers.CharField()
    batch_year = serializers.CharField()
    session_year = serializers.CharField()
    hons_subject = serializers.CharField()
    center_name = serializers.CharField()
    
    # Nested subjects data
    subjects = serializers.DictField(child=MarksheetSubjectGroupSerializer())
    
    grand_total = serializers.CharField()
    result_status = serializers.CharField()
    hons_total_words = serializers.CharField()
    publication_date = serializers.CharField()
