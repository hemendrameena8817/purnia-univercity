from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from django.db.models import Q
from .models import (
    UGFaculty, UGDepartment, UGDegree, UGProgram, UGBatch, UGStudentProfile,
    CourseStructure, StudentCourseAssessment, SemesterRegistration, ExamRegistration,
    CommonCourseStructure, UGExamResult, ExamRegistrationPayment,
    UGExam, UGExamCenterMapping, UGExamSchedule
)
from university.models import University
from colleges.models import College
from accounts.models import UserAccount

class CourseStructureWidget(ForeignKeyWidget):
    """
    Custom widget for CourseStructure lookup in UGExamScheduleResource.
    Filters by paper_code, course_name, course_type, course_code, and max_marks.
    """
    def clean(self, value, row=None, **kwargs):
        if not value:
            return None
        
        # Normalize the primary lookup value (paper_code)
        val = str(value).strip()
        query = Q(paper_code__iexact=val)
        
        # Add additional filters from row data if present
        if row:
            # Handle both hyphenated/underscore and space variations
            c_name = row.get('course_name') or row.get('Course name') or row.get('Course Name')
            c_type = row.get('course_type') or row.get('Course type') or row.get('Course Type')
            c_code = row.get('course_code') or row.get('Course code') or row.get('Course Code')
            m_marks = row.get('max_marks') or row.get('Max marks') or row.get('Max Marks')

            if c_name: query &= Q(course_name__iexact=str(c_name).strip())
            if c_type: query &= Q(course_type__iexact=str(c_type).strip())
            if c_code: query &= Q(course_code__iexact=str(c_code).strip())
            if m_marks: 
                try:
                    query &= Q(max_marks=float(m_marks))
                except (ValueError, TypeError):
                    pass
            
        try:
            res = self.model.objects.filter(query).last()
            if not res:
                return self.model.objects.filter(paper_code__iexact=val).last()
            return res
        except Exception:
            return None

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
        fields = ('uid', 'name', 'short_name', 'description', 'university', 'departments', 'is_publish', 'json_data')

class UGDepartmentResource(resources.ModelResource):
    class Meta:
        model = UGDepartment
        import_id_fields = ('code',)
        fields = ('uid', 'name', 'code', 'head_of_department', 'is_publish', 'json_data')

class UGDegreeResource(resources.ModelResource):
    class Meta:
        model = UGDegree
        import_id_fields = ('name',)
        fields = ('uid', 'name', 'short_name', 'total_semesters', 'total_years', 'json_data')

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
        fields = ('uid', 'name', 'short_name', 'degree', 'department', 'json_data')

class UGBatchResource(resources.ModelResource):
    program = fields.Field(
        column_name='program',
        attribute='program',
        widget=ForeignKeyWidget(UGProgram, 'name')
    )
    
    class Meta:
        model = UGBatch
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'program', 'json_data')

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
            'address', 'admission_date', 'date_of_birth', 'aadhar_no', 'apaar_id',
            'mobile_no', 'migration_submitted', 'last_university', 'gender', 'caste',
            'religion', 'nationality', 'medium_of_student', 'enrollment_date',
            'roll_no', 'batch', 'father_name', 'mother_name', 'current_semester',
            'session', 'status', 'college', 'department', 'program', 'degree',
            'major_course', 'minor_course', 'mdc_course', 'profile_image',
            'signature', 'is_active', 'json_data'
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
            'description', 'label', 'semester', 'batch', 'json_data'
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
            'uid', 'course_name', 'course_short_name', 'student', 'course_type',
            'course_code', 'paper_code', 'semester', 'label', 'department',
            'degree', 'session', 'batch', 'college_code', 'exam_type',
            'attendance', 'ind_max_marks', 'ind_pass_marks', 'ind_is_absent',
            'ind_marks_obtained', 'ind_grace_obtained', 'ind_final_marks_obtained',
            'ind_is_pass', 'comb_max_marks', 'comb_max_credits', 'comb_pass_marks',
            'comb_marks_obtained', 'comb_grace_obtained', 'comb_final_marks_obtained',
            'comb_credit_obtained', 'comb_numeric_grade', 'comb_letter_grade',
            'comb_grade_point', 'course_max_marks', 'course_max_credits',
            'course_pass_marks', 'course_marks_obtained', 'course_grace_obtained',
            'course_final_marks_obtained', 'course_credit_obtained', 'course_grade_point',
            'sem_max_credit', 'sem_credit_obtained', 'sgpa', 'sem_result',
            'next_sem_status', 'sem_grace_obtained', 'temp_total_gp', 'is_cia_filled',
            'cia_filled_on', 'is_migrated', 'json_data',
            'student_registration_no', 'student_roll_no', 'student_name', 
            'student_batch', 'paper_department', 'semester_result'
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
            'uid', 'student', 'semester', 'session', 'cia_pass', 'ese_pass',
            'semester_result', 'semester_max_credit', 'semester_credit_earned',
            'sgpa', 'next_semester', 'next_sem_status', 'is_legacy', 'published_at',
            'registration_no', 'student_name', 'student_batch', 'failed_ese_papers'
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
    assessment = fields.Field(
        column_name='assessment_uids',
        attribute='assessment',
        widget=ManyToManyWidget(StudentCourseAssessment, field='uid')
    )
    
    class Meta:
        model = SemesterRegistration
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'batch', 'start_date', 'end_date', 'is_open', 
            'sem', 'status', 'exam_eligible', 'remarks', 'assessment', 'session', 'json_data'
        )

class ExamRegistrationResource(resources.ModelResource):
    student = fields.Field(
        column_name='registration_no',
        attribute='student',
        widget=ForeignKeyWidget(UGStudentProfile, 'registration_no')
    )
    assessment = fields.Field(
        column_name='assessment_uids',
        attribute='assessment',
        widget=ManyToManyWidget(StudentCourseAssessment, field='uid')
    )
    
    class Meta:
        model = ExamRegistration
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'admission_receipt', 'start_date', 'end_date', 
            'is_open', 'fees', 'sem', 'status', 'session', 'exam_type', 'assessment', 'json_data'
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
            'amount', 'payment_status', 'payment_mode', 'card_name', 'raw_response'
        )

class CommonCourseStructureResource(resources.ModelResource):
    class Meta:
        model = CommonCourseStructure
        import_id_fields = ('uid',)
        fields = ('uid', 'semester', 'course_name', 'course_type', 'ltp', 'credit', 'marks', 'code', 'json_data')

class UGExamResource(resources.ModelResource):
    class Meta:
        model = UGExam
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'semester', 'session', 'exam_month_year', 'publication_date', 'is_active', 'json_data')

class UGExamCenterMappingResource(resources.ModelResource):
    exam = fields.Field(
        column_name='exam_uid',
        attribute='exam',
        widget=ForeignKeyWidget(UGExam, 'uid')
    )
    center = fields.Field(
        column_name='center_college_code',
        attribute='center',
        widget=ForeignKeyWidget(College, 'college_code')
    )
    attached_colleges = fields.Field(
        column_name='attached_college_codes',
        attribute='attached_colleges',
        widget=ManyToManyWidget(College, field='college_code')
    )
    
    class Meta:
        model = UGExamCenterMapping
        import_id_fields = ('uid',)
        fields = ('uid', 'exam', 'center', 'attached_colleges', 'json_data')

class UGExamScheduleResource(resources.ModelResource):
    exam = fields.Field(
        column_name='exam_uid',
        attribute='exam',
        widget=ForeignKeyWidget(UGExam, 'uid')
    )
    department = fields.Field(
        column_name='department_codes',
        attribute='department',
        widget=ManyToManyWidget(UGDepartment, field='code')
    )
    exam_subject = fields.Field(
        column_name='paper_code',
        attribute='exam_subject',
        widget=CourseStructureWidget(CourseStructure, 'paper_code')
    )
    mjc = fields.Field(
        column_name='mjc_department_codes',
        attribute='mjc',
        widget=ManyToManyWidget(UGDepartment, field='code')
    )
    
    # Export-only fields from CourseStructure for accurate re-import matching
    course_name = fields.Field(attribute='exam_subject__course_name', column_name='course_name', readonly=True)
    course_type = fields.Field(attribute='exam_subject__course_type', column_name='course_type', readonly=True)
    course_code = fields.Field(attribute='exam_subject__course_code', column_name='course_code', readonly=True)
    max_marks = fields.Field(attribute='exam_subject__max_marks', column_name='max_marks', readonly=True)

    class Meta:
        model = UGExamSchedule
        import_id_fields = ('uid',)
        fields = (
            'uid', 'exam', 'department', 'exam_type', 'exam_subject', 
            'mjc', 'exam_date', 'exam_time', 'sitting', 'json_data'
        )
        export_order = (
            'uid', 'exam', 'department', 'mjc', 'exam_subject', 
            'course_name', 'course_type', 'course_code', 'max_marks',
            'exam_type', 'exam_date', 'exam_time', 'sitting'
        )
