from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export.formats.base_formats import CSV, XLSX, JSON
from .models import (
    NewRegistrationCourse, NewRegistrationBatch, NewRegistrationSession,
    NewRegistration, RegistrationPayment
)
from .resources import (
    NewRegistrationResource, NewRegistrationCourseResource,
    NewRegistrationBatchResource, NewRegistrationSessionResource
)

@admin.register(NewRegistrationCourse)
class NewRegistrationCourseAdmin(ImportExportModelAdmin):
    resource_class = NewRegistrationCourseResource
    list_display = ('uid', 'code', 'name', 'registration_fee', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)
    readonly_fields = ('uid',)
    
    # Export formats
    formats = [CSV, XLSX, JSON]

@admin.register(NewRegistrationBatch)
class NewRegistrationBatchAdmin(ImportExportModelAdmin):
    resource_class = NewRegistrationBatchResource
    list_display = ('uid', 'name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    readonly_fields = ('uid',)
    
    # Export formats
    formats = [CSV, XLSX, JSON]

@admin.register(NewRegistrationSession)
class NewRegistrationSessionAdmin(ImportExportModelAdmin):
    resource_class = NewRegistrationSessionResource
    list_display = ('uid', 'name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    readonly_fields = ('uid',)
    
    # Export formats
    formats = [CSV, XLSX, JSON]

@admin.register(NewRegistration)
class NewRegistrationAdmin(ImportExportModelAdmin):
    resource_class = NewRegistrationResource
    
    list_display = (
        'uid', 
        'student_name', 
        'registration_number', 
        'course', 
        'college', 
        'registration_status_badge',
        'updated_at'
    )
    search_fields = ('student_name', 'aadhaar_no', 'registration_number', 'mobile_no', 'email')
    list_filter = (
        'is_registration_completed',
        'migrated_from_other_university',
        'is_account_created',
        'is_deleted',
        'course',
        'college',
        'batch',
        'session',
        'gender',
        'caste',
        ('created_at', admin.DateFieldListFilter),
        ('registration_at', admin.DateFieldListFilter),
    )
    readonly_fields = ('created_at', 'updated_at', 'uid', 'registration_at')
    
    # Export formats
    formats = [CSV, XLSX, JSON]
    
    # Fields to display in detail view
    fieldsets = (
        ('Basic Information', {
            'fields': ('uid', 'student_name', 'student_name_hindi', 'father_name', 'mother_name')
        }),
        ('Personal Details', {
            'fields': ('dob', 'gender', 'caste')
        }),
        ('Contact Information', {
            'fields': ('mobile_no', 'email', 'aadhaar_no', 'apaar_no')
        }),
        
        ('Academic Details', {
            'fields': ('course', 'batch', 'session', 'college')
        }),
        ('Registration Details', {
            'fields': ('registration_number', 'sr_no', 'old_registration_no', 'is_registration_completed', 'registration_at')
        }),
        ('Migration Details', {
            'fields': ('migrated_from_other_university', 'last_attended_university', 'migration_submitted')
        }),
        ('Documents', {
            'fields': ('profile_picture', 'signature', 'migration_certificate', 'registration_certificate')
        }),
        ('Status', {
            'fields': ('is_account_created', 'is_deleted')
        }),
        ('Metadata', {
            'fields': ('json_data', 'created_at', 'updated_at')
        }),
    )
    
    def registration_status_badge(self, obj):
        """Display registration status with color badge"""
        if obj.is_registration_completed:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">✓ Completed</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">⏳ Pending</span>'
            )
    registration_status_badge.short_description = 'Status'
    
    # Custom actions
    actions = ['export_as_csv', 'export_as_excel', 'mark_as_completed', 'mark_as_pending']
    
    def mark_as_completed(self, request, queryset):
        """Mark selected registrations as completed"""
        updated = queryset.update(is_registration_completed=True)
        self.message_user(request, f'{updated} registration(s) marked as completed.')
    mark_as_completed.short_description = 'Mark selected as Completed'
    
    def mark_as_pending(self, request, queryset):
        """Mark selected registrations as pending"""
        updated = queryset.update(is_registration_completed=False)
        self.message_user(request, f'{updated} registration(s) marked as pending.')
    mark_as_pending.short_description = 'Mark selected as Pending'

@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('order_id', 'registration_student', 'amount', 'payment_status_badge', 'payment_mode', 'created_at')
    search_fields = ('order_id', 'tracking_id', 'bank_ref_no', 'registration__student_name', 'registration__aadhaar_no')
    list_filter = (
        'payment_status',
        'payment_mode',
        ('created_at', admin.DateFieldListFilter),
    )
    readonly_fields = ('raw_response', 'created_at', 'updated_at')
    
    # Export formats
    formats = [CSV, XLSX, JSON]
    
    def registration_student(self, obj):
        """Display student name from registration"""
        return obj.registration.student_name
    registration_student.short_description = 'Student Name'
    registration_student.admin_order_field = 'registration__student_name'
    
    def payment_status_badge(self, obj):
        """Display payment status with color badge"""
        colors = {
            'SUCCESS': '#28a745',
            'PENDING': '#ffc107',
            'FAILED': '#dc3545',
            'ABORTED': '#6c757d',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        text_color = 'white' if obj.payment_status != 'PENDING' else 'black'
        
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, text_color, obj.payment_status
        )
    payment_status_badge.short_description = 'Payment Status'
    payment_status_badge.admin_order_field = 'payment_status'
