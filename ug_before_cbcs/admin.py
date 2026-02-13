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
    list_display = (
        'registration_no',
        'student_name',
        'roll_no',
        'fathers_name',
        'mothers_name',
        'gender',
        'course_code',
        'discipline_code',
        'college_display',
        'is_active',
        'created_at'
    )
    list_per_page = 50
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

@admin.register(UGBeforeCBCSExam)
class UGBeforeCBCSExamAdmin(admin.ModelAdmin):
    list_display = (
        'exam_code',
        'name',
        'part',
        'semester_code',
        'exam_year',
        'exam_month_year',
        'batch_code',
        'session_code',
        'course_code',
        'discipline_code',
        'publication_date',
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
    """Admin for Student Results with optimized list view"""
    list_display = (
        'student_display',
        'exam_display',
        'paper_code',
        'subject_name',
        'exam_type',
        'theory',
        'practical',
        'sessional',
        'mark_secured',
        'maximum_mark',
        'pass_mark',
        'subject_result_badge',
        'is_absent',
        'is_ex_regular',
        'total_secured_mark',
        'grade',
        'final_result'
    )
    
    list_per_page = 50
    list_select_related = ('student', 'exam')  # Optimize DB queries
    
    list_filter = (
        'exam_type',
        'is_ex_regular',
        'is_absent',
        'subject_result',
        'final_result',
        'exam__part',
        'exam__exam_year'
    )
    
    search_fields = (
        'student__registration_no',
        'student__student_name',
        'paper_code',
        'subject_name',
        'exam__exam_code',
        'source_id'
    )
    
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_editable = ('is_absent', 'is_ex_regular')  # Allow quick editing
    
    fieldsets = (
        ('Relationships', {
            'fields': ('uid', 'student', 'exam')
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
        ('Source & Metadata', {
            'fields': (
                'source_id',
                'registration_no',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset to reduce database queries"""
        return super().get_queryset(request).select_related(
            'student', 'exam'
        ).only(
            'student__registration_no',
            'student__student_name',
            'exam__name',
            'exam__exam_year',
            'paper_code',
            'subject_name',
            'exam_type',
            'theory',
            'practical',
            'sessional',
            'mark_secured',
            'maximum_mark',
            'pass_mark',
            'subject_result',
            'is_absent',
            'is_ex_regular',
            'total_secured_mark',
            'grade',
            'final_result'
        )
    
    @admin.display(description='Student')
    def student_display(self, obj):
        return f"{obj.student.registration_no} - {obj.student.student_name}"
    
    @admin.display(description='Exam')
    def exam_display(self, obj):
        return f"{obj.exam.name} ({obj.exam.exam_year})"
    
    @admin.display(description='Result')
    def subject_result_badge(self, obj):
        if not obj.subject_result:
            return '-'
        
        result = str(obj.subject_result).upper()
        if 'PASS' in result:
            color = 'green'
        elif 'FAIL' in result:
            color = 'red'
        else:
            color = 'orange'
            
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color, obj.subject_result
        )
    
    class Media:
        css = {
            'all': ['admin/css/ug_results.css']
        }