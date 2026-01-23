import uuid
from django.db import models


class University(models.Model):
    """
    Represents a University. In this system, all colleges belong to Purnea University.
    """
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='university_logos/', null=True, blank=True)
    address = models.TextField()
    vice_chancellor = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=15, blank=True)
    email = models.EmailField(unique=True)
    established_date = models.DateField()
    website = models.URLField(unique=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'University'
        verbose_name_plural = 'Universities'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['short_name']),
        ]

    def __str__(self):
        return self.name


class Faculty(models.Model):
    """
    Represents an Academic Faculty/School division of a University.
    Examples: Faculty of Social Science, Faculty of Humanities, Faculty of Science.
    Departments belong to a Faculty.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name='faculties'
    )

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculties'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Represents a Department within a Faculty (academic division).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    head_of_department = models.CharField(max_length=255, blank=True, null=True)

    faculty = models.ForeignKey(
        Faculty,
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
        return f"{self.name} ({self.faculty.short_name})"
