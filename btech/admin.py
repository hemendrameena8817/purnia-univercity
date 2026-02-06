from django.contrib import admin
from .models import (
    BTechCourse, BTechBranch, BTechSession, BTechBatch, BTechStudentProfile, 
    BTechCourseStructure, BTechCommonCourseStructure,
    BTechExam, BTechExamSchedule, BTechYearRegistration, 
    BTechExamRegistration, BTechStudentAssessment, BTechExamResult,
    BTechExamCenterMapping
)

@admin.register(BTechBranch)
class BTechBranchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'code', 'course', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('course', 'is_active')

@admin.register(BTechCourse)
class BTechCourseAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'duration_years')
    readonly_fields = ('uid',)
    search_fields = ('name',)

@admin.register(BTechSession)
class BTechSessionAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'start_year', 'end_year', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('is_active',)

@admin.register(BTechBatch)
class BTechBatchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('session', 'is_active')

@admin.register(BTechStudentProfile)
class BTechStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('uid', 'roll_no', 'registration_no', 'first_name', 'last_name', 'college', 'batch')
    readonly_fields = ('uid',)
    search_fields = ('roll_no', 'registration_no', 'first_name', 'last_name', 'user__username')
    list_filter = ('college', 'batch', 'status')

@admin.register(BTechCourseStructure)
class BTechCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_code', 'course_type', 'year')
    list_filter = ('year', 'course_type')
    search_fields = ('course_name', 'course_code')

@admin.register(BTechCommonCourseStructure)
class BTechCommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('year', 'course_name', 'course_type', 'marks')
    list_filter = ('year', 'course_type')
    search_fields = ('course_name', 'code')

@admin.register(BTechExam)
class BTechExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'exam_month_year', 'publication_date')
    readonly_fields = ('uid',)
    search_fields = ('name', 'session')

@admin.register(BTechExamCenterMapping)
class BTechExamCenterMappingAdmin(admin.ModelAdmin):
    list_display = ('uid', 'get_exams', 'center')
    list_filter = ('exams', 'center')
    filter_horizontal = ('attached_colleges', 'exams')

    def get_exams(self, obj):
        return ", ".join([str(exam) for exam in obj.exams.all()])
    get_exams.short_description = 'Exams'

@admin.register(BTechExamSchedule)
class BTechExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date', 'sitting')
    search_fields = ('common_course_structure__course_name', 'common_course_structure__code')

@admin.register(BTechYearRegistration)
class BTechYearRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'year', 'session', 'status', 'exam_eligible')
    list_filter = ('year', 'session', 'status', 'exam_eligible')

@admin.register(BTechExamRegistration)
class BTechExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'exam_type', 'year', 'session', 'status', 'is_open')
    list_filter = ('exam', 'exam_type', 'year', 'session', 'status', 'is_open')
    filter_horizontal = ('backlog_subjects',)
    search_fields = ('student__registration_no', 'student__first_name', 'student__last_name')

@admin.register(BTechStudentAssessment)
class BTechStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_code', 'year', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('year', 'label', 'exam_type', 'batch')
    search_fields = ('student__roll_no', 'course_name', 'course_code')

@admin.register(BTechExamResult)
class BTechExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'year', 'session', 'year_result', 'total_marks_obtained', 'percentage')
    list_filter = ('year', 'session', 'year_result')
    search_fields = ('student__roll_no',)
