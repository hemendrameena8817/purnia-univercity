from django.contrib import admin
from .models import (
    BBACourse, BBASession, BBABatch, BBAStudentProfile,
    BBACourseStructure, BBACommonCourseStructure, BBAExam,
    BBAExamCenterMapping, BBAExamSchedule, BBAYearRegistration,
    BBAExamRegistration, BBAStudentAssessment, BBAExamResult,
    BBAStudentCourseAssessment
)

@admin.register(BBACourse)
class BBACourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'discipline_code', 'duration_years')
    search_fields = ('name', 'discipline_code')

@admin.register(BBASession)
class BBASessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_year', 'end_year', 'is_active')
    list_filter = ('is_active',)

@admin.register(BBABatch)
class BBABatchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'is_active')
    list_filter = ('is_active',)

@admin.register(BBAStudentProfile)
class BBAStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'roll_no', 'first_name', 'last_name', 'college', 'current_year', 'status')
    search_fields = ('registration_no', 'roll_no', 'first_name', 'last_name')
    list_filter = ('current_year', 'status', 'college', 'batch')
    raw_id_fields = ('user',)

@admin.register(BBACourseStructure)
class BBACourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_code', 'course', 'year', 'label', 'max_marks')
    list_filter = ('course', 'year', 'label')
    search_fields = ('course_name', 'course_code')

@admin.register(BBACommonCourseStructure)
class BBACommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'code', 'course', 'year', 'course_type', 'paper_type', 'marks')
    list_filter = ('course', 'year', 'course_type', 'paper_type')
    search_fields = ('course_name', 'code')

@admin.register(BBAExam)
class BBAExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'year', 'session', 'publication_date')
    list_filter = ('year', 'session')

@admin.register(BBAExamCenterMapping)
class BBAExamCenterMappingAdmin(admin.ModelAdmin):
    list_display = ('exam', 'center')
    filter_horizontal = ('attached_colleges',)

@admin.register(BBAExamSchedule)
class BBAExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date')

@admin.register(BBAYearRegistration)
class BBAYearRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'year', 'session', 'status', 'exam_eligible')
    list_filter = ('year', 'session', 'status', 'exam_eligible')
    raw_id_fields = ('student',)

@admin.register(BBAExamRegistration)
class BBAExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'year', 'exam_type', 'status')
    list_filter = ('exam', 'year', 'exam_type', 'status')
    raw_id_fields = ('student',)
    filter_horizontal = ('exam_subjects',)

@admin.register(BBAStudentAssessment)
class BBAStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_name', 'year', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('year', 'label', 'exam_type', 'ind_is_pass')
    raw_id_fields = ('student', 'batch')
    search_fields = ('student__registration_no', 'course_name', 'course_code')

@admin.register(BBAExamResult)
class BBAExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'year', 'session', 'year_result', 'total_marks_obtained', 'percentage')
    list_filter = ('year', 'session', 'year_result')
    raw_id_fields = ('student',)
    search_fields = ('student__registration_no', 'student__roll_no')

@admin.register(BBAStudentCourseAssessment)
class BBAStudentCourseAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_name', 'year', 'label', 'session', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('year', 'label', 'session', 'exam_type', 'batch')
    raw_id_fields = ('student', 'batch', 'bba_exam')
    search_fields = ('student__registration_no', 'course_name', 'paper_code')
