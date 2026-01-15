from django.contrib import admin
from .models import College, Department, Program, Course, Faculty


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'college_code', 'principal', 'university', 'email')
    search_fields = ('name', 'short_name', 'college_code', 'email')
    list_filter = ('university',)
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'short_name', 'college_code', 'logo')
        }),
        ('Admin User', {
            'fields': ('admin_user',),
            'description': 'Link a user account for college administrator login'
        }),
        ('Contact Information', {
            'fields': ('address', 'contact_no', 'email', 'website')
        }),
        ('Administration', {
            'fields': ('principal', 'founded', 'university')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_of_department', 'college')
    search_fields = ('name', 'code')
    list_filter = ('college', 'college__university')
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'degree_level', 'total_semesters', 'total_years', 'department')
    search_fields = ('name', 'code')
    list_filter = ('degree_level', 'department')
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'program', 'semester', 'course_category', 'course_type', 'credits', 'total_marks', 'is_elective', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('program', 'semester', 'course_category', 'course_type', 'is_elective', 'is_active', 'college')
    ordering = ('program', 'semester', 'name')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'code', 'description')
        }),
        ('Academic Details', {
            'fields': ('program', 'semester', 'course_category', 'course_type', 'credits', 'is_elective')
        }),
        ('Marks Configuration', {
            'fields': ('theory_marks', 'practical_marks', 'internal_marks', 'total_marks', 'passing_marks')
        }),
        ('Assignments', {
            'fields': ('college', 'faculty'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'designation', 'department', 'has_login')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('department', 'designation')
    ordering = ('first_name', 'last_name')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Account', {
            'fields': ('uid', 'user'),
            'description': 'Optional - link to user account for login access'
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Department Information', {
            'fields': ('designation', 'department')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Has Login', boolean=True)
    def has_login(self, obj):
        return obj.user is not None
