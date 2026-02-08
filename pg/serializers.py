from rest_framework import serializers
from .models import PGStudentProfile, PGDepartment, PGDegree, PGProgram, PGStudentCourseAssessment, PGCourseStructure
from colleges.models import College


class PGCollegeSerializer(serializers.ModelSerializer):
    """Lightweight College serializer for nested use."""
    class Meta:
        model = College
        fields = ['uid', 'name', 'short_name', 'college_code']


class PGDepartmentSerializer(serializers.ModelSerializer):
    """Lightweight Department serializer for nested use."""
    class Meta:
        model = PGDepartment
        fields = ['uid', 'name', 'code']


class PGDegreeSerializer(serializers.ModelSerializer):
    """Lightweight Degree serializer for nested use."""
    class Meta:
        model = PGDegree
        fields = ['uid', 'name', 'short_name', 'total_semesters', 'total_years']


class PGProgramSerializer(serializers.ModelSerializer):
    """Lightweight Program serializer for nested use."""
    class Meta:
        model = PGProgram
        fields = ['uid', 'name', 'short_name']


class PGStudentProfileSerializer(serializers.ModelSerializer):
    """
    PG Student Profile serializer for login response.
    Optimized with nested serializers for related objects.
    """
    department = PGDepartmentSerializer(read_only=True)
    degree = PGDegreeSerializer(read_only=True)
    program = PGProgramSerializer(read_only=True)
    college = PGCollegeSerializer(read_only=True)

    class Meta:
        model = PGStudentProfile
        fields = [
            'uid',
            'registration_no', 'roll_no',
            'father_name', 'mother_name',
            'date_of_birth', 'gender', 'caste',
            'mobile_no', 'aadhar_no', 'address',
            'college',
            'department', 'degree', 'program',
            'status', 'session', 'batch', 'is_active'
        ]
        read_only_fields = ['uid']

class PGStudentCourseAssessmentSerializer(serializers.ModelSerializer):
    """
    Serializer for CIA Marks Entry.
    Allows updating marks obtained and absent status.
    """
    class Meta:
        model = PGStudentCourseAssessment
        fields = [
            'id', 
            'student', 'paper_code', 'label', 
            'ind_marks_obtained', 'ind_max_marks', 'ind_pass_marks', 
            'ind_is_absent', 'ind_is_pass'
        ]
        read_only_fields = [
            'student', 'paper_code', 'label', 
            'ind_max_marks', 'ind_pass_marks', 'ind_is_pass'
        ]
    
    def validate(self, data):
        """
        Check that marks obtained do not exceed max marks.
        """
        instance = self.instance
        if instance:
            max_marks = instance.ind_max_marks
            new_marks = data.get('ind_marks_obtained')
            
            if new_marks is not None and max_marks is not None:
                if new_marks > max_marks:
                    raise serializers.ValidationError(
                        f"Marks obtained ({new_marks}) cannot exceed max marks ({max_marks})."
                    )
        return data

    def update(self, instance, validated_data):
        """
        Auto-calculate pass status on update.
        """
        instance = super().update(instance, validated_data)
        
        # Recalculate pass status
        if instance.ind_marks_obtained is not None and instance.ind_pass_marks is not None:
            if instance.ind_is_absent:
                instance.ind_is_pass = False
            else:
                instance.ind_is_pass = instance.ind_marks_obtained >= instance.ind_pass_marks
        elif instance.ind_is_absent:
             instance.ind_is_pass = False
             
        instance.save()
        return instance


class AssessmentDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for assessment details in college students view.
    """
    class Meta:
        model = PGStudentCourseAssessment
        fields = [
            'uid', 'semester', 'session', 'paper_code', 
            'course_name', 'course_code', 'label',
            'ind_max_marks', 'ind_pass_marks', 
            'ind_marks_obtained', 'ind_is_absent'
        ]


class StudentWithAssessmentsSerializer(serializers.Serializer):
    """
    Serializer for student with their assessments grouped together.
    """
    registration_no = serializers.CharField()
    name = serializers.CharField()
    department = serializers.CharField(allow_null=True)
    batch = serializers.CharField(allow_null=True)
    assessments = AssessmentDetailSerializer(many=True)


class PGSubjectDropdownSerializer(serializers.ModelSerializer):
    """
    Serializer for subject dropdown.
    """
    uid = serializers.CharField(read_only=True)
    
    class Meta:
        model = PGCourseStructure
        fields = ['uid', 'code', 'semester']


class PGCollegeStudentSerializer(serializers.Serializer):
    """
    Serializer for college students with assessment marks info.
    Used in PGCollegeStudentsView.
    """
    uid = serializers.UUIDField()  # Assessment UID for marks entry
    registration_no = serializers.CharField()
    name = serializers.CharField()
    ind_max_marks = serializers.IntegerField(allow_null=True)
    ind_pass_marks = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    is_cia_fill = serializers.BooleanField()
