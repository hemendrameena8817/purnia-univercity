import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class UserAccountManager(BaseUserManager):
    """
    Custom manager for UserAccount model.
    """

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError(_("Users must have a valid username."))

        if email:
            email = self.normalize_email(email)

        user = self.model(
            email=email,
            username=username,
            first_name=extra_fields.get("first_name", ""),
            last_name=extra_fields.get("last_name", ""),
            user_type=extra_fields.get("user_type", "student"),
            current_profile=extra_fields.get("current_profile"),
            is_staff=extra_fields.get("is_staff", False),
            is_superuser=extra_fields.get("is_superuser", False),
            is_active=extra_fields.get("is_active", True),
            is_verified=extra_fields.get("is_verified", False),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "university_admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(username, email, password, **extra_fields)


class UserAccount(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for authentication.
    Supports different user types with role-based access control.
    """

    USER_TYPE_CHOICES = [
        ("university_admin", "University Admin"),
        ("college_user", "College User"), 
        ("student", "Student"),
        ("examiner", "Examiner"),
    ]

    PROFILE_TYPE_CHOICES = [
        ("mca_sem", "MCA Semester"),
        ("plw", "Pre-Law"),
        ("ug", "Undergraduate"),
        ("pg", "Postgraduate"),
        ("btech", "B.Tech"),
        ("mba", "MBA"),
    ]

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(_("email address"), max_length=255, blank=True, null=True)
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default="student")
    current_profile = models.CharField(max_length=20, choices=PROFILE_TYPE_CHOICES, blank=True, null=True)
    college = models.ForeignKey('colleges.College', on_delete=models.CASCADE, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(_("staff status"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserAccountManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []  # email is optional now

    class Meta:
        verbose_name = "User Account"
        verbose_name_plural = "User Accounts"

    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()

    def is_college_user(self):
        """Check if user is a college user"""
        return self.user_type == "college_user"

    def is_student_user(self):
        """Check if user is a student"""
        return self.user_type == "student"

    def is_university_user(self):
        """Check if user is a university admin"""
        return self.user_type == "university_admin"

    def get_college(self):
        """Get the college associated with this user (if any)"""
        if hasattr(self, 'college_profile') and self.college_profile:
            return self.college_profile.college
        return None


class CollegeUserProfile(models.Model):
    """
    Profile for college users (admin/staff).
    Allows multiple users to be associated with one college.
    """
    
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    user = models.OneToOneField(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='college_profile',
        limit_choices_to={'user_type': 'college_user'}
    )
    
    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='users'
    )
    
    designation = models.CharField(max_length=100, blank=True, null=True)
    PG_department = models.ForeignKey(
        "pg.PGDepartment",
        on_delete=models.CASCADE,
        related_name='pg_department_users',
        null=True,
        blank=True
    )
    # Permissions
    can_manage_students = models.BooleanField(default=False)
    can_manage_marks = models.BooleanField(default=False)
    can_manage_results = models.BooleanField(default=False)
    can_verify_data = models.BooleanField(default=False)
    can_approve_certificates = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "College User Profile"
        verbose_name_plural = "College User Profiles"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.college.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class UniversityUserProfile(models.Model):
    """
    Profile for university admin users.
    Allows granular permission control for different modules.
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='university_profile',
        limit_choices_to={'user_type': 'university_admin'}
    )
    
    designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True) # e.g. Registration Section, Exam Section
    
    # Granular Module Permissions
    can_manage_voc_registration = models.BooleanField(default=False)
    can_manage_grievances = models.BooleanField(default=False)
    can_manage_ug = models.BooleanField(default=False)
    can_manage_pg = models.BooleanField(default=False)
    can_manage_mca = models.BooleanField(default=False)
    can_manage_btech = models.BooleanField(default=False)
    can_manage_colleges = models.BooleanField(default=False)
    can_manage_university_settings = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "University User Profile"
        verbose_name_plural = "University User Profiles"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.designation or 'University Admin'}"

