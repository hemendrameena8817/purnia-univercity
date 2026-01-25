from django.contrib import admin
from .models import VocNewRegistration


@admin.register(VocNewRegistration)
class VocNewRegistrationAdmin(admin.ModelAdmin):
    """
    Admin interface for VOC New Registration model.
    """
    list_display = [
        'student_name',
        'course',
        'batch',
        'gender',
        'mobile_no',
        'college',
        'migration_submitted',
        'created_at',
    ]
    list_filter = [
        'course',
        'batch',
        'gender',
        'caste',
        'migration_submitted',
        'migrated_from_other_university',
        'college',
        'created_at',
    ]
    search_fields = [
        'student_name',
        'student_name_hindi',
        'father_name',
        'mother_name',
        'mobile_no',
        'email',
        'aadhaar_no',
        'apaar_no',
        'old_registration_no',
    ]
    readonly_fields = ['uid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                'uid',
                'profile_picture',
                'signature',
                'student_name',
                'student_name_hindi',
                'father_name',
                'mother_name',
            )
        }),
        ('Course & Category', {
            'fields': (
                'course',
                'batch',
                'gender',
                'caste',
                'dob',
            )
        }),
        ('Contact Information', {
            'fields': (
                'mobile_no',
                'email',
                'aadhaar_no',
                'apaar_no',
            )
        }),
        ('Admission Details', {
            'fields': (
                'migration_submitted',
                'migrated_from_other_university',
                'last_attended_university',
                'old_registration_no',
                'is_account_created',
                'is_registration_completed',
                'college',
            )
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    

    ordering = ['-created_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('college')
