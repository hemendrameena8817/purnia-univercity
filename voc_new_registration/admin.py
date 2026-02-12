from django.contrib import admin
from .models import (
    NewRegistrationCourse, NewRegistrationBatch, NewRegistrationSession,
    NewRegistration, RegistrationPayment
)

@admin.register(NewRegistrationCourse)
class NewRegistrationCourseAdmin(admin.ModelAdmin):
    list_display = ('uid', 'code', 'name', 'registration_fee', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)
    readonly_fields = ('uid',)

@admin.register(NewRegistrationBatch)
class NewRegistrationBatchAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    readonly_fields = ('uid',)

@admin.register(NewRegistrationSession)
class NewRegistrationSessionAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    readonly_fields = ('uid',)

@admin.register(NewRegistration)
class NewRegistrationAdmin(admin.ModelAdmin):
    list_display = ('uid', 'student_name', 'registration_number', 'course', 'college', 'is_registration_completed', 'updated_at')
    search_fields = ('student_name', 'aadhaar_no', 'registration_number', 'mobile_no')
    list_filter = (
        'is_registration_completed', 
        'course',
        'college'
    )
    readonly_fields = ('created_at', 'updated_at', 'uid')

@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'registration', 'amount', 'payment_status', 'created_at')
    search_fields = ('order_id', 'registration__student_name', 'registration__aadhaar_no')
    list_filter = ('payment_status',)
    readonly_fields = ('raw_response', 'created_at', 'updated_at')
