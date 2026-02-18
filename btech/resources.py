from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateTimeWidget, BooleanWidget
from .models import (
    BTechCourse, BTechBranch, BTechSession, BTechBatch, BTechStudentProfile, 
    BTechCourseStructure, BTechCommonCourseStructure,
    BTechExam, BTechExamSchedule, BTechYearRegistration, 
    BTechExamRegistration, BTechStudentAssessment, BTechExamResult,
    BTechExamCenterMapping
)
from colleges.models import College

class BTechStudentProfileResource(resources.ModelResource):
    college_name = fields.Field(
        column_name='College',
        attribute='college',
        widget=ForeignKeyWidget(College, 'name')
    )
    course_name = fields.Field(
        column_name='Course',
        attribute='course',
        widget=ForeignKeyWidget(BTechCourse, 'name')
    )
    branch_name = fields.Field(
        column_name='Branch',
        attribute='branch',
        widget=ForeignKeyWidget(BTechBranch, 'name')
    )
    batch_name = fields.Field(
        column_name='Batch',
        attribute='batch',
        widget=ForeignKeyWidget(BTechBatch, 'name')
    )

    class Meta:
        model = BTechStudentProfile
        fields = (
            'uid', 'registration_no', 'roll_no', 'first_name', 'last_name', 
            'father_name', 'mother_name', 'date_of_birth', 'gender', 
            'mobile_no', 'aadhar_no', 'category', 'college_name', 
            'course_name', 'branch_name', 'batch_name', 'current_year', 
            'session_str', 'status', 'is_active'
        )
        export_order = fields

class BTechExamRegistrationResource(resources.ModelResource):
    student_name = fields.Field(
        column_name='Student Name',
        attribute='student__first_name'
    )
    registration_no = fields.Field(
        column_name='Registration No',
        attribute='student__registration_no'
    )
    exam_name = fields.Field(
        column_name='Exam',
        attribute='exam',
        widget=ForeignKeyWidget(BTechExam, 'name')
    )

    class Meta:
        model = BTechExamRegistration
        fields = (
            'uid', 'student_name', 'registration_no', 'exam_name', 
            'exam_type', 'year', 'session', 'status', 'is_open', 'fees'
        )
        export_order = fields

class BTechStudentAssessmentResource(resources.ModelResource):
    student_name = fields.Field(
        column_name='Student Name',
        attribute='student__first_name'
    )
    roll_no = fields.Field(
        column_name='Roll No',
        attribute='student__roll_no'
    )

    class Meta:
        model = BTechStudentAssessment
        fields = (
            'uid', 'student_name', 'roll_no', 'course_name', 'course_code', 
            'year', 'label', 'session', 'exam_type', 'ind_max_marks', 
            'ind_pass_marks', 'ind_marks_obtained', 'ind_is_pass', 'ind_is_absent'
        )
        export_order = fields

class BTechExamResultResource(resources.ModelResource):
    student_name = fields.Field(
        column_name='Student Name',
        attribute='student__first_name'
    )
    roll_no = fields.Field(
        column_name='Roll No',
        attribute='student__roll_no'
    )

    class Meta:
        model = BTechExamResult
        fields = (
            'uid', 'student_name', 'roll_no', 'year', 'session', 
            'year_result', 'total_marks_obtained', 'percentage', 
            'next_year_status'
        )
        export_order = fields

class BTechBranchResource(resources.ModelResource):
    class Meta:
        model = BTechBranch
        fields = ('uid', 'name', 'code', 'course__name', 'is_active')

class BTechCourseResource(resources.ModelResource):
    class Meta:
        model = BTechCourse
        fields = ('uid', 'name', 'duration_years')

class BTechSessionResource(resources.ModelResource):
    class Meta:
        model = BTechSession
        fields = ('uid', 'name', 'start_year', 'end_year', 'is_active')

class BTechBatchResource(resources.ModelResource):
    class Meta:
        model = BTechBatch
        fields = ('uid', 'name', 'session__name', 'branch__name', 'is_active')

class BTechCourseStructureResource(resources.ModelResource):
    class Meta:
        model = BTechCourseStructure
        fields = ('uid', 'course_name', 'course_code', 'course_type', 'year', 'branch__name', 'max_marks', 'min_marks')

class BTechCommonCourseStructureResource(resources.ModelResource):
    class Meta:
        model = BTechCommonCourseStructure
        fields = ('uid', 'year', 'course_name', 'course_type', 'marks', 'code', 'branch__name')

class BTechExamResource(resources.ModelResource):
    class Meta:
        model = BTechExam
        fields = ('uid', 'name', 'year', 'session', 'batch', 'exam_month_year', 'publication_date')

class BTechExamCenterMappingResource(resources.ModelResource):
    class Meta:
        model = BTechExamCenterMapping
        fields = ('uid', 'center__name', 'created_at')

class BTechExamScheduleResource(resources.ModelResource):
    class Meta:
        model = BTechExamSchedule
        fields = ('uid', 'exam__name', 'common_course_structure__code', 'exam_date', 'exam_time', 'sitting')

class BTechYearRegistrationResource(resources.ModelResource):
    class Meta:
        model = BTechYearRegistration
        fields = ('uid', 'student__registration_no', 'year', 'session', 'status', 'exam_eligible')
