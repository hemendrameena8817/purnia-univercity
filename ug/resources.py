from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from .models import (
    UGFaculty, UGDepartment, UGDegree, UGProgram, UGBatch, UGStudentProfile,
    CourseStructure, StudentCourseAssessment, SemesterRegistration, ExamRegistration,
    CommonCourseStructure, UGExamResult, ExamRegistrationPayment
)
from university.models import University
from colleges.models import College
from accounts.models import UserAccount

class UGFacultyResource(resources.ModelResource):
    university = fields.Field(
        column_name='university',
        attribute='university',
        widget=ForeignKeyWidget(University, 'name')
    )
    departments = fields.Field(
        column_name='department_codes',
        attribute='departments',
        widget=ManyToManyWidget(UGDepartment, field='code')
    )
    
    class Meta:
        model = UGFaculty
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'short_name', 'description', 'university', 'departments', 'is_publish')

class UGDepartmentResource(resources.ModelResource):
    class Meta:
        model = UGDepartment
        import_id_fields = ('code',) # Use code as unique identifier for import if possible
        fields = ('uid', 'name', 'code', 'head_of_department', 'is_publish')

class UGDegreeResource(resources.ModelResource):
    class Meta:
        model = UGDegree
        import_id_fields = ('name',)
        fields = ('uid', 'name', 'short_name', 'total_semesters', 'total_years')

class UGProgramResource(resources.ModelResource):
    degree = fields.Field(
        column_name='degree',
        attribute='degree',
        widget=ForeignKeyWidget(UGDegree, 'name')
    )
    department = fields.Field(
        column_name='department_code',
        attribute='department',
        widget=ForeignKeyWidget(UGDepartment, 'code')
    )
    
    class Meta:
        model = UGProgram
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'short_name', 'degree', 'department')

class UGBatchResource(resources.ModelResource):
    program = fields.Field(
        column_name='program',
        attribute='program',
        widget=ForeignKeyWidget(UGProgram, 'name')
    )
    
    class Meta:
        model = UGBatch
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'program')

class UGStudentProfileResource(resources.ModelResource):
    user = fields.Field(
        column_name='username',
        attribute='user',
        widget=ForeignKeyWidget(UserAccount, 'username')
    )
    batch = fields.Field(
        column_name='batch',
        attribute='batch',
        widget=ForeignKeyWidget(UGBatch, 'name')
    )
    college = fields.Field(
        column_name='center_code',
        attribute='college',
        widget=ForeignKeyWidget(College, 'center_code')
    )
    department = fields.Field(
        column_name='department_code',
        attribute='department',
        widget=ForeignKeyWidget(UGDepartment, 'code')
    )
    program = fields.Field(
        column_name='program',
        attribute='program',
        widget=ForeignKeyWidget(UGProgram, 'name')
    )
    degree = fields.Field(
        column_name='degree',
        attribute='degree',
        widget=ForeignKeyWidget(UGDegree, 'name')
    )
    major_course = fields.Field(
        column_name='major_course_code',
        attribute='major_course',
        widget=ForeignKeyWidget(UGDepartment, 'code')
    )
    minor_course = fields.Field(
        column_name='minor_course_code',
        attribute='minor_course',
        widget=ForeignKeyWidget(UGDepartment, 'code')
    )
    mdc_course = fields.Field(
        column_name='mdc_course_code',
        attribute='mdc_course',
        widget=ForeignKeyWidget(UGDepartment, 'code')
    )

    class Meta:
        model = UGStudentProfile
        import_id_fields = ('registration_no',)
        fields = (
            'uid', 'user', 'first_name', 'last_name', 'hindi_name', 'registration_no',
            'address', 'admission_date', 'date_of_birth', 'aadhar_no', 'mobile_no',
            'gender', 'caste', 'religion', 'nationality', 'roll_no', 'batch',
            'father_name', 'mother_name', 'current_semester', 'session', 'status',
            'college', 'department', 'program', 'degree', 'major_course',
            'minor_course', 'mdc_course', 'is_active'
        )

class CourseStructureResource(resources.ModelResource):
    department = fields.Field(
        column_name='department_code',
        attribute='department',
        widget=ForeignKeyWidget(UGDepartment, 'code')
    )
    batch = fields.Field(
        column_name='batch',
        attribute='batch',
        widget=ForeignKeyWidget(UGBatch, 'name')
    )
    
    class Meta:
        model = CourseStructure
        import_id_fields = ('uid',)
        fields = (
            'uid', 'course_name', 'course_short_name', 'department', 'course_type',
            'course_code', 'paper_code', 'max_credit', 'max_marks', 'min_marks',
            'label', 'semester', 'batch'
        )

class StudentCourseAssessmentResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(UGStudentProfile, 'registration_no')
    )
    department = fields.Field(
        column_name='department_code',
        attribute='department',
        widget=ForeignKeyWidget(UGDepartment, 'code')
    )
    batch = fields.Field(
        column_name='batch',
        attribute='batch',
        widget=ForeignKeyWidget(UGBatch, 'name')
    )
    
    # Export only fields (already defined in previous step)
    student_registration_no = fields.Field(attribute='student__registration_no', column_name='Registration No', readonly=True)
    student_roll_no = fields.Field(attribute='student__roll_no', column_name='Roll No', readonly=True)
    student_name = fields.Field(attribute='student__first_name', column_name='Student Name', readonly=True)
    student_batch = fields.Field(attribute='student__batch__name', column_name='Export Batch', readonly=True)
    paper_department = fields.Field(attribute='department__name', column_name='Paper Department', readonly=True)
    semester_result = fields.Field(column_name='Semester Result', readonly=True)
    
    class Meta:
        model = StudentCourseAssessment
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'semester', 'session', 'course_name', 'course_code', 
            'department', 'course_type', 'label', 'ind_pass_marks', 
            'ind_marks_obtained', 'ind_max_marks', 'ind_is_pass', 'ind_is_absent',
            'batch', 'college_code', 'exam_type'
        )
        export_order = (
            'uid', 'student_registration_no', 'student_roll_no', 'student_name', 'student_batch', 
            'semester', 'session', 'semester_result', 'course_name', 'course_code', 
            'paper_department', 'course_type', 'label', 'ind_marks_obtained', 
            'ind_pass_marks', 'ind_is_pass'
        )

    def dehydrate_semester_result(self, assessment):
        from .models import UGExamResult
        res = UGExamResult.objects.filter(
            student_id=assessment.student_id,
            semester=assessment.semester,
            session=assessment.session
        ).first()
        return res.semester_result if res else ''

class UGExamResultResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(UGStudentProfile, 'registration_no')
    )
    
    # Export only fields
    registration_no = fields.Field(attribute='student__registration_no', column_name='Registration No', readonly=True)
    student_name = fields.Field(attribute='student__first_name', column_name='Student Name', readonly=True)
    student_batch = fields.Field(attribute='student__batch__name', column_name='Batch Name', readonly=True)
    failed_ese_papers = fields.Field(column_name='Failed ESE Papers', readonly=True)
    
    class Meta:
        model = UGExamResult
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'semester', 'session', 
            'sgpa', 'semester_result', 'semester_credit_earned', 'semester_max_credit', 
            'cia_pass', 'ese_pass', 'next_sem_status', 'is_legacy'
        )
        export_order = (
            'uid', 'registration_no', 'student_name', 'student_batch', 'semester', 'session', 
            'semester_result', 'sgpa', 'failed_ese_papers'
        )

    def dehydrate_failed_ese_papers(self, exam_result):
        failures = StudentCourseAssessment.objects.filter(
            student=exam_result.student,
            semester=exam_result.semester,
            session=exam_result.session,
            label__icontains='ESE',
            ind_is_pass=False
        )
        return ", ".join([a.paper_code for a in failures])

class SemesterRegistrationResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(UGStudentProfile, 'registration_no')
    )
    batch = fields.Field(
        column_name='batch',
        attribute='batch',
        widget=ForeignKeyWidget(UGBatch, 'name')
    )
    
    class Meta:
        model = SemesterRegistration
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'batch', 'start_date', 'end_date', 'is_open', 
            'sem', 'status', 'exam_eligible', 'remarks', 'session'
        )

class ExamRegistrationResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(UGStudentProfile, 'registration_no')
    )
    
    class Meta:
        model = ExamRegistration
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'admission_receipt', 'start_date', 'end_date', 
            'is_open', 'fees', 'sem', 'status', 'session', 'exam_type'
        )

class ExamRegistrationPaymentResource(resources.ModelResource):
    registration = fields.Field(
        column_name='registration_uid',
        attribute='registration',
        widget=ForeignKeyWidget(ExamRegistration, 'uid')
    )
    
    class Meta:
        model = ExamRegistrationPayment
        import_id_fields = ('uid',)
        fields = (
            'uid', 'registration', 'order_id', 'tracking_id', 'bank_ref_no', 
            'amount', 'payment_status', 'payment_mode', 'card_name'
        )

class CommonCourseStructureResource(resources.ModelResource):
    class Meta:
        model = CommonCourseStructure
        import_id_fields = ('uid',)
        fields = ('uid', 'semester', 'course_name', 'course_type', 'ltp', 'credit', 'marks', 'code')
