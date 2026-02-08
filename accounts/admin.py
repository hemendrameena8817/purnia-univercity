from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import UserAccount, CollegeUserProfile
from mca_sem.models import MCAStudentProfile
from plw.models import PLWStudentProfile
from ug.models import UGStudentProfile
from pg.models import PGStudentProfile


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


class MCAStudentProfileInline(admin.StackedInline):
    model = MCAStudentProfile
    can_delete = False
    verbose_name_plural = 'MCA Student Profile'
    fk_name = 'user'
    extra = 0


class PLWStudentProfileInline(admin.StackedInline):
    model = PLWStudentProfile
    can_delete = False
    verbose_name_plural = 'PLW Student Profile'
    fk_name = 'user'
    extra = 0


class UGStudentProfileInline(admin.StackedInline):
    model = UGStudentProfile
    can_delete = False
    verbose_name_plural = 'UG Student Profile'
    fk_name = 'user'
    extra = 0


class PGStudentProfileInline(admin.StackedInline):
    model = PGStudentProfile
    can_delete = False
    verbose_name_plural = 'PG Student Profile'
    fk_name = 'user'
    extra = 0


@admin.register(UserAccount)
class UserAccountAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "user_type",
        "current_profile",
        "get_college",
        "is_staff",
        "is_active",
        "college"
    )

    list_filter = (
        "user_type",
        "current_profile",
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
        (None, {"fields": ("email", "password")} ),
        ("Personal Info", {"fields": ("username", "first_name", "last_name", "phone", "college")} ),
        (
            "Permissions",
            {
                "fields": (
                    "user_type",
                    "current_profile",
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
                    "college",
                    "password1",
                    "password2",
                    "user_type",
                    "current_profile",
                ),
            },
        ),
    )
    
    inlines = [
        CollegeUserProfileInline,
        MCAStudentProfileInline,
        PLWStudentProfileInline,
        UGStudentProfileInline,
        PGStudentProfileInline
    ]

    def get_college(self, obj):
        if hasattr(obj, 'college_profile') and obj.college_profile:
            return obj.college_profile.college.name
        return "-"
    get_college.short_description = "College"
    
    def get_inline_instances(self, request, obj=None):
        """Show relevant profile inline based on user type and current profile"""
        if not obj:
            return []
            
        inline_instances = []
        
        # Show college profile for college users
        if obj.user_type == 'college_user':
            inline_instances.append(CollegeUserProfileInline)
            
        # Show student profile based on current_profile
        elif obj.user_type == 'student':
            if obj.current_profile == 'mca_sem':
                inline_instances.append(MCAStudentProfileInline)
            elif obj.current_profile == 'plw':
                inline_instances.append(PLWStudentProfileInline)
            elif obj.current_profile == 'ug':
                inline_instances.append(UGStudentProfileInline)
            elif obj.current_profile == 'pg':
                inline_instances.append(PGStudentProfileInline)
                
        return [inline(self.model, self.admin_site) for inline in inline_instances]


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
