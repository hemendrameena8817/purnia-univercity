from django.contrib import admin
from .models import (
    StagingInstituteMaster, StagingApplicantMaster, ApplicantRegMaster,
    SubjectMaster, PaperSubjectMapping, DisciplineMaster, CourseDisciplineSemPaperMapping,
    RegisteredApplicantMaster, StagingApplicantQualificationDetail, UGSemResultCurrent,
    UGResultCurrent, PGResultCurrent, DisciplineMasterDump, StagingLLBResultCurrent, \
    CenterInstituteMapPurnea,ExamMasterDump
)



@admin.register(StagingInstituteMaster)
class StagingInstituteMasterAdmin(admin.ModelAdmin):
    list_display = ('institute_code', 'institute_name', 'institute_type', 'is_migrated', 'imported_at')
    list_filter = ('is_migrated', 'record_status')
    search_fields = ('institute_code', 'institute_name', 'institute_address')
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)


@admin.register(StagingApplicantMaster)
class StagingApplicantMasterAdmin(admin.ModelAdmin):
    list_display = (
        'csv_id', 'reg_user_id', 'full_name', 'applicant_mobile', 'applicant_email',
        'applied_program', 'discipline_code', 'institute_code', 
        'category', 'gender', 'application_status', 'is_migrated'
    )
    list_filter = (
        'is_migrated', 'applied_program', 'discipline_code', 'institute_code',
        'category', 'gender', 'application_status', 'record_status'
    )
    search_fields = (
        'full_name', 'first_name', 'last_name', 'applicant_mobile', 
        'applicant_email', 'univ_regn_no', 'aadhar_no', 'csv_id', 'reg_user_id'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
    list_per_page = 50
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                ('first_name', 'mid_name', 'last_name'),
                'full_name',
                ('gender', 'dob', 'dob_in_word'),
                ('nationality', 'religion', 'caste'),
                ('category', 'blood_group', 'marital_status'),
                ('differently_abled', 'is_physically_challanged'),
            )
        }),
        ('Contact Information', {
            'fields': (
                'applicant_email',
                ('applicant_mobile', 'applicant_landline'),
                ('comm_address_ref_id', 'perm_address_ref_id'),
            )
        }),
        ('Academic Information', {
            'fields': (
                ('applied_program', 'applied_class', 'discipline_code'),
                ('center', 'exam_center_code'),
                ('instruction_mode', 'medium', 'second_language'),
                ('highest_qualification', 'last_grade', 'last_board', 'secured_mark'),
                'univ_regn_no',
            )
        }),
        ('Application Details', {
            'fields': (
                ('institute_code', 'applied', 'applied_details'),
                ('application_status', 'present_status'),
                'employer_address',
            )
        }),
        ('Guardian & Other Info', {
            'fields': (
                'guardian_name',
                'aadhar_no',
            )
        }),
        ('System Information', {
            'fields': (
                ('csv_id', 'reg_user_id'),
                ('created_by', 'created_on'),
                ('updated_by', 'updated_on'),
                ('record_status', 'last_updated'),
            ),
            'classes': ('collapse',)
        }),
        ('Migration Status', {
            'fields': (
                ('uid', 'imported_at'),
                'is_migrated',
                'migration_notes',
            )
        }),
    )


@admin.register(ApplicantRegMaster)
class ApplicantRegMasterAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'mobile', 'applied_program', 'institute_code', 'is_migrated', 'imported_at')
    list_filter = ('is_migrated', 'applied_program', 'reg_status')
    search_fields = ('first_name', 'last_name', 'mobile', 'email_id')
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)


@admin.register(SubjectMaster)
class SubjectMasterAdmin(admin.ModelAdmin):
    list_display = ('subject_code', 'subject_name', 'syllabus_code', 'institute_code', 'is_migrated', 'imported_at')
    list_filter = ('is_migrated', 'syllabus_code', 'institute_code')
    search_fields = ('subject_code', 'subject_name')
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)


@admin.register(PaperSubjectMapping)
class PaperSubjectMappingAdmin(admin.ModelAdmin):
    list_display = ('paper_code', 'subject_code', 'discipline_code', 'institute_code', 'is_migrated', 'imported_at')
    list_filter = ('is_migrated', 'discipline_code')
    search_fields = ('paper_code', 'subject_code')
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)


@admin.register(DisciplineMaster)
class DisciplineMasterAdmin(admin.ModelAdmin):
    list_display = ('discipline_code', 'discipline_name', 'institute_code', 'is_migrated', 'imported_at')
    list_filter = ('is_migrated', 'institute_code')
    search_fields = ('discipline_code', 'discipline_name')
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)


@admin.register(CourseDisciplineSemPaperMapping)
class CourseDisciplineSemPaperMappingAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'paper_code', 'discipline_code', 'semester_code', 'paper_type', 'is_migrated', 'imported_at')
    list_filter = ('is_migrated', 'discipline_code', 'semester_code', 'paper_type')
    search_fields = ('course_code', 'paper_code', 'discipline_code')
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)


@admin.register(RegisteredApplicantMaster)
class RegisteredApplicantMasterAdmin(admin.ModelAdmin):
    list_display = (
        'csv_id', 'reg_no', 'college_roll_no', 'student_name', 'fathers_name',
        'course_code', 'discipline_code', 'semester_code', 'batch_code',
        'institute_code', 'session_code', 'result', 'is_migrated'
    )
    list_filter = (
        'is_migrated', 'course_code', 'discipline_code', 'semester_code', 
        'batch_code', 'session_code', 'institute_code', 'result', 
        'exam_type_code', 'gender', 'category', 'payment_status'
    )
    search_fields = (
        'reg_no', 'student_name', 'fathers_name', 'mothers_name',
        'college_roll_no', 'college_reg_no', 'phone', 'aadhar_card_no',
        'roll_no', 'appl_no', 'csv_id'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
    list_per_page = 50
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                'student_name',
                ('fathers_name', 'mothers_name'),
                ('dob', 'gender', 'category'),
                ('phone', 'aadhar_card_no'),
                'full_address',
            )
        }),
        ('Registration Details', {
            'fields': (
                ('reg_no', 'roll_no'),
                ('college_roll_no', 'college_reg_no'),
                ('sams_id', 'appl_no'),
                ('abc_id', 'addmision_date'),
            )
        }),
        ('Academic Information', {
            'fields': (
                ('course_code', 'discipline_code'),
                ('semester_code', 'batch_code'),
                ('syllabus_year', 'session_code'),
                ('institute_code', 'is_sem'),
                'last_board',
            )
        }),
        ('Examination Details', {
            'fields': (
                ('exam_type_code', 'result'),
                ('center', 'center2017', 'center2017_old'),
            )
        }),
        ('Status Information', {
            'fields': (
                ('approve', 'payment_status', 'api_status'),
                ('institute_pub_status', 'student_pub_status'),
            )
        }),
        ('System Information', {
            'fields': (
                'csv_id',
                ('created_by', 'created_on'),
                ('updated_by', 'updated_on'),
                ('record_status', 'last_updated'),
            ),
            'classes': ('collapse',)
        }),
        ('Migration Status', {
            'fields': (
                ('uid', 'imported_at'),
                'is_migrated',
                'migration_notes',
            )
        }),
    )


@admin.register(StagingApplicantQualificationDetail)
class StagingApplicantQualificationDetailAdmin(admin.ModelAdmin):
    list_display = ('applied_class', 'applied_program', 'created_by', 'created_on', 'division_distinction', 'is_migrated', 'imported_at')
    list_filter = ('is_migrated',)
    search_fields = ('applied_class', 'applied_program', 'created_by')
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)


from import_export import resources
from import_export.admin import ImportExportModelAdmin

class UGSemResultCurrentResource(resources.ModelResource):
    class Meta:
        model = UGSemResultCurrent
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True
        exclude = ('uid',)

@admin.register(UGSemResultCurrent)
class UGSemResultCurrentAdmin(ImportExportModelAdmin):
    resource_class = UGSemResultCurrentResource
    show_full_result_count = False
    list_display = (
        'source_id', 'college_roll_no', 'student_name', 'semester_code', 
        'course_code', 'discipline_code', 'paper_code', 'subject_code',
        'subject_result', 'final_result', 'exam_type',
        'institute_code', 'is_migrated'
    )
    list_filter = (
        'is_migrated', 'semester_code', 'course_code', 'discipline_code',
        'batch_code', 'session_code', 'institute_code', 'subject_result', 
        'final_result', 'exam_type'
    )
    search_fields = (
        'college_roll_no', 'college_reg_no', 'student_name', 'fathers_name',
        'mothers_name', 'user_id', 'source_id', 'paper_code', 'subject_code', 'exam_type'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
    list_per_page = 50
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                ('student_name', 'student_name_hindi'),
                ('fathers_name', 'mothers_name'),
                ('college_roll_no', 'college_reg_no'),
                ('user_id', 'source_id'),
            )
        }),
        ('Course Information', {
            'fields': (
                ('course_code', 'discipline_code'),
                ('semester_code', 'session_code', 'batch_code'),
                ('paper_code', 'subject_code'),
                'subject_name',
                ('faculty', 'institute_code'),
            )
        }),
        ('Exam Details', {
            'fields': (
                ('exam_type', 'exam_type_his'),
                ('status', 'final_sheet_status', 'record_status'),
            )
        }),
        ('Marks & Result', {
            'fields': (
                ('maximum_mark', 'pass_mark', 'mark_secured'),
                'subject_total_mark',
                ('subject_ca', 'total_ca'),
                ('subject_ce', 'total_ce'),
                ('subject_gp', 'subject_ng'),
                ('subject_result', 'final_result'),
                ('grand_total_mark', 'total_secured_mark'),
                ('total_per', 'final_merit'),
                ('gpa', 'cgpa', 'dsc_grad'),
                ('let_grad', 'let_grad_sub', 'numrical_let_grad'),
                ('sem_1_total_ce', 'sem_2_total_ce', 'sem_3_total_ce'),
                ('sem_1_final_result', 'is_grace', 'gpa_grace'),
            )
        }),
        ('Migration Status', {
            'fields': (
                ('uid', 'imported_at'),
                'is_migrated',
                'migration_notes',
            )
        }),
    )

@admin.register(UGResultCurrent)
class UGResultCurrentAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_display = (
        'source_id', 'user_id', 'uid', 'college_roll_no', 'college_reg_no', 
        'student_name', 'fathers_name', 'mothers_name', 
        'semester_code', 'batch_code', 'session_code', 'course_code', 'discipline_code', 
        'paper_code', 'subject_code', 'subject_name', 
        'theory', 'sessional', 'status', 'pra', 
        'exam_type', 'exam_type_his', 
        'maximum_mark', 'pass_mark', 'mark_secured', 'mark_secured_history', 
        'subject_total_mark', 'subject_result', 'subject_result_1', 'subject_result_2', 
        'final_result', 
        'grand_total_mark', 'total_secured_mark_1', 'total_secured_mark_2', 'total_secured_mark', 
        'hon', 'total_per', 'agreegate', 
        'institute_code', 
        'record_status_check', 'record_status', 
        'grade', 'student_check', 'grace_chk', 'remark', 
        'paper_type_code', 'sub_reult_com', 'ExRegular_chk', 'subject_count', 
        'aggregate_hindi', 
        'temp_paper_code', 'paper_code_correction', 'subject_code_correction', 
        'is_migrated', 'migration_notes', 'imported_at'
    )
    list_filter = (
        'is_migrated', 'semester_code', 'course_code', 'discipline_code',
        'batch_code', 'session_code', 'institute_code', 
        'subject_result', 'final_result', 'exam_type', 'status', 'grade'
    )
    search_fields = (
        'college_roll_no', 'college_reg_no', 'student_name', 
        'fathers_name', 'mothers_name', 'user_id', 'source_id', 
        'paper_code', 'subject_code', 'exam_type', 'uid'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
    list_per_page = 50
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                ('student_name', 'fathers_name', 'mothers_name'),
                ('college_roll_no', 'college_reg_no'),
                ('user_id', 'source_id', 'uid'),
            )
        }),
        ('Course Information', {
            'fields': (
                ('course_code', 'discipline_code'),
                ('semester_code', 'session_code', 'batch_code'),
                ('paper_code', 'subject_code'),
                'subject_name',
                'institute_code',
            )
        }),
        ('Exam Details', {
            'fields': (
                ('exam_type', 'exam_type_his'),
                ('status', 'record_status', 'record_status_check'),
                'paper_type_code',
            )
        }),
        ('Marks & Result', {
            'fields': (
                ('theory', 'sessional', 'pra'),
                ('maximum_mark', 'pass_mark', 'mark_secured', 'mark_secured_history'),
                'subject_total_mark',
                ('subject_result', 'subject_result_1', 'subject_result_2'),
                'final_result',
                ('grand_total_mark', 'total_secured_mark', 'total_secured_mark_1', 'total_secured_mark_2'),
                ('total_per', 'hon', 'agreegate', 'grade'),
                ('student_check', 'grace_chk', 'remark'),
                ('sub_reult_com', 'ExRegular_chk', 'subject_count'),
                'aggregate_hindi',
            )
        }),
        ('Correction Fields', {
            'fields': (
                ('temp_paper_code', 'paper_code_correction', 'subject_code_correction'),
            ),
            'classes': ('collapse',)
        }),
        ('Migration Status', {
            'fields': (
                ('imported_at'),
                'is_migrated',
                'migration_notes',
            )
        }),
    )


@admin.register(PGResultCurrent)
class PGResultCurrentAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_display = (
        'source_id', 'college_roll_no', 'student_name', 'semester_code', 
        'course_code', 'discipline_code', 'paper_code', 'subject_code',
        'subject_result', 'final_result', 'exam_type',
        'institute_code', 'is_migrated'
    )
    list_filter = (
        'paper_code','is_migrated', 'semester_code', 'course_code', 'discipline_code',
        'batch_code', 'session_code', 'institute_code', 'subject_result', 
        'final_result', 'exam_type'
    )
    search_fields = (
        'college_roll_no', 'college_reg_no', 'student_name', 'fathers_name',
        'mothers_name', 'user_id', 'source_id', 'paper_code', 'subject_code', 'exam_type'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
    list_per_page = 50
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                ('student_name', 'student_name_hindi'),
                ('fathers_name', 'mothers_name'),
                ('college_roll_no', 'college_reg_no'),
                ('user_id', 'source_id'),
            )
        }),
        ('Course Information', {
            'fields': (
                ('course_code', 'discipline_code'),
                ('semester_code', 'session_code', 'batch_code'),
                ('paper_code', 'subject_code'),
                'subject_name',
                ('faculty', 'institute_code'),
            )
        }),
        ('Exam Details', {
            'fields': (
                ('exam_type', 'exam_type_his'),
                ('status', 'final_sheet_status', 'record_status'),
            )
        }),
        ('Marks & Result', {
            'fields': (
                ('maximum_mark', 'pass_mark', 'mark_secured'),
                'subject_total_mark',
                ('subject_ca', 'total_ca'),
                ('subject_ce', 'total_ce'),
                ('subject_gp', 'subject_ng'),
                ('subject_result', 'final_result'),
                ('grand_total_mark', 'total_secured_mark'),
                ('total_per', 'max_total_mark'),
                ('gpa', 'cgpa', 'dsc_grad'),
                ('let_grad', 'let_grad_sub', 'numrical_let_grad'),
                ('agreegate', 'grade'),
            )
        }),
        ('Migration Status', {
            'fields': (
                ('uid', 'imported_at'),
                'is_migrated',
                'migration_notes',
            )
        }),
    )


@admin.register(DisciplineMasterDump)
class DisciplineMasterDumpAdmin(admin.ModelAdmin):
    list_display = (
        'source_id', 'discipline_code', 'discipline', 'discipline_name', 
        'discipline_name_new', 'institute_code', 'is_migrated'
    )
    list_filter = ('is_migrated', 'institute_code', 'record_status')
    search_fields = (
        'discipline_code', 'discipline', 'discipline_name', 
        'discipline_name_new', 'discipline_name_hindi', 'source_id'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
    list_per_page = 50


@admin.register(CenterInstituteMapPurnea)
class CenterInstituteMapPurneaAdmin(admin.ModelAdmin):
    list_display = (
        'source_id', 'center_code', 'center_name', 'batch_code', 'course_code',
        'semester_code', 'institute_code', 'institute_name', 'record_status',
        'exam_type', 'session_code', 'is_sem', 'is_migrated'
    )
    list_filter = (
        'is_migrated', 'course_code', 'batch_code', 'session_code', 'exam_type', 'is_sem'
    )
    search_fields = (
        'center_code', 'center_name', 'batch_code', 'course_code', 'semester_code',
        'institute_code', 'institute_name', 'record_status', 'exam_type', 'session_code', 'source_id'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
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
        ('Migration Status', {
            'fields': (
                ('uid', 'imported_at'),
                'is_migrated',
                'migration_notes',
            )
        }),
    )


@admin.register(ExamMasterDump)
class ExamMasterDumpAdmin(admin.ModelAdmin):
    list_display = (
        'source_id', 'exam_type', 'exam_code', 'exam_name', 'batch_code', 'session_code', 
        'course_code', 'discipline_code', 'semester_code', 'publish_all', 'actual_exam_month', 
        'year', 'sl_no', 'exam_month', 'exam_year', 'exam_start_date', 'exam_end_date', 
        'apply_start_date', 'apply_end_date', 'exam_mark_entry_date', 'online_payment_transaction_no', 
        'omr_no', 'template_code', 'publish_status', 'institute_code', 'created_by', 'created_on', 
        'updated_by', 'updated_on', 'record_status', 'last_updated', 'imported_at', 'is_migrated'
    )
    list_filter = (
        'is_migrated', 'course_code', 'batch_code', 'session_code', 'exam_type', 'is_sem'
    )
    search_fields = (
        'source_id', 'exam_type', 'exam_code', 'exam_name', 'batch_code', 'session_code', 
        'course_code', 'discipline_code', 'semester_code', 'publish_all', 'actual_exam_month', 
        'year', 'sl_no', 'exam_month', 'exam_year', 'exam_start_date', 'exam_end_date', 
        'apply_start_date', 'apply_end_date', 'exam_mark_entry_date', 'online_payment_transaction_no', 
        'omr_no', 'template_code', 'publish_status', 'institute_code', 'created_by', 'created_on', 
        'updated_by', 'updated_on', 'record_status', 'last_updated', 'imported_at'
    )
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
    list_per_page = 50
    
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
                ('publish_status', 'institute_code'),
                ('created_by', 'created_on'),
                ('updated_by', 'updated_on'),
                ('record_status', 'last_updated'),
                ('source_id',),
            )
        }),
        ('Migration Status', {
            'fields': (
                ('uid', 'imported_at'),
                'is_migrated',
                'migration_notes',
            )
        }),
    )