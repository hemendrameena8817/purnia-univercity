from django.contrib import admin
from .models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile, 
    LLBCourseStructure, CommonCourseStructure, LLBExam, LLBStudentExamResult, 
    LLBStudentCourseAssessment, LLBExamCenterMapping, 
    LLBExamSchedule, LLBYearRegistration, LLBExamRegistration
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

@admin.register(CommonCourseStructure)
class CommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'course_code', 'full_marks', 'cia_max_marks', 'ese_max_marks')
    search_fields = ('name', 'course_code')
    list_filter = ('course_code',)

@admin.register(LLBExam)
class LLBExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester', 'session', 'batch', 'exam_month_year', 'publication_date')
    list_filter = ('semester', 'batch', 'session')
    search_fields = ('name', 'session')
    raw_id_fields = ('batch',)

@admin.register(LLBStudentExamResult)
class LLBStudentExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'total_marks', 'result_status')
    list_filter = ('exam', 'result_status')
    search_fields = ('student__roll_no', 'student__user__first_name', 'student__user__last_name')
    raw_id_fields = ('student', 'exam')

@admin.register(LLBStudentCourseAssessment)
class LLBStudentCourseAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'course_structure', 'label', 'semester', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('label', 'semester', 'session', 'batch', 'exam_type')
    search_fields = ('student__roll_no', 'student__registration_no', 'course_structure__name', 'course_code')
    raw_id_fields = ('student', 'exam_result', 'course', 'course_structure', 'batch')
    list_select_related = ('student', 'exam_result', 'course', 'course_structure', 'batch')

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
