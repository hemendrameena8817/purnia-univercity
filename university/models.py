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
