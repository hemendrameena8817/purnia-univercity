from django.contrib import admin
from .models import (
    UGFaculty, UGDepartment, UGDegree, UGProgram, UGBatch, UGStudentProfile,
    CourseStructure, StudentCourseAssessment, SemesterRegistration, ExamRegistration,
    CommonCourseStructure
)


@admin.register(UGFaculty)
class UGFacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'university', 'created_at')
    list_filter = ('university',)
    search_fields = ('name', 'short_name')
    ordering = ('name',)


@admin.register(UGDepartment)
class UGDepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'faculty', 'head_of_department', 'created_at')
    list_filter = ('faculty',)
    search_fields = ('name', 'code', 'faculty__name')
    ordering = ('faculty', 'name')


@admin.register(UGDegree)
class UGDegreeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'total_semesters', 'total_years', 'created_at')
    search_fields = ('name', 'short_name')
    ordering = ('name',)


@admin.register(UGProgram)
class UGProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'degree', 'department', 'created_at')
    list_filter = ('degree', 'department__faculty')
    search_fields = ('name', 'short_name', 'degree__name', 'department__name')
    ordering = ('name',)


@admin.register(UGBatch)
class UGBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'program', 'created_at')
    list_filter = ('program',)
    search_fields = ('name', 'program__name')
    ordering = ('name',)


@admin.register(UGStudentProfile)
class UGStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'first_name', 'last_name', 'roll_no', 'college', 
                   'department', 'program', 'current_semester', 'status', 'is_active', 'batch')
    list_filter = ('status', 'gender', 'college', 'department', 'program', 'degree', 
                  'current_semester', 'batch')
    search_fields = ('registration_no', 'roll_no', 'first_name', 'last_name', 
                    'mobile_no', 'aadhar_no')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    # Performance optimizations for large datasets
    list_select_related = ('department', 'program', 'degree', 'batch', 'college')
    show_full_result_count = False
    list_per_page = 50
    raw_id_fields = ('user', 'department', 'program', 'degree', 'batch', 'college')
    
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
        ('Course Selections (CBCS)', {
            'fields': ('major_course', 'minor_course', 'mdc_course')
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


@admin.register(CourseStructure)
class CourseStructureAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_short_name', 'department', 'course_type', 'course_code', 'paper_code', 'semester', 'max_marks', 'max_credit')
    list_filter = ('course_type', 'semester', 'course_code', 'department__faculty', 'department', )
    search_fields = ('course_name', 'course_short_name', 'course_code', 'department__name')
    ordering = ('department', 'semester', 'course_code')


@admin.register(StudentCourseAssessment)
class StudentCourseAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'label', 'course_type', 'paper_code', 'ind_marks_obtained', 'comb_letter_grade')
    list_filter = ('semester', 'label', 'course_type', 'exam_type', 'ind_is_absent')
    search_fields = ('student__registration_no', 'student__first_name', 'student__last_name', 'paper_code')
    ordering = ('-created_at',)
    
    # Performance optimizations for large datasets
    list_select_related = ('student', 'department', 'batch')  # Reduce DB queries for ForeignKeys
    show_full_result_count = False  # Disable expensive COUNT(*) query
    list_per_page = 50  # Reduce records per page (default is 100)
    
    # Optional: Add raw_id_fields for faster FK selection in forms
    raw_id_fields = ('student', 'department', 'batch')


@admin.register(SemesterRegistration)
class SemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'status', 'exam_eligible', 'is_open')
    list_filter = ('sem', 'status', 'exam_eligible', 'is_open')
    search_fields = ('student__registration_no', 'student__first_name')
    ordering = ('student', 'sem')


@admin.register(ExamRegistration)
class ExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'status', 'fees', 'is_open')
    list_filter = ('sem', 'status', 'is_open')
    search_fields = ('student__registration_no', 'student__first_name')
    ordering = ('student', 'sem')

@admin.register(CommonCourseStructure)
class CommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('semester', 'course_type','code', 'course_name', 'ltp', 'credit', 'marks')
    list_filter = ('semester', 'course_type')
    search_fields = ('semester', 'course_name', 'course_type')
    ordering = ('semester', 'course_type')
