from django.contrib import admin
from django.contrib import messages
from .models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile, 
    LLBCourseStructure, CommonCourseStructure, LLBExam, 
    LLBStudentCourseAssessment, LLBExamCenterMapping, 
    LLBExamSchedule, LLBYearRegistration, LLBExamRegistration,
    LLBStatistics
)
from .utils.stats import calculate_and_save_llb_stats

@admin.register(LLBCourse)
class LLBCourseAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'duration_years')
    search_fields = ('name',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'duration_years')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBSession)
class LLBSessionAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'start_year', 'end_year', 'is_active')
    list_filter = ('is_active',)
    fieldsets = (
        ('Session Information', {
            'fields': ('uid', 'name', 'start_year', 'end_year', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBBatch)
class LLBBatchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    fieldsets = (
        ('Batch Information', {
            'fields': ('uid', 'name', 'is_active')
        }),
    )
    readonly_fields = ('uid',)

@admin.register(LLBStudentProfile)
class LLBStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('uid', 'roll_no', 'registration_no', 'user', 'college', 'course', 'batch')
    search_fields = ('roll_no', 'registration_no', 'user__first_name', 'user__last_name')
    list_filter = ('college', 'course', 'batch')
    raw_id_fields = ('user', 'college', 'course', 'batch')
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'roll_no', 'registration_no', 'user')
        }),
        ('Academic Information', {
            'fields': ('college', 'course', 'batch')
        }),
        ('Personal Details', {
            'fields': ('father_name', 'mother_name', 'hindi_name', 'date_of_birth', 'gender', 'aadhar_no', 'category', 'status')
        }),
        ('Documents', {
            'fields': ('profile_image', 'signature')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBCourseStructure)
class LLBCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'semester', 'status', 'full_marks', 'pass_marks')
    list_filter = ('semester', 'status')
    search_fields = ('name',)
    fieldsets = (
        ('Course Information', {
            'fields': ('uid', 'name', 'semester', 'status', 'full_marks', 'pass_marks')
        }),
        ('Course Codes', {
            'fields': ('course_code', 'paper_code', 'subject_code')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(CommonCourseStructure)
class CommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'semester', 'course_code', 'full_marks', 'cia_max_marks', 'ese_max_marks')
    search_fields = ('name', 'course_code')
    list_filter = ('semester', 'course_code')
    fieldsets = (
        ('Course Information', {
            'fields': ('uid', 'name', 'semester', 'course_code', 'full_marks', 'pass_marks')
        }),
        ('Course Codes', {
            'fields': ('paper_code', 'subject_code')
        }),
        ('Marks Breakdown', {
            'fields': ('cia_max_marks', 'ese_max_marks')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBExam)
class LLBExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'semester', 'session', 'batch', 'exam_month_year', 'publication_date')
    list_filter = ('semester', 'batch', 'session')
    search_fields = ('name', 'session')
    raw_id_fields = ('batch',)
    fieldsets = (
        ('Exam Information', {
            'fields': ('uid', 'name', 'semester', 'session', 'batch', 'exam_month_year', 'publication_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBStudentCourseAssessment)
class LLBStudentCourseAssessmentAdmin(admin.ModelAdmin):
    list_display = ('uid', 'student', 'course', 'course_structure', 'label', 'semester', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('label', 'semester', 'session', 'batch', 'exam_type')
    search_fields = ('student__roll_no', 'student__registration_no', 'course_structure__name', 'paper_code')
    raw_id_fields = ('student', 'exam', 'course', 'course_structure', 'batch')
    list_select_related = ('student', 'course', 'course_structure', 'batch')
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'student', 'course', 'course_structure', 'exam')
        }),
        ('Assessment Details', {
            'fields': ('label', 'semester', 'session', 'batch', 'exam_type', 'paper_code', 'college_code')
        }),
        ('Individual Marks', {
            'fields': ('ind_max_marks', 'ind_pass_marks', 'ind_is_absent', 'ind_marks_obtained', 'ind_grace_obtained', 'ind_final_marks_obtained', 'ind_is_pass')
        }),
        ('Combined Marks', {
            'fields': ('comb_max_marks', 'comb_pass_marks', 'comb_marks_obtained', 'comb_grace_obtained', 'comb_final_marks_obtained', 'comb_is_pass')
        }),
        ('Course Summary', {
            'fields': ('course_max_marks', 'course_marks_obtained', 'course_final_marks_obtained')
        }),
        ('Result Status', {
            'fields': ('subject_result', 'grade')
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBExamCenterMapping)
class LLBExamCenterMappingAdmin(admin.ModelAdmin):
    list_display = ('uid', 'center', 'get_exams_count')
    filter_horizontal = ('exams', 'attached_colleges')
    raw_id_fields = ('center',)
    fieldsets = (
        ('Mapping Information', {
            'fields': ('uid', 'center', 'exams', 'attached_colleges')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    def get_exams_count(self, obj):
        return obj.exams.count()
    get_exams_count.short_description = 'Exams Count'

@admin.register(LLBExamSchedule)
class LLBExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('uid', 'exam', 'subject', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date')
    search_fields = ('subject__name',)
    raw_id_fields = ('exam', 'subject')
    fieldsets = (
        ('Schedule Information', {
            'fields': ('uid', 'exam', 'subject', 'exam_date', 'exam_time', 'sitting')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBYearRegistration)
class LLBYearRegistrationAdmin(admin.ModelAdmin):
    list_display = ('uid', 'student', 'year', 'session', 'is_open', 'exam_eligible', 'status')
    list_filter = ('year', 'is_open', 'exam_eligible', 'status')
    search_fields = ('student__roll_no', 'student__registration_no')
    raw_id_fields = ('student',)
    fieldsets = (
        ('Registration Information', {
            'fields': ('uid', 'student', 'year', 'session', 'is_open', 'exam_eligible', 'status')
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')

@admin.register(LLBExamRegistration)
class LLBExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('uid', 'student', 'exam', 'exam_type', 'year', 'fees', 'status')
    list_filter = ('exam_type', 'year', 'status')
    search_fields = ('student__roll_no', 'student__registration_no')
    raw_id_fields = ('student', 'exam')
    fieldsets = (
        ('Registration Information', {
            'fields': ('uid', 'student', 'exam', 'exam_type', 'year', 'fees', 'status')
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')


@admin.register(LLBStatistics)
class LLBStatisticsAdmin(admin.ModelAdmin):
    list_display = ('last_updated', 'total_students', 'total_assessments', 'pass_percentage')
    readonly_fields = ('uid', 'last_updated', 'data')
    change_list_template = "admin/llb/stats_changelist.html"

    def total_students(self, obj):
        if not obj.data: return 0
        return obj.data.get('global', {}).get('total_students', 0)
    
    def total_assessments(self, obj):
        if not obj.data: return 0
        return obj.data.get('global', {}).get('total_assessments', 0)
    
    def pass_percentage(self, obj):
        if not obj.data: return 0
        return obj.data.get('global', {}).get('pass_percentage', 0)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('refresh-stats/', self.admin_site.admin_view(self.refresh_stats_view), name='llb-refresh-stats'),
        ]
        return custom_urls + urls

    def refresh_stats_view(self, request):
        from django.shortcuts import redirect
        calculate_and_save_llb_stats()
        self.message_user(request, "LLB Statistics refreshed successfully.", messages.SUCCESS)
        return redirect("..")
