from django.contrib import admin
from .models import (
    NewRegistrationCourse, 
    NewRegistrationBatch, 
    NewRegistrationSession, 
    NewRegistration, 
    RegistrationPayment
)


@admin.register(NewRegistrationCourse)
class NewRegistrationCourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    search_fields = ['name', 'code']


@admin.register(NewRegistrationBatch)
class NewRegistrationBatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    search_fields = ['name']


@admin.register(NewRegistrationSession)
class NewRegistrationSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    search_fields = ['name']


@admin.register(NewRegistration)
class NewRegistrationAdmin(admin.ModelAdmin):
    """
    Admin interface for VOC New Registration model.
    """
    list_display = [
        'student_name',
        'course',
        'course_type',
        'batch',
        'gender',
        'mobile_no',
        'college',
        'migration_submitted',
        'is_registration_completed',
        'registration_number',
        'created_at',
    ]
    list_filter = [
        'course',
        'course_type',
        'batch',
        'gender',
        'caste',
        'migration_submitted',
        'migrated_from_other_university',
        'is_registration_completed',
        'college',
        'created_at',
    ]
    search_fields = [
        'student_name',
        'aadhaar_no',
        'mobile_no',
        'email',
    ]
    readonly_fields = ['uid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Student Information', {
            'fields': (
                'uid',
                'profile_picture',
                'signature',
                'migration_certificate',
                'registration_certificate',
                'student_name',
                'student_name_hindi',
                'father_name',
                'mother_name',
            )
        }),
        ('Course & Category', {
            'fields': (
                'course',
                'course_type',
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
                'registration_number',
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


@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'order_id',
        'registration',
        'amount',
        'payment_status',
        'payment_mode',
        'created_at',
    ]
    list_filter = ['payment_status', 'payment_mode', 'created_at']
    search_fields = ['order_id', 'tracking_id', 'registration__student_name', 'registration__aadhaar_no']
    readonly_fields = [
        'registration',
        'order_id',
        'tracking_id',
        'bank_ref_no',
        'amount',
        'payment_status',
        'payment_mode',
        'card_name',
        'raw_response',
        'created_at',
        'updated_at'
    ]
