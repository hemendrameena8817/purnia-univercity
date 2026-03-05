from rest_framework import serializers
from .models import PGStudentProfile, PGDepartment, PGDegree, PGProgram, PGStudentCourseAssessment, PGCourseStructure, PGExamRegistration
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
            'first_name', 'last_name', 'hindi_name',
            'registration_no', 'roll_no',
            'father_name', 'mother_name',
            'date_of_birth', 'gender', 'caste',
            'mobile_no', 'aadhar_no', 'apaar_id', 'address',
            'admission_date', 'enrollment_date',
            'migration_submitted', 'last_university',
            'college', 'department', 'degree', 'program',
            'current_semester', 'session', 'batch'
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
            'course_name'
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
    roll_no = serializers.CharField()
    name = serializers.CharField()
    ind_max_marks = serializers.IntegerField(allow_null=True)
    ind_pass_marks = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    ind_marks_obtained = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    ind_is_absent = serializers.BooleanField(allow_null=True)
    is_cia_fill = serializers.BooleanField()
    cia_ok = serializers.BooleanField(allow_null=True)
    updated_at = serializers.DateTimeField()


class PGExamRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for PG Exam Registration.
    Includes student profile and assessment details.
    """
    student = PGStudentProfileSerializer(read_only=True)
    assessments = serializers.SerializerMethodField()

    class Meta:
        model = PGExamRegistration
        fields = [
            'uid', 'student', 'sem', 'session', 'exam_type', 
            'status', 'fees', 'is_open', 'assessments'
        ]

    def get_assessments(self, obj):
        """
        Fetch ESE assessments for the student matching:
        - semester from the registration (obj.sem)
        - label starts with 'ESE'
        - No exam_type filter — returns both REGULAR and BACK subjects
        """
        sem_str = str(obj.sem) if obj.sem else ""

        assessments = PGStudentCourseAssessment.objects.filter(
            student=obj.student,
            semester__icontains=sem_str,
            label__icontains='ESE',
        ).order_by('paper_code')

        return AssessmentDetailSerializer(assessments, many=True).data


# ─────────────────────────────────────────────────────────────────────────────
# Attendance Serializers
# ─────────────────────────────────────────────────────────────────────────────

class PGAttendanceStudentSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for each student's ESE assessment entry
    returned in the attendance list API (GET /student-attendance/list/).

    Includes:
    - assessment_uid  → used by frontend to submit attendance (POST /mark/)
    - student details (name, roll_no, registration_no, photo)
    - course info (course_code, course_name)
    - is_absent       → current attendance status (True = Absent, False = Present)
    """
    assessment_uid  = serializers.UUIDField(source='uid', read_only=True)
    name            = serializers.SerializerMethodField()
    roll_no         = serializers.SerializerMethodField()
    registration_no = serializers.SerializerMethodField()
    photo_url       = serializers.SerializerMethodField()
    student_uid     = serializers.UUIDField(source='student.uid', read_only=True)
    is_absent       = serializers.BooleanField(source='ind_is_absent', read_only=True)

    class Meta:
        model  = PGStudentCourseAssessment
        fields = [
            'assessment_uid',
            'student_uid',
            'name',
            'roll_no',
            'registration_no',
            'photo_url',
            'course_code',
            'course_name',
            'is_absent',
        ]

    def get_name(self, obj):
        return obj.student.get_full_name() if obj.student else '-'

    def get_roll_no(self, obj):
        return obj.student.roll_no or 'N/A' if obj.student else 'N/A'

    def get_registration_no(self, obj):
        return obj.student.registration_no or 'N/A' if obj.student else 'N/A'

    def get_photo_url(self, obj):
        if obj.student and obj.student.profile_image:
            try:
                return obj.student.profile_image.url
            except Exception:
                return None
        return None


class PGAttendanceMarkSerializer(serializers.Serializer):
    """
    Write serializer for the attendance mark API (POST /student-attendance/mark/).

    Fields:
    - assessment_uid  → PGStudentCourseAssessment.uid
    - is_absent       → True = Absent, False = Present
    """
    assessment_uid = serializers.UUIDField()
    is_absent      = serializers.BooleanField()

    def validate_assessment_uid(self, value):
        if not PGStudentCourseAssessment.objects.filter(uid=value).exists():
            raise serializers.ValidationError("Assessment not found.")
        return value


