import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class UserAccountManager(BaseUserManager):
    """
    Custom manager for UserAccount model.
    """
    def create_user(self, email, password=None, **kwargs):
        if not email:
            raise ValueError('Users must have a valid email address.')
        if not kwargs.get('username'):
            raise ValueError('Users must have a valid username.')

        account = self.model(
            email=self.normalize_email(email),
            username=kwargs.get('username'),
            first_name=kwargs.get('first_name', ''),
            last_name=kwargs.get('last_name', ''),
            is_staff=kwargs.get('is_staff', False),
            is_superuser=kwargs.get('is_superuser', False),
            is_active=kwargs.get('is_active', True),
            user_type=kwargs.get('user_type', 'student'),
        )
        account.set_password(password)
        account.save(using=self._db)
        return account

    def create_superuser(self, email, password, **kwargs):
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)

        if not kwargs.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not kwargs.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **kwargs)


class UserAccount(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for authentication.
    Supports different user types: student, college, admin.
    """
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('college', 'College'),
        ('admin', 'Admin'),
    ]
    
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(_('email address'), max_length=255, unique=True)
    first_name = models.CharField(_('first name'), max_length=100)
    last_name = models.CharField(_('last name'), max_length=100, blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')
    
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_active = models.BooleanField(_('active'), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User Account'
        verbose_name_plural = 'User Accounts'

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()
