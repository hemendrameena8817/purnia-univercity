from django.contrib import admin
from .models import College


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'college_name_hindi', 'college_name_krutidev', 
        'short_name', 'college_code', 'center_code', 'principal', 'university', 'email'
    )
    search_fields = ('name', 'college_name_hindi', 'college_name_krutidev', 'short_name', 'college_code', 'center_code', 'email')
    list_filter = ('university',)
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'uid', 'name', 'college_name_hindi', 'college_name_krutidev', 
                'short_name', 'college_code', 'center_code', 'logo'
            )
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
