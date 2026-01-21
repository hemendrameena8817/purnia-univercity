import uuid
from django.db import models


class College(models.Model):
    """
    Represents a College affiliated to a University.
    Students belong to colleges, and colleges belong to the university.
    Multiple users can be associated with a college through CollegeUserProfile.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, null=True, blank=True)
    short_name = models.CharField(max_length=100, null=True, blank=True)
    college_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    principal = models.CharField(max_length=255, null=True, blank=True)
    contact_no = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    founded = models.DateField(null=True, blank=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='college_logos/', null=True, blank=True)

    university = models.ForeignKey(
        'university.University',
        on_delete=models.CASCADE,
        related_name='colleges',
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'College'
        verbose_name_plural = 'Colleges'

    def __str__(self):
        return self.name or self.college_code or str(self.uid)

    def get_admin_users(self):
        """Get all admin users for this college"""
        return self.users.filter(role__in=['principal', 'admin'], is_active=True)

    def get_all_users(self):
        """Get all users for this college"""
        return self.users.filter(is_active=True)