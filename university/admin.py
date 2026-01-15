from django.contrib import admin
from .models import University


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'vice_chancellor', 'email', 'contact_no', 'established_date')
    search_fields = ('name', 'short_name', 'email')
    list_filter = ('established_date',)
    ordering = ('name',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'short_name', 'logo')
        }),
        ('Contact Information', {
            'fields': ('address', 'contact_no', 'email', 'website')
        }),
        ('Administration', {
            'fields': ('vice_chancellor', 'established_date')
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
