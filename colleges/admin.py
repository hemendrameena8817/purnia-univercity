from django.contrib import admin
from .models import College, Department


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
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
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

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'code')
        }),
        ('Administration', {
            'fields': ('head_of_department', 'college')
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
