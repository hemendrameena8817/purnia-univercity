from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import (
    MBACourse, MBASession, MBABatch, MBAStudentProfile, MBACourseStructure,
    MBACommonCourseStructure, MBAExam, MBAExamCenterMapping, MBAExamSchedule,
    MBASemesterRegistration, MBAExamRegistration, MBAStudentAssessment,
    MBAExamResult, MBAStudentCourseAssessment
)
from .resources import (
    MBACourseResource, MBASessionResource, MBABatchResource, MBAStudentProfileResource,
    MBACourseStructureResource, MBACommonCourseStructureResource, MBAExamResource,
    MBAExamCenterMappingResource, MBAExamScheduleResource, MBASemesterRegistrationResource,
    MBAExamRegistrationResource, MBAStudentAssessmentResource, MBAExamResultResource,
    MBAStudentCourseAssessmentResource
)


@admin.register(MBACourse)
class MBACourseAdmin(ImportExportModelAdmin):
    resource_class = MBACourseResource
    list_display = ('uid', 'name', 'discipline_code', 'duration_years')
    readonly_fields = ('uid',)
    search_fields = ('name',)

@admin.register(MBASession)
class MBASessionAdmin(ImportExportModelAdmin):
    resource_class = MBASessionResource
    list_display = ('uid', 'name', 'start_year', 'end_year', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('is_active',)

@admin.register(MBABatch)
class MBABatchAdmin(ImportExportModelAdmin):
    resource_class = MBABatchResource
    list_display = ('uid', 'name', 'session', 'is_active')
    readonly_fields = ('uid',)
    list_filter = ('session', 'is_active')

@admin.register(MBAStudentProfile)
class MBAStudentProfileAdmin(ImportExportModelAdmin):
    resource_class = MBAStudentProfileResource
    list_display = ('uid', 'roll_no', 'registration_no', 'first_name', 'last_name', 'college', 'batch')
    readonly_fields = ('uid',)
    search_fields = ('roll_no', 'registration_no', 'first_name', 'last_name', 'user__username')
    list_filter = ('college', 'batch', 'status')
    raw_id_fields = ("user", "college", "course", "batch")


@admin.register(MBACourseStructure)
class MBACourseStructureAdmin(ImportExportModelAdmin):
    resource_class = MBACourseStructureResource
    list_display = ('course_name', 'course_code', 'course_type', 'semester')
    list_filter = ('semester', 'course_type')
    search_fields = ('course_name', 'course_code')

@admin.register(MBACommonCourseStructure)
class MBACommonCourseStructureAdmin(ImportExportModelAdmin):
    resource_class = MBACommonCourseStructureResource
    list_display = ('uid','semester', 'course_name', 'course_type', 'marks', 'code')
    list_filter = ('semester', 'course_type')
    search_fields = ('course_name', 'code')

@admin.register(MBAExam)
class MBAExamAdmin(ImportExportModelAdmin):
    resource_class = MBAExamResource
    list_display = ('uid', 'name', 'session', 'exam_month_year', 'publication_date')
    readonly_fields = ('uid',)
    search_fields = ('name', 'session')

@admin.register(MBAExamCenterMapping)
class MBAExamCenterMappingAdmin(ImportExportModelAdmin):
    resource_class = MBAExamCenterMappingResource
    list_display = ('exam', 'center')
    list_filter = ('exam', 'center')
    filter_horizontal = ('attached_colleges',)
    raw_id_fields = ("exam", "center")

@admin.register(MBAExamSchedule)
class MBAExamScheduleAdmin(ImportExportModelAdmin):
    resource_class = MBAExamScheduleResource
    list_display = ('exam', 'common_course_structure', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date', 'sitting')
    search_fields = ('common_course_structure__course_name', 'common_course_structure__code')

@admin.register(MBASemesterRegistration)
class MBASemesterRegistrationAdmin(ImportExportModelAdmin):
    resource_class = MBASemesterRegistrationResource
    list_display = ('student', 'sem', 'session', 'status', 'exam_eligible')
    list_filter = ('sem', 'session', 'status', 'exam_eligible')

@admin.register(MBAExamRegistration)
class MBAExamRegistrationAdmin(ImportExportModelAdmin):
    resource_class = MBAExamRegistrationResource
    list_display = ('student', 'get_roll_no', 'sem', 'session', 'status', 'is_open')
    list_filter = ('sem', 'session', 'status', 'is_open')
    raw_id_fields = ("student","exam")

    @admin.display(description='Roll No')
    def get_roll_no(self, obj):
        return obj.student.roll_no if obj.student else None


@admin.register(MBAStudentAssessment)
class MBAStudentAssessmentAdmin(ImportExportModelAdmin):
    resource_class = MBAStudentAssessmentResource
    list_display = ('student', 'course_code', 'semester', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('semester', 'label', 'exam_type', 'batch')
    search_fields = ('student__roll_no', 'course_name', 'course_code')

@admin.register(MBAExamResult)
class MBAExamResultAdmin(ImportExportModelAdmin):
    resource_class = MBAExamResultResource
    list_display = ('student', 'semester', 'session', 'semester_result', 'total_marks_obtained', 'percentage')
    list_filter = ('semester', 'session', 'semester_result')
    search_fields = ('student__roll_no',)

@admin.register(MBAStudentCourseAssessment)
class StudentCourseAssessmentAdmin(ImportExportModelAdmin):
    resource_class = MBAStudentCourseAssessmentResource
    list_display = (
        "uid",
        "get_roll_no",
        "student",
        "semester",
        "paper_code",
        "label",
        "exam_type",
        "ind_marks_obtained",
        "ind_is_absent",
        "ind_is_pass",
        "sgpa",
        "created_at",
    )

    list_editable = (
        "ind_marks_obtained",
        "ind_is_absent",
        "ind_is_pass",
        "sgpa",
    )

    list_filter = (
        "semester",
        "label",
        "exam_type",
        "batch",
        "session",
        "paper_code"
    )

    search_fields = (
        "student__roll_no",
        "paper_code",
        "course_name",
    )

    def get_roll_no(self, obj): return obj.student.roll_no if obj.student else ""

    raw_id_fields = ("student", "batch", "mba_exam")

    ordering = ("-created_at",)
