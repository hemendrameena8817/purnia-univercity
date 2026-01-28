from django.contrib import admin
from .models import (
    PGFaculty, PGDepartment, PGDegree, PGProgram, PGBatch, PGStudentProfile,
    PGCourseStructure, PGStudentCourseAssessment, PGSemesterRegistration, PGExamRegistration
)


@admin.register(PGFaculty)
class PGFacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'university', 'created_at')
    list_filter = ('university',)
    search_fields = ('name', 'short_name')
    ordering = ('name',)


@admin.register(PGDepartment)
class PGDepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'faculty', 'head_of_department', 'created_at')
    list_filter = ('faculty',)
    search_fields = ('name', 'code', 'faculty__name')
    ordering = ('faculty', 'name')


@admin.register(PGDegree)
class PGDegreeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'total_semesters', 'total_years', 'created_at')
    search_fields = ('name', 'short_name')
    ordering = ('name',)


@admin.register(PGProgram)
class PGProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'degree', 'department', 'created_at')
    list_filter = ('degree', 'department__faculty')
    search_fields = ('name', 'short_name', 'degree__name', 'department__name')
    ordering = ('name',)


@admin.register(PGBatch)
class PGBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'program', 'created_at')
    list_filter = ('program',)
    search_fields = ('name', 'program__name')
    ordering = ('name',)


@admin.register(PGStudentProfile)
class PGStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'first_name', 'last_name', 'roll_no', 'college', 
                   'department', 'program', 'current_semester', 'status', 'is_active', 'batch')
    list_filter = ('status', 'gender', 'college', 'department', 'program', 'degree', 
                  'current_semester', 'batch')
    search_fields = ('registration_no', 'roll_no', 'first_name', 'last_name', 
                    'mobile_no', 'aadhar_no')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('uid', 'user', 'first_name', 'last_name', 'hindi_name',
                      'date_of_birth', 'gender', 'caste', 'mobile_no', 'aadhar_no', 'address')
        }),
        ('Academic Information', {
            'fields': ('registration_no', 'roll_no', 'college', 'department', 
                      'program', 'degree', 'current_semester', 'session', 'batch', 'status', 'is_active')
        }),
        ('Admission Details', {
            'fields': ('admission_date', 'enrollment_date', 'migration_submitted', 'last_university')
        }),
        ('Course Selections (PG)', {
            'fields': ('cc_course', 'sec_course', 'ec_course')
        }),
        ('Family Information', {
            'fields': ('father_name', 'mother_name')
        }),
        ('Documents', {
            'fields': ('profile_image', 'signature'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(PGCourseStructure)
class PGCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'department', 'course_type', 'code', 'semester', 'max_marks', 'max_credit', 'label')
    list_filter = ('department__faculty', 'department', 'course_type', 'semester')
    search_fields = ('course_name', 'course_short_name', 'code', 'department__name', 'label')
    ordering = ('department', 'semester', 'code')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'course_name', 'course_short_name', 'department', 'course_type', 'code', 'semester')
        }),
        ('Credits & Marks', {
            'fields': ('max_credit', 'max_marks', 'min_marks')
        }),
        ('Assessment Details', {
            'fields': ('label', 'description')
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(PGStudentCourseAssessment)
class PGStudentCourseAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_type', 'course_code', 'semester', 'label', 
                   'ind_marks_obtained', 'comb_final_marks_obtained', 'comb_letter_grade', 'sem_result', 'ind_is_absent')
    list_filter = ('semester', 'course_type', 'exam_type', 'sem_result', 'ind_is_absent', 'session', 'batch')
    search_fields = ('student__first_name', 'student__last_name', 'student__roll_no', 'course_code', 'course_name', 'label')
    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Student & Course Info', {
            'fields': ('uid', 'student', 'course_name', 'course_short_name', 'course_type', 'course_code', 'paper_code', 'semester', 'label')
        }),
        ('Exam Details', {
            'fields': ('exam_type', 'session', 'batch', 'department', 'degree', 'college_code', 'attendance')
        }),
        ('Individual Assessment', {
            'fields': ('ind_max_marks', 'ind_pass_marks', 'ind_marks_obtained', 'ind_is_absent')
        }),
        ('Combined Assessment', {
            'fields': ('comb_max_marks', 'comb_max_credits', 'comb_pass_marks', 'comb_marks_obtained', 
                      'comb_grace_obtained', 'comb_final_marks_obtained', 'comb_credit_obtained', 
                      'comb_numeric_grade', 'comb_letter_grade')
        }),
        ('Course Assessment', {
            'fields': ('course_max_marks', 'course_max_credits', 'course_pass_marks', 'course_marks_obtained',
                      'course_grace_obtained', 'course_final_marks_obtained', 'course_credit_obtained', 'course_grade_point')
        }),
        ('Semester Assessment', {
            'fields': ('sem_max_credit', 'sem_credit_obtained', 'sgpa', 'sem_result', 'next_sem_status', 'sem_grace_obtained')
        }),
        ('Temp Fields', {
            'fields': ('temp_total_gp',),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(PGSemesterRegistration)
class PGSemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'is_open', 'exam_eligible', 'start_date', 'end_date')
    list_filter = ('sem', 'is_open', 'status', 'exam_eligible', 'session')
    search_fields = ('student__first_name', 'student__last_name', 'student__roll_no', 'session', 'remarks')
    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'student', 'sem', 'session')
        }),
        ('Registration Period', {
            'fields': ('start_date', 'end_date', 'is_open', 'status')
        }),
        ('Eligibility & Remarks', {
            'fields': ('exam_eligible', 'remarks')
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(PGExamRegistration)
class PGExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'is_open', 'fees', 'start_date', 'end_date')
    list_filter = ('sem', 'is_open', 'status', 'session')
    search_fields = ('student__first_name', 'student__last_name', 'student__roll_no', 'session')
    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'student', 'sem', 'session')
        }),
        ('Registration Period', {
            'fields': ('start_date', 'end_date', 'is_open', 'status')
        }),
        ('Fees', {
            'fields': ('fees',)
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )