from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import UserAccount, CollegeUserProfile


class CollegeUserProfileInline(admin.StackedInline):
    model = CollegeUserProfile
    can_delete = False
    verbose_name_plural = 'College Profile'
    fk_name = 'user'
    extra = 0
    
    fieldsets = (
        ('College Assignment', {
            'fields': ('college', 'designation')
        }),
        ('Permissions', {
            'fields': (
                'can_manage_students', 
                'can_manage_marks', 
                'can_manage_results',
                'can_verify_data', 
                'can_approve_certificates'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(UserAccount)
class UserAccountAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "user_type",
        "get_college",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "user_type",
        "is_staff",
        "is_active",
        "is_verified",
    )

    search_fields = (
        "email",
        "username",
        "first_name",
        "last_name",
        "phone",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("username", "first_name", "last_name", "phone")}),
        (
            "Permissions",
            {
                "fields": (
                    "user_type",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "phone",
                    "password1",
                    "password2",
                    "user_type",
                ),
            },
        ),
    )
    
    inlines = [CollegeUserProfileInline]

    def get_college(self, obj):
        if hasattr(obj, 'college_profile') and obj.college_profile:
            return obj.college_profile.college.name
        return "-"
    get_college.short_description = "College"
    
    def get_inline_instances(self, request, obj=None):
        """Only show college profile inline for college users"""
        if obj and obj.user_type == 'college_user':
            return super().get_inline_instances(request, obj)
        return []


@admin.register(CollegeUserProfile)
class CollegeUserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'college',
        'designation',
        'can_manage_students',
        'can_manage_marks',
        'is_active',
    )
    
    list_filter = (
        'college',
        'is_active',
        'can_manage_students',
        'can_manage_marks',
        'can_verify_data',
        'can_approve_certificates',
    )
    
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'college__name',
        'college__college_code',
    )
    
    raw_id_fields = ('user', 'college')
    
    fieldsets = (
        ('User & College', {
            'fields': ('user', 'college')
        }),
        ('Role', {
            'fields': ('designation',)
        }),
        ('Permissions', {
            'fields': (
                'can_manage_students',
                'can_manage_marks',
                'can_manage_results',
                'can_verify_data',
                'can_approve_certificates',
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'college')
