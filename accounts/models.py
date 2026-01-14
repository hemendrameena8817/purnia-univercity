import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords



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
    choice = (
        ('student', 'Student'),
        ('college', 'College'),
        ('admin', 'Admin'),
    )
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=600, unique=True)
    email = models.EmailField(_('email address'), max_length=60, unique=True)
    first_name = models.CharField(_('first name'), max_length=40)
    last_name = models.CharField(_('last name'), max_length=40, blank=True, null=True)
    type = models.CharField(max_length=20, default='student')
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


class Product(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    history = HistoricalRecords()

    def __str__(self):
        return self.name



import uuid
from django.db import models


class University(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='university_logos/', null=True, blank=True)
    address = models.TextField()
    vice_chairman = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=15)
    email = models.EmailField()
    established_date = models.DateField()
    website = models.URLField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class College(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)
    college_code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    principal = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=15)
    email = models.EmailField()
    founded = models.DateField()
    website = models.URLField()
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='colleges')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class Department(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    head_of_faculty = models.CharField(max_length=255)
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='departments')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name




class Program(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    total_semesters = models.PositiveIntegerField()
    degree_level = models.CharField(
        max_length=10,
        choices=[('UG', 'UG'), ('PG', 'PG')]
    )
    total_years = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class Faculty(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    designation = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='faculties')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



class Student(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    student_no = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    email = models.EmailField(unique=True)
    batch = models.CharField(max_length=50)
    current_semester = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('Active', 'Active'), ('Suspended', 'Suspended'), ('Alumni', 'Alumni')]
    )
    enrollment_no = models.CharField(max_length=50, unique=True)
    roll_no = models.CharField(max_length=50, unique=True)
    father_name = models.CharField(max_length=255)
    mother_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10)
    profile_image = models.ImageField(upload_to='students/', null=True, blank=True)
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.student_no


