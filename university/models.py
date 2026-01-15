import uuid
from django.db import models


class University(models.Model):
    """
    Represents a University. In this system, all colleges belong to Purnea University.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='university_logos/', null=True, blank=True)
    address = models.TextField()
    vice_chancellor = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=15)
    email = models.EmailField()
    established_date = models.DateField()
    website = models.URLField()
    json_data = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'University'
        verbose_name_plural = 'Universities'

    def __str__(self):
        return self.name
