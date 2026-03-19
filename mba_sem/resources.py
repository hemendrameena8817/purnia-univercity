from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from .models import (
    MBACourse, MBASession, MBABatch, MBAStudentProfile, MBACourseStructure,
    MBACommonCourseStructure, MBAExam, MBAExamCenterMapping, MBAExamSchedule,
    MBASemesterRegistration, MBAExamRegistration, MBAStudentAssessment,
    MBAExamResult, MBAStudentCourseAssessment
)
from colleges.models import College
from accounts.models import UserAccount

class MBACourseResource(resources.ModelResource):
    class Meta:
        model = MBACourse
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'discipline_code', 'duration_years')

class MBASessionResource(resources.ModelResource):
    class Meta:
        model = MBASession
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'start_year', 'end_year', 'is_active')

class MBABatchResource(resources.ModelResource):
    session = fields.Field(
        column_name='session_name',
        attribute='session',
        widget=ForeignKeyWidget(MBASession, 'name')
    )
    class Meta:
        model = MBABatch
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'session', 'is_active')

class MBAStudentProfileResource(resources.ModelResource):
    user = fields.Field(
        column_name='username',
        attribute='user',
        widget=ForeignKeyWidget(UserAccount, 'username')
    )
    college = fields.Field(
        column_name='center_code',
        attribute='college',
        widget=ForeignKeyWidget(College, 'center_code')
    )
    course = fields.Field(
        column_name='course_name',
        attribute='course',
        widget=ForeignKeyWidget(MBACourse, 'name')
    )
    batch = fields.Field(
        column_name='batch_name',
        attribute='batch',
        widget=ForeignKeyWidget(MBABatch, 'name')
    )

    class Meta:
        model = MBAStudentProfile
        import_id_fields = ('registration_no',)
        fields = (
            'uid', 'user', 'first_name', 'last_name', 'hindi_name', 'registration_no',
            'roll_no', 'father_name', 'mother_name', 'date_of_birth', 'gender',
            'mobile_no', 'address', 'aadhar_no', 'college', 'course', 'batch',
            'current_semester', 'session_str', 'status', 'is_active',
            'sem_1_gpa', 'sem_1_credit_earned', 'sem_2_gpa', 'sem_2_credit_earned',
            'sem_3_gpa', 'sem_3_credit_earned', 'sem_4_gpa', 'sem_4_credit_earned'
        )

class MBACourseStructureResource(resources.ModelResource):
    class Meta:
        model = MBACourseStructure
        import_id_fields = ('uid',)
        fields = (
            'uid', 'course_name', 'course_short_name', 'course_type', 'course_code',
            'max_marks', 'min_marks', 'label', 'semester', 'credit', 'description'
        )

class MBACommonCourseStructureResource(resources.ModelResource):
    class Meta:
        model = MBACommonCourseStructure
        import_id_fields = ('uid',)
        fields = ('uid', 'semester', 'course_name', 'course_type', 'ltp', 'marks', 'code')

class MBAExamResource(resources.ModelResource):
    class Meta:
        model = MBAExam
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'semester', 'session', 'exam_month_year', 'publication_date')

class MBAExamCenterMappingResource(resources.ModelResource):
    exam = fields.Field(
        column_name='exam_name',
        attribute='exam',
        widget=ForeignKeyWidget(MBAExam, 'name')
    )
    center = fields.Field(
        column_name='center_code',
        attribute='center',
        widget=ForeignKeyWidget(College, 'center_code')
    )
    attached_colleges = fields.Field(
        column_name='attached_college_codes',
        attribute='attached_colleges',
        widget=ManyToManyWidget(College, field='center_code')
    )
    class Meta:
        model = MBAExamCenterMapping
        import_id_fields = ('uid',)
        fields = ('uid', 'exam', 'center', 'attached_colleges')

class MBAExamScheduleResource(resources.ModelResource):
    exam = fields.Field(
        column_name='exam_name',
        attribute='exam',
        widget=ForeignKeyWidget(MBAExam, 'name')
    )
    common_course_structure = fields.Field(
        column_name='course_code',
        attribute='common_course_structure',
        widget=ForeignKeyWidget(MBACommonCourseStructure, 'code')
    )
    class Meta:
        model = MBAExamSchedule
        import_id_fields = ('uid',)
        fields = ('uid', 'exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting')

class MBASemesterRegistrationResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(MBAStudentProfile, 'registration_no')
    )
    class Meta:
        model = MBASemesterRegistration
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'start_date', 'end_date', 'is_open', 'sem',
            'status', 'exam_eligible', 'remarks', 'session'
        )

class MBAExamRegistrationResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(MBAStudentProfile, 'registration_no')
    )
    exam = fields.Field(
        column_name='exam_name',
        attribute='exam',
        widget=ForeignKeyWidget(MBAExam, 'name')
    )
    exam_subjects = fields.Field(
        column_name='subject_codes',
        attribute='exam_subjects',
        widget=ManyToManyWidget(MBACommonCourseStructure, field='code')
    )
    class Meta:
        model = MBAExamRegistration
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'exam', 'exam_type', 'exam_subjects', 'start_date',
            'end_date', 'is_open', 'fees', 'sem', 'status', 'session'
        )

class MBAStudentAssessmentResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(MBAStudentProfile, 'registration_no')
    )
    batch = fields.Field(
        column_name='batch_name',
        attribute='batch',
        widget=ForeignKeyWidget(MBABatch, 'name')
    )
    class Meta:
        model = MBAStudentAssessment
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'course_name', 'course_type', 'course_code',
            'semester', 'label', 'session', 'batch', 'college_code', 'exam_type',
            'attendance', 'ind_max_marks', 'ind_pass_marks', 'ind_is_absent',
            'ind_marks_obtained', 'ind_grace_obtained', 'ind_final_marks_obtained',
            'ind_is_pass', 'comb_max_marks', 'comb_pass_marks', 'comb_marks_obtained',
            'comb_numeric_grade', 'comb_letter_grade', 'comb_grade_point',
            'course_max_marks', 'course_marks_obtained', 'course_final_marks_obtained',
            'sem_result', 'next_sem_status'
        )

class MBAExamResultResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(MBAStudentProfile, 'registration_no')
    )
    class Meta:
        model = MBAExamResult
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'semester', 'session', 'cia_pass', 'ese_pass',
            'semester_result', 'total_marks_obtained', 'percentage',
            'next_semester', 'next_sem_status', 'is_legacy', 'published_at'
        )

class MBAStudentCourseAssessmentResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(MBAStudentProfile, 'registration_no')
    )
    mba_exam = fields.Field(
        column_name='exam_name',
        attribute='mba_exam',
        widget=ForeignKeyWidget(MBAExam, 'name')
    )
    batch = fields.Field(
        column_name='batch_name',
        attribute='batch',
        widget=ForeignKeyWidget(MBABatch, 'name')
    )
    
    # Export only fields (following UG pattern)
    student_registration_no = fields.Field(attribute='student__registration_no', column_name='Registration No', readonly=True)
    student_roll_no = fields.Field(attribute='student__roll_no', column_name='Roll No', readonly=True)
    student_name = fields.Field(attribute='student__first_name', column_name='Student Name', readonly=True)
    
    class Meta:
        model = MBAStudentCourseAssessment
        import_id_fields = ('uid',)
        fields = (
            'uid', 'mba_exam', 'course_name', 'course_short_name', 'student',
            'course_type', 'course_code', 'paper_code', 'semester', 'label',
            'degree', 'session', 'batch', 'college_code', 'exam_type',
            'attendance', 'ind_max_marks', 'ind_pass_marks', 'ind_is_absent',
            'ind_marks_obtained', 'ind_grace_obtained', 'ind_final_marks_obtained',
            'ind_is_pass', 'comb_max_marks', 'comb_max_credits', 'comb_pass_marks',
            'comb_marks_obtained', 'comb_grace_obtained', 'comb_final_marks_obtained',
            'comb_credit_obtained', 'comb_numeric_grade', 'comb_letter_grade',
            'comb_grade_point', 'course_max_marks', 'course_max_credits',
            'course_pass_marks', 'course_marks_obtained', 'course_grace_obtained',
            'course_final_marks_obtained', 'course_credit_obtained',
            'course_grade_point', 'sem_max_credit', 'sem_credit_obtained',
            'sgpa', 'sem_result', 'next_sem_status', 'sem_grace_obtained'
        )
        export_order = (
            'uid', 'student_registration_no', 'student_roll_no', 'student_name',
            'semester', 'session', 'paper_code', 'label', 'ind_marks_obtained',
            'ind_pass_marks', 'ind_is_pass'
        )
