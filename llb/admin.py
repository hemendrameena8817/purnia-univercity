from django.contrib import admin
from .models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile, 
    LLBCourseStructure, LLBExam, LLBStudentExamResult, LLBStudentAssessment,
    LLBExamCenterMapping, LLBExamSchedule, LLBYearRegistration, LLBExamRegistration
)

@admin.register(LLBCourse)
class LLBCourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_years')
    search_fields = ('name',)

@admin.register(LLBSession)
class LLBSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_year', 'end_year', 'is_active')
    list_filter = ('is_active',)

@admin.register(LLBBatch)
class LLBBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(LLBStudentProfile)
class LLBStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('roll_no', 'registration_no', 'user', 'college', 'course', 'batch')
    search_fields = ('roll_no', 'registration_no', 'user__first_name', 'user__last_name')
    list_filter = ('college', 'course', 'batch')
    raw_id_fields = ('user', 'college', 'course', 'batch')

@admin.register(LLBCourseStructure)
class LLBCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'full_marks', 'pass_marks')
    search_fields = ('name',)

@admin.register(LLBExam)
class LLBExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester', 'session', 'batch', 'exam_month_year', 'publication_date')
    list_filter = ('semester', 'batch', 'session')
    search_fields = ('name', 'session')
    raw_id_fields = ('batch',)

class LLBStudentAssessmentInline(admin.TabularInline):
    model = LLBStudentAssessment
    extra = 1

@admin.register(LLBStudentExamResult)
class LLBStudentExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'total_marks', 'result_status', 'exam_center')
    list_filter = ('exam', 'result_status')
    search_fields = ('student__roll_no', 'student__user__first_name', 'student__user__last_name')
    raw_id_fields = ('student', 'exam')
    inlines = [LLBStudentAssessmentInline]

@admin.register(LLBStudentAssessment)
class LLBStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('exam_result', 'subject', 'paper_code', 'marks_obtained')
    list_filter = ('subject', 'paper_code')
    search_fields = ('subject__name', 'paper_code')
    raw_id_fields = ('exam_result', 'subject')

@admin.register(LLBExamCenterMapping)
class LLBExamCenterMappingAdmin(admin.ModelAdmin):
    list_display = ('center', 'get_exams_count')
    filter_horizontal = ('exams', 'attached_colleges')
    raw_id_fields = ('center',)
    
    def get_exams_count(self, obj):
        return obj.exams.count()
    get_exams_count.short_description = 'Exams Count'

@admin.register(LLBExamSchedule)
class LLBExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('exam', 'subject', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date')
    search_fields = ('subject__name',)
    raw_id_fields = ('exam', 'subject')

@admin.register(LLBYearRegistration)
class LLBYearRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'year', 'session', 'is_open', 'exam_eligible', 'status')
    list_filter = ('year', 'is_open', 'exam_eligible', 'status')
    search_fields = ('student__roll_no', 'student__registration_no')
    raw_id_fields = ('student',)

@admin.register(LLBExamRegistration)
class LLBExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'exam_type', 'year', 'fees', 'status')
    list_filter = ('exam_type', 'year', 'status')
    search_fields = ('student__roll_no', 'student__registration_no')
    raw_id_fields = ('student', 'exam')
