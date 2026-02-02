from django.contrib import admin
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCACourseStructure, MCACommonCourseStructure,
    MCAExam, MCAExamSchedule, MCASemesterRegistration, 
    MCAExamRegistration, MCAStudentAssessment, MCAExamResult
)

@admin.register(MCACourse)
class MCACourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_years')
    search_fields = ('name',)

@admin.register(MCASession)
class MCASessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_year', 'end_year', 'is_active')
    list_filter = ('is_active',)

@admin.register(MCABatch)
class MCABatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'is_active')
    list_filter = ('session', 'is_active')

@admin.register(MCAStudentProfile)
class MCAStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('roll_no', 'registration_no', 'first_name', 'last_name', 'college', 'batch')
    search_fields = ('roll_no', 'registration_no', 'first_name', 'last_name', 'user__username')
    list_filter = ('college', 'batch', 'status')

@admin.register(MCACourseStructure)
class MCACourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'paper_code', 'course_type', 'semester', 'batch')
    list_filter = ('semester', 'batch', 'course_type')
    search_fields = ('course_name', 'course_code', 'paper_code')

@admin.register(MCACommonCourseStructure)
class MCACommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('semester', 'course_name', 'course_type', 'credit', 'marks')
    list_filter = ('semester', 'course_type')
    search_fields = ('course_name', 'code')

@admin.register(MCAExam)
class MCAExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'exam_month_year', 'publication_date')
    search_fields = ('name', 'session')

@admin.register(MCAExamSchedule)
class MCAExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('exam', 'course_structure', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date', 'sitting')
    search_fields = ('course_structure__course_name', 'course_structure__paper_code')

@admin.register(MCASemesterRegistration)
class MCASemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'exam_eligible')
    list_filter = ('sem', 'session', 'status', 'exam_eligible')

@admin.register(MCAExamRegistration)
class MCAExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'is_open')
    list_filter = ('sem', 'session', 'status', 'is_open')

@admin.register(MCAStudentAssessment)
class MCAStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'paper_code', 'semester', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('semester', 'label', 'exam_type', 'batch')
    search_fields = ('student__roll_no', 'course_name', 'paper_code')

@admin.register(MCAExamResult)
class MCAExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'session', 'semester_result', 'sgpa')
    list_filter = ('semester', 'session', 'semester_result')
    search_fields = ('student__roll_no',)
