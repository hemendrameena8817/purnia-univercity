import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class UserAccountManager(BaseUserManager):
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


# ✅ THIS MODEL WAS MISSING
class UserAccount(AbstractBaseUser, PermissionsMixin):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=600, unique=True)
    email = models.EmailField(_('email address'), max_length=60, unique=True)
    first_name = models.CharField(_('first name'), max_length=40)
    last_name = models.CharField(_('last name'), max_length=40, blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_active = models.BooleanField(_('active'), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()
