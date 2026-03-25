from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import PGOldResult, PGCenterInstituteMap, PGOldStudentProfile, PGExamMasterDump
from .resources import PGOldStudentProfileResource


@admin.register(PGOldStudentProfile)
class PGOldStudentProfileAdmin(ImportExportModelAdmin):
    resource_class = PGOldStudentProfileResource
    
    list_display = (
        'user',
        'registration_no',
        'roll_no',
        'first_name',
        'fathers_name',
        'mothers_name',
        'college',
        'course_code',
        'discipline_code',
        'batch_code',
        'final_result',
        'gpa',
        'cgpa',
        'total_percentage',
        'pg_faculty',
        'pg_department',
        'pg_degree',
        'pg_program',
        'source_user_id',
        'is_active',
        'created_at',
        'updated_at',
    )
    
    list_filter = (
        'college',
        'course_code',
        'discipline_code',
        'batch_code',
        'final_result',
        'is_active',
    )
    
    search_fields = (
        'registration_no',
        'roll_no',
        'first_name',
        'fathers_name',
        'mothers_name',
        'college__name',
        'college__college_code',
    )
    
    readonly_fields = (
        'uid',
        'created_at',
        'updated_at',
    )
    
    raw_id_fields = ('user',)
    
    ordering = ('-created_at', 'registration_no')
    
    list_per_page = 50
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                'uid',
                'user',
                'registration_no',
                'roll_no',
                'first_name',
                'hindi_name',
                'fathers_name',
                'mothers_name',
                'gender',
                'dob',
            )
        }),
        ('Academic Details', {
            'fields': (
                'college',
                'course_code',
                'discipline_code',
                'batch_code',
                'current_semester',
                'pg_faculty',
                'pg_department',
                'pg_degree',
                'pg_program',
            )
        }),
        ('Result Information', {
            'fields': (
                'final_result',
                'gpa',
                'cgpa',
                'total_percentage',
            )
        }),
        ('Source Information', {
            'fields': (
                'source_user_id',
                'is_active',
            )
        }),
        ('Meta', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        })
    )


@admin.register(PGOldResult)
class PGOldResultAdmin(ImportExportModelAdmin):
    list_display = (
        'student_profile',
        'batch_code',
        'semester_code',
        'session_code',
        'subject_name',
        'mark_secured',
        'subject_result',
        'gpa',
        'imported_at',
        'total_ce'

    )
    
    list_filter = (
        'batch_code',
        'semester_code',
        'session_code',
        'course_code',
        'discipline_code',
        'status',
        'subject_result',
        'final_result',
        'institute_code',)
    
    search_fields = (
        'subject_name',
        'paper_code'
    )
    
    readonly_fields = (
        'uid',
        'copied_from_staging',
        'imported_at'
    )
    
    raw_id_fields = ('student_profile',)
    
    ordering = ('-imported_at', 'batch_code', 'semester_code')
    
    list_per_page = 50
    
    show_full_result_count = False
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                'uid',
                'student_profile',
            )
        }),
        ('Academic Details', {
            'fields': (
                'batch_code',
                'semester_code',
                'session_code',
                'course_code',
                'discipline_code',
                'institute_code',
            )
        }),
        ('Subject Information', {
            'fields': (
                'paper_code',
                'subject_code',
                'subject_name',
                'exam_type',
                'exam_type_his',
                'status'
            )
        }),
        ('Marks Details', {
            'fields': (
                'maximum_mark',
                'pass_mark',
                'mark_secured',
                'subject_total_mark',
                'grand_total_mark',
                'total_secured_mark',
                'max_total_mark',
                'total_per'
            )
        }),
        ('Grades & Credits', {
            'fields': (
                'subject_ca',
                'subject_ng',
                'subject_ce',
                'subject_gp',
                'total_ca',
                'total_ce',
                'gpa',
                'cgpa',
                'numrical_let_grad',
                'let_grad_sub',
                'let_grad',
                'dsc_grad',
                'grade',
                'agreegate'
            )
        }),
        ('Result Status', {
            'fields': (
                'subject_result',
                'final_result',
                'record_status',
                'final_sheet_status'
            )
        }),
        ('Meta', {
            'fields': (
                'copied_from_staging',
                'imported_at'
            ),
            'classes': ('collapse',)
        })
    )


@admin.register(PGCenterInstituteMap)
class PGCenterInstituteMapAdmin(ImportExportModelAdmin):
    list_display = (
        'source_id', 'center_code', 'center_name', 'batch_code', 'course_code',
        'semester_code', 'institute_code', 'institute_name', 'record_status',
        'exam_type', 'session_code', 'is_sem', 'imported_at'
    )
    list_filter = (
        'course_code', 'batch_code', 'session_code', 'exam_type', 'is_sem','semester_code'
    )
    search_fields = (
        'center_code', 'center_name', 'batch_code', 'course_code', 'semester_code',
        'institute_code', 'institute_name', 'record_status', 'exam_type', 'session_code', 'source_id'
    )
    readonly_fields = ('uid', 'imported_at')
    list_per_page = 50
    
    fieldsets = (
        ('Center Information', {
            'fields': (
                ('center_code', 'center_name'),
                ('batch_code', 'course_code'),
                ('semester_code', 'institute_code'),
                ('institute_name', 'record_status'),
                ('exam_type', 'session_code'),
                ('is_sem', 'source_id'),
            )
        }),
        ('Meta', {
            'fields': (
                ('uid', 'imported_at'),
                'copied_from_staging',
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(PGExamMasterDump)
class PGExamMasterDumpAdmin(ImportExportModelAdmin):
    list_display = (
        'source_id', 'exam_type', 'exam_code', 'exam_name', 'batch_code',
        'session_code', 'course_code', 'discipline_code', 'semester_code',
        'exam_start_date', 'exam_end_date', 'publish_date', 'institute_code',
        'imported_at',
    )
    list_filter = (
        'course_code', 'batch_code', 'session_code', 'semester_code',
        'exam_type', 'discipline_code', 'publish_date', 'is_sem',
    )
    search_fields = (
        'source_id', 'exam_code', 'exam_name', 'batch_code',
        'session_code', 'discipline_code', 'institute_code',
    )
    readonly_fields = ('uid', 'imported_at', 'copied_from_staging')
    list_per_page = 50
    show_full_result_count = False

    fieldsets = (
        ('Exam Information', {
            'fields': (
                ('exam_type', 'exam_code'),
                ('exam_name', 'batch_code'),
                ('session_code', 'course_code'),
                ('discipline_code', 'semester_code'),
                ('publish_all', 'actual_exam_month'),
                ('year', 'sl_no'),
                ('exam_month', 'exam_year'),
                ('exam_start_date', 'exam_end_date'),
                ('apply_start_date', 'apply_end_date'),
                ('exam_mark_entry_date', 'online_payment_transaction_no'),
                ('omr_no', 'template_code'),
                ('publish_date', 'institute_code'),
                ('created_by', 'created_on'),
                ('updated_by', 'updated_on'),
                ('record_status', 'last_updated'),
                ('is_sem', 'source_id'),
            )
        }),
        ('Meta', {
            'fields': (
                ('uid', 'imported_at'),
                'copied_from_staging',
            ),
            'classes': ('collapse',)
        }),
    )
