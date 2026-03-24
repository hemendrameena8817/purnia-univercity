from rest_framework import serializers
from .models import PGOldResult, PGOldStudentProfile, PGExamMasterDump



class PGOldStudentProfileSerializer(serializers.ModelSerializer):
    college = serializers.StringRelatedField()
    
    class Meta:
        model = PGOldStudentProfile
        fields = [
            'uid', 'registration_no', 'roll_no', 'first_name', 'hindi_name',
            'fathers_name', 'mothers_name', 'gender', 'dob', 'college',
            'course_code', 'discipline_code', 'pg_faculty', 'pg_department',
            'pg_degree', 'pg_program', 'batch_code', 'current_semester',
            'final_result', 'gpa', 'cgpa', 'total_percentage',
            'is_active', 'created_at', 'updated_at'
        ]


class SubjectDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PGOldResult
        fields = [
       'uid', 'status','exam_type', 'exam_type_his', 'paper_code', 'subject_code', 'subject_name', 'faculty',
            'maximum_mark', 'pass_mark', 'mark_secured', 'subject_total_mark',
            'subject_ca', 'subject_ng', 'subject_ce', 'subject_gp',
            'subject_result', 'let_grad_sub', 'semester_code', 'batch_code','session_code'
        ]


class StudentInfoSerializer(serializers.ModelSerializer):
    college = serializers.StringRelatedField()
    class Meta:
        model = PGOldResult
        fields = [
             'uid','college','college_roll_no', 'college_reg_no', 'student_name', 'fathers_name',
            'mothers_name','session_code',
            'course_code', 'discipline_code', 'final_result', 'grand_total_mark',
            'total_secured_mark', 'total_per', 'gpa', 'cgpa', 'grade',
            'student_name_hindi', 'pg_faculty', 'pg_department', 'pg_degree', 'pg_program'
        ]
    def get_college(self, obj):
        return obj.college.name


class PGOldResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = PGOldResult
        fields = '__all__'


class PGOldResultDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PGOldResult
        fields = '__all__'
        depth = 1


class PGExamMasterDumpSerializer(serializers.ModelSerializer):
    class Meta:
        model = PGExamMasterDump
        fields = ['uid','actual_exam_month','year','exam_month','exam_year','publish_date']