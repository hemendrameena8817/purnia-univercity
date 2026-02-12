from django.contrib import admin
from .models import (
    UGBeforeCBCSCourse,
    UGBeforeCBCSDiscipline,
    UGBeforeCBCSSession,
    UGBeforeCBCSBatch,
    UGBeforeCBCSSubject,
    UGBeforeCBCSCourseStructure,
    UGBeforeCBCSStudentProfile,
    UGBeforeCBCSExam,
    UGBeforeCBCSExamRegistration,
    UGBeforeCBCSStudentAssessment,
    UGBeforeCBCSExamResult
)


@admin.register(UGBeforeCBCSCourse)
class UGBeforeCBCSCourseAdmin(admin.ModelAdmin):
    list_display = ('uid', 'course_code', 'name', 'duration_years', 'created_at', 'updated_at')
    search_fields = ('uid', 'course_code', 'name')
    ordering = ('course_code',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_per_page = 50


@admin.register(UGBeforeCBCSDiscipline)
class UGBeforeCBCSDisciplineAdmin(admin.ModelAdmin):
    list_display = ('uid', 'code', 'name', 'course', 'is_active', 'created_at', 'updated_at')
    list_filter = ('course', 'is_active')
    search_fields = ('uid', 'code', 'name')
    ordering = ('course', 'code')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_select_related = ('course',)
    list_per_page = 50


@admin.register(UGBeforeCBCSSession)
class UGBeforeCBCSSessionAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'start_year', 'end_year', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('uid', 'name')
    ordering = ('-start_year',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_per_page = 50


@admin.register(UGBeforeCBCSBatch)
class UGBeforeCBCSBatchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'is_active', 'created_at', 'updated_at')
    list_filter = ('session', 'is_active')
    search_fields = ('uid', 'name')
    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_select_related = ('session',)
    list_per_page = 50


@admin.register(UGBeforeCBCSSubject)
class UGBeforeCBCSSubjectAdmin(admin.ModelAdmin):
    list_display = ('uid', 'code', 'name', 'paper_number', 'subject_type', 'has_practical', 'is_active')
    list_filter = ('subject_type', 'is_active', 'has_practical')
    search_fields = ('uid', 'code', 'name', 'paper_number')
    ordering = ('code',)
    readonly_fields = ('uid',)
    list_per_page = 50


@admin.register(UGBeforeCBCSCourseStructure)
class UGBeforeCBCSCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('uid', 'discipline', 'part', 'subject', 'subject_type', 'theory_max_marks', 'theory_pass_marks', 'practical_max_marks', 'practical_pass_marks')
    list_filter = ('part', 'discipline', 'subject_type')
    search_fields = ('uid', 'subject__name', 'discipline__name')
    ordering = ('discipline', 'part', 'subject')
    readonly_fields = ('uid',)
    list_select_related = ('discipline', 'subject', 'discipline__course')
    list_per_page = 50


@admin.register(UGBeforeCBCSStudentProfile)
class UGBeforeCBCSStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('uid', 'registration_no', 'roll_no', 'student_name', 'college', 'course', 'discipline', 'batch', 'session', 'gender', 'is_active')
    list_filter = ('college', 'course', 'discipline', 'batch', 'session', 'is_active', 'gender')
    search_fields = ('uid', 'registration_no', 'roll_no', 'student_name', 'fathers_name', 'mothers_name', 'user__username')
    ordering = ('registration_no',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_select_related = ('user', 'college', 'course', 'discipline', 'batch', 'session')
    list_per_page = 100
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'user', 'registration_no', 'roll_no')
        }),
        ('Personal Details', {
            'fields': ('student_name', 'student_name_hindi', 'fathers_name', 'mothers_name', 'gender', 'dob')
        }),
        ('Academic Details', {
            'fields': ('college', 'course', 'discipline', 'batch', 'session')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(UGBeforeCBCSExam)
class UGBeforeCBCSExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'part', 'exam_year', 'exam_month_year', 'publication_date', 'is_active', 'created_at', 'updated_at')
    list_filter = ('part', 'exam_year', 'is_active')
    search_fields = ('uid', 'name', 'exam_month_year')
    ordering = ('-exam_year', 'part')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_per_page = 50


@admin.register(UGBeforeCBCSExamRegistration)
class UGBeforeCBCSExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('uid', 'get_student_name', 'get_registration_no', 'exam', 'exam_type', 'is_ex_regular', 'center', 'college_at_exam', 'status', 'created_at')
    list_filter = ('exam', 'exam_type', 'is_ex_regular', 'status', 'center', 'college_at_exam')
    search_fields = ('uid', 'student__registration_no', 'student__student_name', 'exam__name', 'student__user__username')
    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_select_related = ('student', 'student__user', 'exam', 'center', 'college_at_exam')
    list_per_page = 100
    
    def get_student_name(self, obj):
        return obj.student.student_name if obj.student else '-'
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'student__student_name'
    
    def get_registration_no(self, obj):
        return obj.student.registration_no if obj.student else '-'
    get_registration_no.short_description = 'Registration No'
    get_registration_no.admin_order_field = 'student__registration_no'
    
    fieldsets = (
        ('Registration Details', {
            'fields': ('uid', 'student', 'exam', 'exam_type', 'is_ex_regular')
        }),
        ('Exam Center', {
            'fields': ('center', 'college_at_exam')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(UGBeforeCBCSStudentAssessment)
class UGBeforeCBCSStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('uid', 'get_student_name', 'get_registration_no', 'subject', 'subject_type', 'theory_marks', 'practical_marks', 'sessional_marks', 'marks_secured', 'max_marks', 'pass_marks', 'subject_result', 'is_absent')
    list_filter = ('subject_result', 'subject_type', 'is_absent')
    search_fields = ('uid', 'registration__student__registration_no', 'registration__student__student_name', 'subject__name', 'subject__code')
    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_select_related = ('registration', 'registration__student', 'subject')
    list_per_page = 100
    
    def get_student_name(self, obj):
        return obj.registration.student.student_name if obj.registration and obj.registration.student else '-'
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'registration__student__student_name'
    
    def get_registration_no(self, obj):
        return obj.registration.student.registration_no if obj.registration and obj.registration.student else '-'
    get_registration_no.short_description = 'Registration No'
    get_registration_no.admin_order_field = 'registration__student__registration_no'
    
    fieldsets = (
        ('Assessment Details', {
            'fields': ('uid', 'registration', 'subject', 'subject_type')
        }),
        ('Marks Breakdown', {
            'fields': ('theory_marks', 'practical_marks', 'sessional_marks')
        }),
        ('Total Marks', {
            'fields': ('marks_secured', 'max_marks', 'pass_marks', 'subject_total_mark')
        }),
        ('Result', {
            'fields': ('subject_result', 'is_absent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(UGBeforeCBCSExamResult)
class UGBeforeCBCSExamResultAdmin(admin.ModelAdmin):
    list_display = ('uid', 'get_student_name', 'get_registration_no', 'get_exam_name', 'result_status', 'grand_total_secured', 'grand_total_max', 'hons_total_secured', 'hons_total_max', 'is_published', 'published_at')
    list_filter = ('result_status', 'is_published', 'published_at')
    search_fields = ('uid', 'registration__student__registration_no', 'registration__student__student_name', 'registration__exam__name')
    ordering = ('-published_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_select_related = ('registration', 'registration__student', 'registration__exam')
    list_per_page = 100
    
    def get_student_name(self, obj):
        return obj.registration.student.student_name if obj.registration and obj.registration.student else '-'
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'registration__student__student_name'
    
    def get_registration_no(self, obj):
        return obj.registration.student.registration_no if obj.registration and obj.registration.student else '-'
    get_registration_no.short_description = 'Registration No'
    get_registration_no.admin_order_field = 'registration__student__registration_no'
    
    def get_exam_name(self, obj):
        return obj.registration.exam.name if obj.registration and obj.registration.exam else '-'
    get_exam_name.short_description = 'Exam'
    get_exam_name.admin_order_field = 'registration__exam__name'
    
    fieldsets = (
        ('Result Details', {
            'fields': ('uid', 'registration', 'result_status', 'final_result_text')
        }),
        ('Grand Total', {
            'fields': ('grand_total_secured', 'grand_total_max')
        }),
        ('Honours Total', {
            'fields': ('hons_total_secured', 'hons_total_max')
        }),
        ('Publication', {
            'fields': ('is_published', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
