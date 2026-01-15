import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class UserAccountManager(BaseUserManager):
    """
    Custom manager for UserAccount model.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Users must have a valid email address."))
        if not extra_fields.get("username"):
            raise ValueError(_("Users must have a valid username."))

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            username=extra_fields.get("username"),
            first_name=extra_fields.get("first_name", ""),
            last_name=extra_fields.get("last_name", ""),
            user_type=extra_fields.get("user_type", "student"),
            is_staff=extra_fields.get("is_staff", False),
            is_superuser=extra_fields.get("is_superuser", False),
            is_active=extra_fields.get("is_active", True),
            is_verified=extra_fields.get("is_verified", False),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class UserAccount(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for authentication.
    Supports different user types: student, college, admin.
    """

    USER_TYPE_CHOICES = [
        ("student", "Student"),
        ("college", "College"),
        ("admin", "Admin"),
    ]

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(_("email address"), max_length=255, unique=True)
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100, blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default="student")

    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(_("staff status"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User Account"
        verbose_name_plural = "User Accounts"

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()
