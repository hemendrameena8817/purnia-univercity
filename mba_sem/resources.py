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
from django.db import models
import re

class RobustManyToManyWidget(ManyToManyWidget):
    def __init__(self, model, separator=',', field='pk', *args, **kwargs):
        super().__init__(model, separator, field, *args, **kwargs)

    def clean(self, value, row=None, **kwargs):
        if not value:
            return self.model.objects.none()
        ids = [i.strip() for i in str(value).split(self.separator) if i.strip() and i.strip().lower() != 'none']
        if not ids:
            return self.model.objects.none()
        return self.model.objects.filter(models.Q(center_code__in=ids) | models.Q(college_code__in=ids))

class MBACourseResource(resources.ModelResource):
    class Meta:
        model = MBACourse
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'discipline_code', 'duration_years', 'created_at', 'updated_at')

class MBASessionResource(resources.ModelResource):
    class Meta:
        model = MBASession
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'start_year', 'end_year', 'is_active', 'created_at', 'updated_at')

class MBABatchResource(resources.ModelResource):
    session = fields.Field(
        column_name='session_name',
        attribute='session',
        widget=ForeignKeyWidget(MBASession, 'name')
    )
    class Meta:
        model = MBABatch
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'session', 'is_active', 'json_data', 'created_at', 'updated_at')

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
            'profile_image', 'signature',
            'sem_1_gpa', 'sem_1_credit_earned', 'sem_2_gpa', 'sem_2_credit_earned',
            'sem_3_gpa', 'sem_3_credit_earned', 'sem_4_gpa', 'sem_4_credit_earned',
            'json_data', 'created_at', 'updated_at'
        )

class MBACourseStructureResource(resources.ModelResource):
    class Meta:
        model = MBACourseStructure
        import_id_fields = ('uid',)
        fields = (
            'uid', 'course_name', 'course_short_name', 'course_type', 'course_code',
            'max_marks', 'min_marks', 'label', 'semester', 'credit', 'description',
            'json_data', 'created_at', 'updated_at'
        )

class MBACommonCourseStructureResource(resources.ModelResource):
    class Meta:
        model = MBACommonCourseStructure
        import_id_fields = ('uid',)
        fields = ('uid', 'semester', 'course_name', 'course_type', 'ltp', 'marks', 'code', 'json_data', 'created_at', 'updated_at')

class MBAExamResource(resources.ModelResource):
    class Meta:
        model = MBAExam
        import_id_fields = ('uid',)
        fields = ('uid', 'name', 'semester', 'session', 'exam_month_year', 'publication_date', 'created_at', 'updated_at')

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
        widget=RobustManyToManyWidget(College, field='center_code', separator=',')
    )

    class Meta:
        model = MBAExamCenterMapping

        # 🔥 MAIN FIX (duplicate + update handle karega)
        import_id_fields = ('exam', 'center')

        fields = (
            'uid',
            'exam',
            'center',
            'attached_colleges',
            'created_at',
            'updated_at'
        )

    # 🔥 "None" aur garbage values clean karega
    def before_import_row(self, row, **kwargs):
        # clean attached colleges
        value = row.get('attached_college_codes')

        if value:
            cleaned = [
                v.strip() for v in str(value).split(',')
                if v.strip() and v.strip().lower() != 'none'
            ]
            row['attached_college_codes'] = ",".join(cleaned)

        # strip spaces
        row['exam_name'] = (row.get('exam_name') or '').strip()
        row['center_code'] = (row.get('center_code') or '').strip()

    def dehydrate_attached_colleges(self, mapping):
        # Prefer center_code, fallback to college_code
        codes = []
        for col in mapping.attached_colleges.all():
            val = col.center_code or col.college_code
            if val and str(val).lower() != 'none':
                codes.append(str(val).strip())
        return ",".join(set(codes))

    def get_queryset(self):
        return super().get_queryset().prefetch_related('attached_colleges').select_related('exam', 'center')
        

class SmartCourseStructureWidget(ForeignKeyWidget):
    def __init__(self, model, field='pk', *args, **kwargs):
        super().__init__(model, field, *args, **kwargs)

    def get_queryset(self, value, row, *args, **kwargs):
        queryset = super().get_queryset(value, row, *args, **kwargs)
        exam_name = str(row.get('exam_name', '')).lower()
        if '1st' in exam_name or 'semester 1' in exam_name:
            return queryset.filter(semester='1')
        if '2nd' in exam_name or 'semester 2' in exam_name:
            return queryset.filter(semester='2')
        if '3rd' in exam_name or 'semester 3' in exam_name:
            return queryset.filter(semester='3')
        if '4th' in exam_name or 'semester 4' in exam_name:
            return queryset.filter(semester='4')
        return queryset

class MBAExamScheduleResource(resources.ModelResource):
    exam = fields.Field(
        column_name='exam_name',
        attribute='exam',
        widget=ForeignKeyWidget(MBAExam, 'name')
    )
    common_course_structure = fields.Field(
        column_name='course_code',
        attribute='common_course_structure',
        widget=SmartCourseStructureWidget(MBACommonCourseStructure, 'code')
    )
    class Meta:
        model = MBAExamSchedule
        import_id_fields = ('uid',)
        fields = ('uid', 'exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting', 'created_at', 'updated_at')

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
            'status', 'exam_eligible', 'remarks', 'session', 'json_data',
            'created_at', 'updated_at'
        )

class SmartManyToManyCourseStructureWidget(ManyToManyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return self.model.objects.none()

        codes = [
            v.strip() for v in str(value).split(self.separator)
            if v.strip() and v.strip().lower() != 'none'
        ]

        # detection from exam_name
        exam_name = str(row.get('exam_name', '')).lower()
        qs = self.model.objects.all()

        if re.search(r'\b(1|1st|first)\b', exam_name):
            qs = qs.filter(semester='1')
        elif re.search(r'\b(2|2nd|second)\b', exam_name):
            qs = qs.filter(semester='2')
        elif re.search(r'\b(3|3rd|third)\b', exam_name):
            qs = qs.filter(semester='3')
        elif re.search(r'\b(4|4th|fourth)\b', exam_name):
            qs = qs.filter(semester='4')

        return qs.filter(code__in=codes)

    def render(self, value, obj=None):
        if not value:
            return ""
        return ",".join([str(s.code) for s in value.all() if s.code])

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
        widget=SmartManyToManyCourseStructureWidget(MBACommonCourseStructure, field='code', separator=',')
    )
    class Meta:
        model = MBAExamRegistration
        import_id_fields = ('uid',)
        fields = (
            'uid', 'student', 'exam', 'exam_type', 'exam_subjects', 'start_date',
            'end_date', 'is_open', 'fees', 'sem', 'status', 'session', 'json_data',
            'created_at', 'updated_at'
        )

    def get_queryset(self):
        return super().get_queryset().prefetch_related('exam_subjects').select_related('student', 'exam')

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
            'comb_grace_obtained', 'comb_numeric_grade', 'comb_letter_grade', 'comb_grade_point',
            'course_max_marks', 'course_marks_obtained', 'course_final_marks_obtained',
            'sem_result', 'next_sem_status', 'json_data', 'created_at', 'updated_at'
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
            'next_semester', 'next_sem_status', 'is_legacy', 'published_at',
            'created_at', 'updated_at'
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
            'sgpa', 'sem_result', 'next_sem_status', 'sem_grace_obtained',
            'temp_total_gp', 'json_data', 'created_at', 'updated_at'
        )
        export_order = (
            'uid', 'student_registration_no', 'student_roll_no', 'student_name',
            'semester', 'session', 'paper_code', 'label', 'ind_marks_obtained',
            'ind_pass_marks', 'ind_is_pass'
        )
