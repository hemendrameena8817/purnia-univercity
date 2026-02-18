from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import CSV, XLSX, JSON
from .models import (
    BTechCourse, BTechBranch, BTechSession, BTechBatch, BTechStudentProfile, 
    BTechCourseStructure, BTechCommonCourseStructure,
    BTechExam, BTechExamSchedule, BTechYearRegistration, 
    BTechExamRegistration, BTechStudentAssessment, BTechExamResult,
    BTechExamCenterMapping
)
from .resources import (
    BTechBranchResource, BTechCourseResource, BTechSessionResource, 
    BTechBatchResource, BTechStudentProfileResource, 
    BTechCourseStructureResource, BTechCommonCourseStructureResource,
    BTechExamResource, BTechExamRegistrationResource, 
    BTechStudentAssessmentResource, BTechExamResultResource,
    BTechExamCenterMappingResource, BTechExamScheduleResource, 
    BTechYearRegistrationResource
)

@admin.register(BTechBranch)
class BTechBranchAdmin(ImportExportModelAdmin):
    resource_class = BTechBranchResource
    list_display = ('uid', 'name', 'code', 'course', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('course', 'is_active')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechCourse)
class BTechCourseAdmin(ImportExportModelAdmin):
    resource_class = BTechCourseResource
    list_display = ('uid', 'name', 'duration_years')
    readonly_fields = ('uid',)
    search_fields = ('name',)
    formats = [CSV, XLSX, JSON]

@admin.register(BTechSession)
class BTechSessionAdmin(ImportExportModelAdmin):
    resource_class = BTechSessionResource
    list_display = ('uid', 'name', 'start_year', 'end_year', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('is_active',)
    formats = [CSV, XLSX, JSON]

@admin.register(BTechBatch)
class BTechBatchAdmin(ImportExportModelAdmin):
    resource_class = BTechBatchResource
    list_display = ('uid', 'name', 'session', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('session', 'is_active')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechStudentProfile)
class BTechStudentProfileAdmin(ImportExportModelAdmin):
    resource_class = BTechStudentProfileResource
    list_display = ('uid', 'roll_no', 'registration_no', 'first_name', 'last_name', 'college', 'batch')
    readonly_fields = ('uid',)
    search_fields = ('roll_no', 'registration_no', 'first_name', 'last_name', 'user__username')
    list_filter = ('college', 'batch', 'status')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechCourseStructure)
class BTechCourseStructureAdmin(ImportExportModelAdmin):
    resource_class = BTechCourseStructureResource
    list_display = ('course_name', 'course_code', 'course_type', 'year')
    list_filter = ('year', 'course_type')
    search_fields = ('course_name', 'course_code')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechCommonCourseStructure)
class BTechCommonCourseStructureAdmin(ImportExportModelAdmin):
    resource_class = BTechCommonCourseStructureResource
    list_display = ('year', 'course_name', 'course_type', 'marks')
    list_filter = ('year', 'course_type')
    search_fields = ('course_name', 'code')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechExam)
class BTechExamAdmin(ImportExportModelAdmin):
    resource_class = BTechExamResource
    list_display = ('uid', 'name', 'year', 'session', 'batch', 'exam_month_year', 'publication_date')
    readonly_fields = ('uid',)
    search_fields = ('name', 'session', 'batch')
    list_filter = ('year', 'session', 'batch')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechExamCenterMapping)
class BTechExamCenterMappingAdmin(ImportExportModelAdmin):
    resource_class = BTechExamCenterMappingResource
    list_display = ('uid', 'get_exams', 'center')
    list_filter = ('exams', 'center')
    filter_horizontal = ('attached_colleges', 'exams')
    formats = [CSV, XLSX, JSON]

    def get_exams(self, obj):
        return ", ".join([str(exam) for exam in obj.exams.all()])
    get_exams.short_description = 'Exams'

@admin.register(BTechExamSchedule)
class BTechExamScheduleAdmin(ImportExportModelAdmin):
    resource_class = BTechExamScheduleResource
    list_display = ('exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date', 'sitting')
    search_fields = ('common_course_structure__course_name', 'common_course_structure__code')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechYearRegistration)
class BTechYearRegistrationAdmin(ImportExportModelAdmin):
    resource_class = BTechYearRegistrationResource
    list_display = ('student', 'year', 'session', 'status', 'exam_eligible')
    list_filter = ('year', 'session', 'status', 'exam_eligible')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechExamRegistration)
class BTechExamRegistrationAdmin(ImportExportModelAdmin):
    resource_class = BTechExamRegistrationResource
    list_display = ('student', 'exam', 'exam_type', 'year', 'session', 'status', 'is_open')
    list_filter = ('exam', 'exam_type', 'year', 'session', 'status', 'is_open')
    filter_horizontal = ('backlog_subjects',)
    search_fields = ('student__registration_no', 'student__first_name', 'student__last_name')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechStudentAssessment)
class BTechStudentAssessmentAdmin(ImportExportModelAdmin):
    resource_class = BTechStudentAssessmentResource
    list_display = ('student', 'course_code', 'year', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('year', 'label', 'exam_type', 'batch')
    search_fields = ('student__roll_no', 'course_name', 'course_code')
    formats = [CSV, XLSX, JSON]

@admin.register(BTechExamResult)
class BTechExamResultAdmin(ImportExportModelAdmin):
    resource_class = BTechExamResultResource
    list_display = ('student', 'year', 'session', 'year_result', 'total_marks_obtained', 'percentage')
    list_filter = ('year', 'session', 'year_result')
    search_fields = ('student__roll_no',)
    formats = [CSV, XLSX, JSON]
