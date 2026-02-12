from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import UserAccount, CollegeUserProfile, UniversityUserProfile
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
            'fields': ('college', 'PG_department', 'designation')
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


class UniversityUserProfileInline(admin.StackedInline):
    model = UniversityUserProfile
    can_delete = False
    verbose_name_plural = 'University Profile'
    fk_name = 'user'
    extra = 0
    
    fieldsets = (
        ('Profile Info', {
            'fields': ('designation', 'department')
        }),
        ('Module Permissions', {
            'fields': (
                'can_manage_voc_registration',
                'can_manage_grievances',
                'can_manage_ug',
                'can_manage_pg',
                'can_manage_mca',
                'can_manage_btech',
                'can_manage_colleges',
                'can_manage_university_settings',
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
        "created_at",
        "updated_at",
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
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
        ("System Info", {"fields": ("uid",)}),
    )

    readonly_fields = ("uid", "created_at", "updated_at")

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
        UniversityUserProfileInline,
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
        
        # Show university profile for university admin
        elif obj.user_type == 'university_admin':
            inline_instances.append(UniversityUserProfileInline)
            
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
    
    def save_model(self, request, obj, form, change):
        """
        Save the user and ensure college_profile is synced for college users
        """
        super().save_model(request, obj, form, change)
        
        # For college users, ensure college_profile exists and matches
        if obj.user_type == 'college_user' and obj.college:
            # Get or create the college profile
            college_profile, created = CollegeUserProfile.objects.get_or_create(
                user=obj,
                defaults={
                    'college': obj.college,
                    'is_active': True
                }
            )
            
            # Update college if it changed
            if not created and college_profile.college != obj.college:
                college_profile.college = obj.college
                college_profile.save()
        
        # For university users, ensure university_profile exists
        elif obj.user_type == 'university_admin':
            UniversityUserProfile.objects.get_or_create(
                user=obj,
                defaults={'is_active': True}
            )
    
    def save_formset(self, request, form, formset, change):
        """
        Save inline formsets and ensure UserAccount.college is synced
        """
        instances = formset.save(commit=False)
        
        for instance in instances:
            # If this is a CollegeUserProfile inline
            if isinstance(instance, CollegeUserProfile):
                instance.save()
                # Sync the college field on UserAccount
                if instance.college and instance.user.college != instance.college:
                    instance.user.college = instance.college
                    instance.user.save(update_fields=['college'])
        
        # Delete removed instances
        for obj in formset.deleted_objects:
            obj.delete()
        
        formset.save_m2m()


@admin.register(CollegeUserProfile)
class CollegeUserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'college',
        'PG_department',
        'designation',
        'can_manage_students',
        'can_manage_marks',
        'can_manage_results',
        'can_verify_data',
        'can_approve_certificates',
        'is_active',
    )
    
    list_filter = (
        'college',
        'PG_department',
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
        'PG_department__name',
    )
    
    raw_id_fields = ('user', 'college', 'PG_department')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User & College', {
            'fields': ('user', 'college', 'PG_department')
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
            'fields': ('is_active', 'uid', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'college')


@admin.register(UniversityUserProfile)
class UniversityUserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'designation',
        'department',
        'can_manage_voc_registration',
        'can_manage_grievances',
        'is_active',
    )
    
    list_filter = (
        'department',
        'is_active',
        'can_manage_voc_registration',
        'can_manage_grievances',
    )
    
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'designation',
        'department',
    )
    
    raw_id_fields = ('user',)
    readonly_fields = ('uid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'designation', 'department')
        }),
        ('Module Permissions', {
            'fields': (
                'can_manage_voc_registration',
                'can_manage_grievances',
                'can_manage_ug',
                'can_manage_pg',
                'can_manage_mca',
                'can_manage_btech',
                'can_manage_colleges',
                'can_manage_university_settings',
            )
        }),
        ('Status', {
            'fields': ('is_active', 'uid', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
