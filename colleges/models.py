import uuid
from django.db import models


class College(models.Model):
    """
    Represents a College affiliated to a University.
    Students belong to colleges, and colleges belong to the university.
    The 'admin_user' is the college administrator who can login and manage college data.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Link to UserAccount for college admin
    admin_user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.SET_NULL,
        related_name='college_profile',
        null=True,
        blank=True,
        help_text='The user account for college administrator'
    )

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)
    college_code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    principal = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=15)
    email = models.EmailField()
    founded = models.DateField()
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='college_logos/', null=True, blank=True)

    university = models.ForeignKey(
        'university.University',
        on_delete=models.CASCADE,
        related_name='colleges'
    )

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'College'
        verbose_name_plural = 'Colleges'

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Represents a Department within a College.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    head_of_department = models.CharField(max_length=255)

    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='departments'
    )

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return f"{self.name} - {self.college.short_name}"