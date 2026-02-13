"""
Django Admin for UG Before CBCS - Simplified Models
====================================================
Admin interface for the 5 simplified models.
Use this file after migrating to the new structure.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UGBeforeCBCSStudentProfile,
    UGBeforeCBCSSubject,
    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult,
    UGBeforeCBCSExamSummary
)


@admin.register(UGBeforeCBCSStudentProfile)
class UGBeforeCBCSStudentProfileAdmin(admin.ModelAdmin):
    """Admin for Student Profiles"""
    list_display = (
        'registration_no',
        'student_name',
        'roll_no',
        'course_code',
        'discipline_code',
        'college_display',
        'is_active',
        'created_at'
    )
    list_filter = (
        'is_active',
        'course_code',
        'discipline_code',
        'college',
        'gender',
        'created_at'
    )
    search_fields = (
        'registration_no',
        'roll_no',
        'student_name',
        'fathers_name',
        'mothers_name',
        'source_user_id'
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'user', 'registration_no', 'roll_no')
        }),
        ('Personal Details', {
            'fields': (
                'student_name',
                'student_name_hindi',
                'fathers_name',
                'mothers_name',
                'gender',
                'dob'
            )
        }),
        ('Academic Association', {
            'fields': ('college', 'course_code', 'discipline_code')
        }),
        ('Source Data', {
            'fields': ('source_user_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def college_display(self, obj):
        if obj.college:
            return obj.college.name
        return '-'
    college_display.short_description = 'College'


@admin.register(UGBeforeCBCSSubject)
class UGBeforeCBCSSubjectAdmin(admin.ModelAdmin):
    """Admin for Subjects"""
    list_display = (
        'paper_code',
        'subject_name',
        'subject_code',
        'subject_type',
        'maximum_mark',
        'pass_mark',
        'has_theory',
        'has_practical',
        'is_active'
    )
    list_filter = (
        'is_active',
        'subject_type',
        'has_theory',
        'has_practical',
        'has_sessional'
    )
    search_fields = (
        'paper_code',
        'subject_code',
        'subject_name',
        'temp_paper_code',
        'paper_code_correction',
        'subject_code_correction'
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Subject Identification', {
            'fields': (
                'uid',
                'paper_code',
                'subject_code',
                'subject_name',
                'subject_type'
            )
        }),
        ('Additional Codes (from Staging)', {
            'fields': (
                'temp_paper_code',
                'paper_code_correction',
                'subject_code_correction',
                'paper_type_code'
            ),
            'classes': ('collapse',)
        }),
        ('Marks Configuration', {
            'fields': (
                'maximum_mark',
                'pass_mark',
                'has_theory',
                'has_practical',
                'has_sessional'
            )
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UGBeforeCBCSExam)
class UGBeforeCBCSExamAdmin(admin.ModelAdmin):
    """Admin for Exams"""
    list_display = (
        'exam_code',
        'name',
        'part',
        'exam_year',
        'batch_code',
        'session_code',
        'course_code',
        'is_published',
        'is_active'
    )
    list_filter = (
        'is_active',
        'is_published',
        'part',
        'exam_year',
        'course_code',
        'batch_code'
    )
    search_fields = (
        'exam_code',
        'name',
        'batch_code',
        'session_code',
        'semester_code'
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')
    date_hierarchy = 'publication_date'
    
    fieldsets = (
        ('Exam Identity', {
            'fields': ('uid', 'name', 'exam_code')
        }),
        ('Part & Year', {
            'fields': (
                'part',
                'semester_code',
                'exam_year',
                'exam_month_year'
            )
        }),
        ('Session & Batch', {
            'fields': ('session_code', 'batch_code')
        }),
        ('Course/Discipline', {
            'fields': ('course_code', 'discipline_code')
        }),
        ('Publication', {
            'fields': (
                'publication_date',
                'is_published',
                'published_at'
            )
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UGBeforeCBCSStudentResult)
class UGBeforeCBCSStudentResultAdmin(admin.ModelAdmin):
    """Admin for Student Results"""
    list_display = (
        'student_display',
        'exam_display',
        'subject_display',
        'exam_type',
        'theory',
        'practical',
        'mark_secured',
        'subject_result_badge'
    )
    list_filter = (
        'exam_type',
        'is_ex_regular',
        'is_absent',
        'subject_result',
        'exam__part',
        'exam__exam_year'
    )
    search_fields = (
        'student__registration_no',
        'student__student_name',
        'subject__paper_code',
        'subject__subject_name',
        'source_id'
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Relationships', {
            'fields': ('uid', 'student', 'exam', 'subject')
        }),
        ('Exam Type & Status', {
            'fields': (
                'exam_type',
                'exam_type_his',
                'is_ex_regular',
                'status'
            )
        }),
        ('Marks', {
            'fields': (
                'theory',
                'practical',
                'sessional',
                'mark_secured',
                'mark_secured_history',
                'subject_total_mark',
                'maximum_mark',
                'pass_mark'
            )
        }),
        ('Subject Results', {
            'fields': (
                'subject_result',
                'subject_result_1',
                'subject_result_2',
                'sub_reult_com'
            )
        }),
        ('Additional Fields', {
            'fields': (
                'is_absent',
                'grace_chk',
                'remark',
                'student_check'
            ),
            'classes': ('collapse',)
        }),
        ('Source Tracking', {
            'fields': ('source_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def student_display(self, obj):
        return f"{obj.student.registration_no} - {obj.student.student_name}"
    student_display.short_description = 'Student'
    
    def exam_display(self, obj):
        return f"{obj.exam.exam_code}"
    exam_display.short_description = 'Exam'
    
    def subject_display(self, obj):
        return f"{obj.subject.paper_code}"
    subject_display.short_description = 'Subject'
    
    def subject_result_badge(self, obj):
        if not obj.subject_result:
            return '-'
        
        result_upper = obj.subject_result.upper()
        if 'PASS' in result_upper:
            color = 'green'
            icon = '✓'
        elif 'FAIL' in result_upper:
            color = 'red'
            icon = '✗'
        elif 'ABS' in result_upper:
            color = 'orange'
            icon = '⊘'
        else:
            color = 'gray'
            icon = '•'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.subject_result
        )
    subject_result_badge.short_description = 'Result'


@admin.register(UGBeforeCBCSExamSummary)
class UGBeforeCBCSExamSummaryAdmin(admin.ModelAdmin):
    """Admin for Exam Summaries"""
    list_display = (
        'student_display',
        'exam_display',
        'total_secured_mark',
        'grand_total_mark',
        'total_per',
        'grade',
        'final_result_badge',
        'is_published'
    )
    list_filter = (
        'is_published',
        'final_result',
        'grade',
        'exam__part',
        'exam__exam_year',
        'agreegate'
    )
    search_fields = (
        'student__registration_no',
        'student__student_name',
        'exam__exam_code',
        'exam__name'
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('Relationships', {
            'fields': ('uid', 'student', 'exam')
        }),
        ('Grand Totals', {
            'fields': (
                'grand_total_mark',
                'total_secured_mark',
                'total_secured_mark_1',
                'total_secured_mark_2',
                'hon'
            )
        }),
        ('Percentage & Grade', {
            'fields': ('total_per', 'grade')
        }),
        ('Final Result & Aggregate', {
            'fields': (
                'final_result',
                'agreegate',
                'aggregate_hindi'
            )
        }),
        ('Status & Checks', {
            'fields': (
                'record_status',
                'record_status_check',
                'subject_count'
            ),
            'classes': ('collapse',)
        }),
        ('Publication', {
            'fields': ('is_published', 'published_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def student_display(self, obj):
        return f"{obj.student.registration_no} - {obj.student.student_name}"
    student_display.short_description = 'Student'
    
    def exam_display(self, obj):
        return f"{obj.exam.name}"
    exam_display.short_description = 'Exam'
    
    def final_result_badge(self, obj):
        if not obj.final_result:
            return '-'
        
        result_upper = obj.final_result.upper()
        if 'PASS' in result_upper:
            color = 'green'
            icon = '✓'
        elif 'FAIL' in result_upper:
            color = 'red'
            icon = '✗'
        elif 'PROMOTED' in result_upper:
            color = 'blue'
            icon = '↑'
        elif 'ABSENT' in result_upper:
            color = 'orange'
            icon = '⊘'
        else:
            color = 'gray'
            icon = '•'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.final_result
        )
    final_result_badge.short_description = 'Final Result'
