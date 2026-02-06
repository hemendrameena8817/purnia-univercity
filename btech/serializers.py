from rest_framework import serializers
from .models import (
    BTechCourse, BTechBranch, BTechSession, BTechBatch, BTechStudentProfile, 
    BTechCourseStructure, BTechCommonCourseStructure,
    BTechExam, BTechExamSchedule, BTechYearRegistration, 
    BTechExamRegistration, BTechStudentAssessment, BTechExamResult
)

class BTechCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechCourse
        fields = '__all__'

class BTechBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechBranch
        fields = '__all__'

class BTechSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechSession
        fields = '__all__'

class BTechBatchSerializer(serializers.ModelSerializer):
    session_name = serializers.ReadOnlyField(source='session.name')
    class Meta:
        model = BTechBatch
        fields = '__all__'

class BTechCourseStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechCourseStructure
        fields = '__all__'

class BTechCommonCourseStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechCommonCourseStructure
        fields = '__all__'

class BTechExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechExam
        fields = '__all__'

class BTechExamScheduleSerializer(serializers.ModelSerializer):
    course_details = BTechCourseStructureSerializer(source='course_structure', read_only=True)
    class Meta:
        model = BTechExamSchedule
        fields = '__all__'

class BTechStudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='get_full_name')
    college_name = serializers.ReadOnlyField(source='college.name')
    batch_name = serializers.ReadOnlyField(source='batch.name')
    branch_name = serializers.ReadOnlyField(source='branch.name')

    class Meta:
        model = BTechStudentProfile
        fields = '__all__'

class BTechStudentAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechStudentAssessment
        fields = '__all__'

class BTechExamResultSerializer(serializers.ModelSerializer):
    student_details = BTechStudentProfileSerializer(source='student', read_only=True)
    class Meta:
        model = BTechExamResult
        fields = '__all__'

class BTechYearRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechYearRegistration
        fields = '__all__'

class BTechExamRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTechExamRegistration
        fields = '__all__'
