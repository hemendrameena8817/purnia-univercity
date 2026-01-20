from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'registration_no',
        'get_first_name',
        'get_last_name',
        'roll_no',
        'college',
        'program',
        'current_semester',
        'session',
        'status',
    )

    search_fields = (
        'registration_no',
        'user__first_name',
        'user__last_name',
        'roll_no',
        'user__email',
    )

    list_filter = (
        'status',
        'college',
        'program',
        'department',
        'batch',
        'current_semester',
        'gender',
        'session',
    )

    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    autocomplete_fields = ['user', 'college', 'program', 'department']

    fieldsets = (
        ('User Account', {
            'fields': ('uid', 'user')
        }),
        ('Student Information', {
            'fields': ('registration_no', 'gender', 'date_of_birth', 'address')
        }),
        ('Family Information', {
            'fields': ('father_name', 'mother_name')
        }),
        ('Academic Information', {
            'fields': (
                'enrollment_date',
                'admission_date',
                'roll_no',
                'batch',
                'session',
                'current_semester',
                'status',
                'college',
                'department',
                'program',
            )
        }),
        ('Documents', {
            'fields': ('profile_image', 'signature')
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

    # 🔹 Display name fields from related UserAccount
    @admin.display(description='First Name', ordering='user__first_name')
    def get_first_name(self, obj):
        return obj.user.first_name

    @admin.display(description='Last Name', ordering='user__last_name')
    def get_last_name(self, obj):
        return obj.user.last_name

    @admin.display(description='Email', ordering='user__email')
    def get_email(self, obj):
        return obj.user.email