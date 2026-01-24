from django.contrib import admin
from .models import (
    StagingInstituteMaster, StagingApplicantMaster, ApplicantRegMaster,
    SubjectMaster, PaperSubjectMapping, DisciplineMaster, CourseDisciplineSemPaperMapping,
    RegisteredApplicantMaster, StagingApplicantQualificationDetail
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
