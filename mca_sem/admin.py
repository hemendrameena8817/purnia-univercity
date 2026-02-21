from django.contrib import admin
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCACourseStructure, MCACommonCourseStructure,
    MCAExam, MCAExamSchedule, MCASemesterRegistration, 
    MCAExamRegistration, MCAStudentAssessment, MCAExamResult,
    MCAExamCenterMapping
)

@admin.register(MCACourse)
class MCACourseAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'duration_years')
    readonly_fields = ('uid',)
    search_fields = ('name',)

@admin.register(MCASession)
class MCASessionAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'start_year', 'end_year', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('is_active',)

@admin.register(MCABatch)
class MCABatchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('session', 'is_active')

@admin.register(MCAStudentProfile)
class MCAStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('uid', 'roll_no', 'registration_no', 'first_name', 'last_name', 'college', 'batch')
    readonly_fields = ('uid',)
    search_fields = ('roll_no', 'registration_no', 'first_name', 'last_name', 'user__username')
    list_filter = ('college', 'batch', 'status')

@admin.register(MCACourseStructure)
class MCACourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_code', 'course_type', 'semester')
    list_filter = ('semester', 'course_type')
    search_fields = ('course_name', 'course_code')

@admin.register(MCACommonCourseStructure)
class MCACommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('semester', 'course_name', 'course_type', 'marks')
    list_filter = ('semester', 'course_type')
    search_fields = ('course_name', 'code')

@admin.register(MCAExam)
class MCAExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'batch', 'exam_month_year', 'publication_date')
    readonly_fields = ('uid',)
    search_fields = ('name', 'session')

@admin.register(MCAExamCenterMapping)
class MCAExamCenterMappingAdmin(admin.ModelAdmin):
    list_display = ('exam', 'center')
    list_filter = ('exam', 'center')
    filter_horizontal = ('attached_colleges',)

@admin.register(MCAExamSchedule)
class MCAExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date', 'sitting')
    search_fields = ('common_course_structure__course_name', 'common_course_structure__code')

@admin.register(MCASemesterRegistration)
class MCASemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'exam_eligible')
    list_filter = ('sem', 'session', 'status', 'exam_eligible')

@admin.register(MCAExamRegistration)
class MCAExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'exam_type', 'sem', 'session', 'status', 'is_open')
    list_filter = ('exam', 'exam_type', 'sem', 'session', 'status', 'is_open')
    filter_horizontal = ('subjects',)

@admin.register(MCAStudentAssessment)
class MCAStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'course', 'course_structure', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('exam', 'course', 'course_structure__semester', 'label', 'batch')
    search_fields = ('student__roll_no', 'course_structure__course_name', 'course_structure__course_code')
    list_select_related = ('student', 'exam', 'course', 'course_structure', 'batch')

@admin.register(MCAExamResult)
class MCAExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'session', 'semester_result', 'total_marks_obtained', 'percentage')
    list_filter = ('semester', 'session', 'semester_result')
    search_fields = ('student__roll_no',)
