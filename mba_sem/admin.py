from django.contrib import admin
from .models import *


@admin.register(MBACourse)
class MBACourseAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'discipline_code', 'duration_years')
    readonly_fields = ('uid',)
    search_fields = ('name',)

@admin.register(MBASession)
class MBASessionAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'start_year', 'end_year', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('is_active',)

@admin.register(MBABatch)
class MBABatchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('session', 'is_active')

@admin.register(MBAStudentProfile)
class MBAStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('uid', 'roll_no', 'registration_no', 'first_name', 'last_name', 'college', 'batch')
    readonly_fields = ('uid',)
    search_fields = ('roll_no', 'registration_no', 'first_name', 'last_name', 'user__username')
    list_filter = ('college', 'batch', 'status')

@admin.register(MBACourseStructure)
class MBACourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_code', 'course_type', 'semester')
    list_filter = ('semester', 'course_type')
    search_fields = ('course_name', 'course_code')

@admin.register(MBACommonCourseStructure)
class MBACommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('semester', 'course_name', 'course_type', 'marks', 'code', 'marks')
    list_filter = ('semester', 'course_type')
    search_fields = ('course_name', 'code')

@admin.register(MBAExam)
class MBAExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'exam_month_year', 'publication_date')
    readonly_fields = ('uid',)
    search_fields = ('name', 'session')

@admin.register(MBAExamCenterMapping)
class MBAExamCenterMappingAdmin(admin.ModelAdmin):
    list_display = ('exam', 'center')
    list_filter = ('exam', 'center')
    filter_horizontal = ('attached_colleges',)

@admin.register(MBAExamSchedule)
class MBAExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date', 'sitting')
    search_fields = ('common_course_structure__course_name', 'common_course_structure__code')

@admin.register(MBASemesterRegistration)
class MBASemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'exam_eligible')
    list_filter = ('sem', 'session', 'status', 'exam_eligible')

@admin.register(MBAExamRegistration)
class MBAExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_roll_no', 'sem', 'session', 'status', 'is_open')
    list_filter = ('sem', 'session', 'status', 'is_open')

    def get_roll_no(self, obj):
        return obj.student.roll_no if obj.student else None

    get_roll_no.short_description = 'Roll No'


@admin.register(MBAStudentAssessment)
class MBAStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_code', 'semester', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('semester', 'label', 'exam_type', 'batch')
    search_fields = ('student__roll_no', 'course_name', 'course_code')

@admin.register(MBAExamResult)
class MBAExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'session', 'semester_result', 'total_marks_obtained', 'percentage')
    list_filter = ('semester', 'session', 'semester_result')
    search_fields = ('student__roll_no',)
