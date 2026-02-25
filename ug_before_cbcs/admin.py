"""
Django Admin for UG Before CBCS - Simplified Models
====================================================
Admin interface for the simplified models.
Now only 3 models: StudentProfile, Exam, and StudentResult.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UGBeforeCBCSStudentProfile,
    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult
)

@admin.register(UGBeforeCBCSStudentProfile)
class UGBeforeCBCSStudentProfileAdmin(admin.ModelAdmin):
    show_full_result_count = False  # Faster loading for large tables
    list_display = (
        'registration_no',
        'student_name',
        'roll_no',
        'fathers_name',
        'mothers_name',
        'gender',
        'course_code',
        'discipline_code',
        'college',
        'is_active',
        'created_at'
    )
    list_per_page = 50
    list_select_related = ('user', 'college')
    list_filter = (
        'is_active',
        'course_code',
        'discipline_code',
        'gender',
        'college'
    )
    search_fields = (
        'registration_no',
        'roll_no',
        'student_name',
        'fathers_name'
    )
    raw_id_fields = ['user', 'college']
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

@admin.register(UGBeforeCBCSExam)
class UGBeforeCBCSExamAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_display = (
        'exam_code',
        'name',
        'part',
        'semester_code',
        'exam_year',
        'batch_code',
        'session_code',
        'course_code',
        'is_published',
        'is_active'
    )
    list_per_page = 50
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
        'semester_code',
        'results__registration_no'
    )
    readonly_fields = ('uid', 'created_at', 'updated_at')
    date_hierarchy = 'publication_date'
    fieldsets = (
        ('Exam Identity', {
            'fields': ('uid', 'name', 'exam_code', 'centre_name')
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
    """Admin for Student Results optimized for 2.5 Million+ records"""
    show_full_result_count = False  # DO NOT remove - critical for performance on 2M+ rows
    
    list_display = (
        'registration_no',  # Display denormalized reg_no for speed
        'student_link',
        'exam_link',
        'paper_code',
        'subject_name',
        'exam_type',
        'theory',
        'practical',
        'mark_secured',
        'maximum_mark',
        'subject_result_badge',
        'final_result',
        'is_absent'
    )
    
    list_per_page = 50
    list_select_related = ('student', 'exam')
    
    list_filter = (
        'exam__course_code',
        'exam__part',
        'exam_type',
        'is_ex_regular',
        'is_absent',
        'subject_result',
        'final_result'
    )
    
    search_fields = (
        'registration_no',  
        'student__student_name',
        'paper_code',
        'exam__exam_code'
    )
    
    raw_id_fields = ['student', 'exam']
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_editable = ('is_absent',)
    
    fieldsets = (
        ('Identity', {
            'fields': ('uid', 'registration_no', 'student', 'exam')
        }),
        ('Subject Details', {
            'fields': (
                'paper_code',
                'subject_code',
                'subject_name',
                'paper_type_code',
            )
        }),
        ('Marks', {
            'fields': (
                'theory',
                'practical',
                'sessional',
                'mark_secured',
                'maximum_mark',
                'pass_mark',
                'subject_result'
            )
        }),
        ('Exam Summary', {
            'fields': (
                'total_secured_mark',
                'total_secured_mark_1',
                'total_secured_mark_2',
                'grand_total_mark',
                'hon',
                'total_per',
                'grade',
                'final_result',
                'agreegate'
            )
        }),
        ('Additional Info', {
            'fields': (
                'is_absent',
                'is_ex_regular',
                'exam_type',
                'status',
                'grace_chk',
                'record_status'
            ),
            'classes': ('collapse',)
        }),
        ('Source \u0026 Metadata', {
            'fields': (
                'source_id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset for massive tables"""
        return super().get_queryset(request).select_related('student', 'exam')
    
    @admin.display(description='Student', ordering='student__registration_no')
    def student_link(self, obj):
        return obj.student.student_name
    
    @admin.display(description='Exam', ordering='exam__exam_code')
    def exam_link(self, obj):
        return f"{obj.exam.name} ({obj.exam.exam_year})"
    
    @admin.display(description='Result')
    def subject_result_badge(self, obj):
        if not obj.subject_result:
            return '-'
        
        result = str(obj.subject_result).upper()
        if 'PASS' in result:
            color = '#28a745'  # Green
        elif 'FAIL' in result:
            color = '#dc3545'  # Red
        else:
            color = '#ffc107'  # Amber
            
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.subject_result
        )
    
    class Media:
        css = {
            'all': ['admin/css/ug_results.css']
        }