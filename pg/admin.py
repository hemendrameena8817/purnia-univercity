from django.contrib import admin
from .models import (
    PGCourseStructure,
    PGStudentCourseAssessment,
    PGSemesterRegistration,
    PGExamRegistration
)


@admin.register(PGCourseStructure)
class PGCourseStructureAdmin(admin.ModelAdmin):
    """
    Admin configuration for PG Course Structure
    """
    list_display = [
        'name',
        'department',
        'course_type',
        'code',
        'semester',
        'max_credit',
        'max_marks',
        'label',
        'created_at'
    ]
    
    list_filter = [
        'course_type',
        'semester',
        'department',
        'created_at'
    ]
    
    search_fields = [
        'name',
        'code',
        'course_type',
        'department__name',
        'label'
    ]
    
    readonly_fields = ['uid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'department', 'course_type', 'code', 'semester')
        }),
        ('Credits & Marks', {
            'fields': ('max_credit', 'min_credit', 'max_marks', 'min_mark')
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
    
    list_per_page = 25
    ordering = ['department', 'semester', 'code']


@admin.register(PGStudentCourseAssessment)
class PGStudentCourseAssessmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for PG Student Course Assessment
    """
    list_display = [
        'student',
        'course_type',
        'code',
        'semester',
        'label',
        'marks_obtained',
        'max_marks',
        'grade',
        'exam_result',
        'is_absent',
        'session'
    ]
    
    list_filter = [
        'semester',
        'course_type',
        'exam_type',
        'exam_result',
        'is_absent',
        'session',
        'batch',
        'created_at'
    ]
    
    search_fields = [
        'student__user__first_name',
        'student__user__last_name',
        'student__roll_no',
        'code',
        'course_type',
        'label'
    ]
    
    readonly_fields = ['uid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Student & Course Info', {
            'fields': ('uid', 'student', 'course_type', 'code', 'semester', 'label')
        }),
        ('Credits & Marks Configuration', {
            'fields': ('max_credit', 'min_credit', 'max_marks', 'min_mark')
        }),
        ('Assessment Results', {
            'fields': ('marks_obtained', 'credit_obtained', 'grade', 'numeric_grade')
        }),
        ('Exam Details', {
            'fields': ('is_absent', 'exam_type', 'exam_result', 'session', 'batch')
        }),
        ('Description', {
            'fields': ('description',),
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
    
    list_per_page = 50
    ordering = ['-created_at']
    date_hierarchy = 'created_at'


@admin.register(PGSemesterRegistration)
class PGSemesterRegistrationAdmin(admin.ModelAdmin):
    """
    Admin configuration for PG Semester Registration
    """
    list_display = [
        'student',
        'sem',
        'session',
        'status',
        'is_open',
        'exam_eligible',
        'start_date',
        'end_date',
        'created_at'
    ]
    
    list_filter = [
        'sem',
        'is_open',
        'status',
        'exam_eligible',
        'session',
        'created_at'
    ]
    
    search_fields = [
        'student__user__first_name',
        'student__user__last_name',
        'student__roll_no',
        'session',
        'remarks'
    ]
    
    readonly_fields = ['uid', 'created_at', 'updated_at']
    
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
    
    list_per_page = 50
    ordering = ['-created_at']
    date_hierarchy = 'start_date'


@admin.register(PGExamRegistration)
class PGExamRegistrationAdmin(admin.ModelAdmin):
    """
    Admin configuration for PG Exam Registration
    """
    list_display = [
        'student',
        'sem',
        'session',
        'status',
        'is_open',
        'fees',
        'start_date',
        'end_date',
        'created_at'
    ]
    
    list_filter = [
        'sem',
        'is_open',
        'status',
        'session',
        'created_at'
    ]
    
    search_fields = [
        'student__user__first_name',
        'student__user__last_name',
        'student__roll_no',
        'session'
    ]
    
    readonly_fields = ['uid', 'created_at', 'updated_at']
    
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
    
    list_per_page = 50
    ordering = ['-created_at']
    date_hierarchy = 'start_date'
   