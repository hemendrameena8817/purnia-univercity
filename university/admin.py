from django.contrib import admin
from django.utils.html import format_html
from .models import University


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'short_name',
        'logo_preview',
        'vice_chancellor',
        'email',
        'contact_no',
        'established_date',
    )
    
    search_fields = (
        'name',
        'short_name',
        'email',
        'vice_chancellor',
    )
    
    list_filter = ('established_date',)
    ordering = ('name',)
    
    readonly_fields = ('uid', 'created_at', 'updated_at', 'logo_preview')

    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'name', 'short_name', 'logo', 'logo_preview')
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

    def logo_preview(self, obj):
        """
        Display a small preview of the university logo in the admin panel.
        """
        if obj.logo:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:contain;" />', obj.logo.url)
        return "No Logo"
    
    logo_preview.short_description = "Logo Preview"

    def has_add_permission(self, request):
        """
        Allow only one University record in the system.
        Remove this method if you want to allow multiple universities.
        """
        return not University.objects.exists()
