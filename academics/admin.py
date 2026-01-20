from django.contrib import admin
from .models import Faculty, Degree, Batch, Session, Semester, Program, CourseType, Course, Designation, Professor


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    """Admin for Academic Faculty divisions (Faculty of Science, etc.)"""
    list_display = ('name', 'short_name', 'university')
    search_fields = ('name', 'short_name')
    list_filter = ('university',)
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'short_name', 'description')
        }),
        ('University', {
            'fields': ('university',)
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


@admin.register(Degree)
class DegreeAdmin(admin.ModelAdmin):
    """Admin for Degree types (BCA, MBA, B.Tech, etc.)"""
    list_display = ('name', 'degree_level', 'total_semesters', 'total_years')
    search_fields = ('name',)
    list_filter = ('degree_level',)
    ordering = ('degree_level', 'name')
    readonly_fields = ('uid', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name')
        }),
        ('Academic Details', {
            'fields': ('degree_level', 'total_semesters', 'total_years')
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


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    """Admin for Student Batches (e.g., 2024-2028)"""
    list_display = ('name', 'start_year', 'end_year', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active', 'start_year')
    ordering = ('-start_year',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_editable = ('is_active',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'start_year', 'end_year', 'is_active')
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


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin for Academic Sessions (e.g., 2024-2025)"""
    list_display = ('name', 'start_date', 'end_date', 'is_current')
    search_fields = ('name',)
    list_filter = ('is_current',)
    ordering = ('-start_date',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_editable = ('is_current',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'start_date', 'end_date', 'is_current')
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


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    """Admin for Semesters"""
    list_display = ('number', 'name', 'start_date', 'end_date', 'is_current')
    search_fields = ('name',)
    list_filter = ('is_current', 'number')
    ordering = ('number',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_editable = ('is_current',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'number', 'name')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'is_current')
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


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'degree', 'get_degree_level', 'get_total_semesters', 'department', 'college')
    search_fields = ('name', 'degree__name', 'degree__short_name')
    list_filter = ('degree__degree_level', 'degree', 'department', 'college')
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name')
        }),
        ('Degree', {
            'fields': ('degree',)
        }),
        ('Relationships', {
            'fields': ('college', 'department')
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

    @admin.display(description='Level')
    def get_degree_level(self, obj):
        return obj.degree.get_degree_level_display()

    @admin.display(description='Semesters')
    def get_total_semesters(self, obj):
        return obj.degree.total_semesters


@admin.register(CourseType)
class CourseTypeAdmin(admin.ModelAdmin):
    """Admin for Course Types (MJC, MNC, SEC, etc.)"""
    list_display = ('code', 'name', 'credits')
    search_fields = ('code', 'name')
    ordering = ('code',)
    readonly_fields = ('uid', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'code', 'name', 'credits', 'description')
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


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'program', 'semester', 'course_type', 'is_elective', 'is_active'
    )
    search_fields = ('name', 'code', 'course_type__code', 'course_type__name')
    list_filter = (
        'program', 'semester', 'course_type',
        'is_elective', 'is_active', 'college'
    )
    ordering = ('program', 'semester', 'name')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    list_editable = ('is_active',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'code', 'description')
        }),
        ('Course Classification', {
            'fields': ('course_type',)
        }),
        ('Academic Details', {
            'fields': (
                'program', 'semester', 'is_elective'
            )
        }),
        ('Assignments', {
            'fields': ('college', 'professor'),
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


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    """Admin for Professor Designations"""
    list_display = ('name', 'short_name', 'level')
    search_fields = ('name', 'short_name')
    list_filter = ('level',)
    ordering = ('level', 'name')
    readonly_fields = ('uid', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'short_name', 'level')
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


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'designation', 'department', 'college', 'has_login')
    search_fields = ('first_name', 'last_name', 'email', 'designation__name')
    list_filter = ('designation', 'department', 'college')
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
        ('Position', {
            'fields': ('designation', 'department', 'college')
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

    @admin.display(description='Has Login', boolean=True)
    def has_login(self, obj):
        return obj.user is not None

