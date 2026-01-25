import uuid
from django.db import models


class VocNewRegistration(models.Model):
    """
    Model to store Vocational Course new registration data imported from Excel.
    """
    
    # Gender choices
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    # Caste choices
    CASTE_CHOICES = [
        ('GEN', 'General'),
        ('OBC', 'OBC'),
        ('SC', 'SC'),
        ('ST', 'ST'),
        ('EWS', 'EWS'),
        ('EBC', 'EBC'),
        ('RBC', 'RBC'),
        ('FDC', 'FDC'),
    ]

    # UUID for unique identification
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    
    # Profile Images
    profile_picture = models.ImageField(upload_to='voc_registrations/images/', null=True, blank=True)
    signature = models.ImageField(upload_to='voc_registrations/signatures/', null=True, blank=True)
    
    # Student Information
    student_name = models.CharField(max_length=255, help_text="Student name in English")
    student_name_hindi = models.CharField(max_length=255, null=True, blank=True, help_text="Student name in Hindi")
    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    caste = models.CharField(max_length=10, choices=CASTE_CHOICES, null=True, blank=True)
    dob = models.DateField(null=True, blank=True, help_text="Date of Birth")
    
    course = models.ForeignKey(
        'academics.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voc_registrations_course',
        help_text="Linked to Academics Course"
    )
    batch = models.ForeignKey(
        'academics.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voc_registrations_batch',
        help_text="Linked to Academics Batch"
    )
    session = models.ForeignKey(
        'academics.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voc_registrations_session',
        help_text="Linked to Academics Session"
    )
    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voc_new_registrations',
        help_text="College where student is registered"
    )
    
    # Contact Information
    mobile_no = models.CharField(max_length=15, null=True, blank=True)
    aadhaar_no = models.CharField(max_length=12, null=True, blank=True, help_text="12-digit Aadhaar number")
    apaar_no = models.CharField(max_length=12, null=True, blank=True, help_text="12-digit Apaar number")
    email = models.EmailField(null=True, blank=True)
    
    # Admission Details
    migration_submitted = models.BooleanField(default=False)

    migrated_from_other_university = models.BooleanField(default=False)
    last_attended_university = models.CharField(max_length=255, null=True, blank=True)

    is_account_created = models.BooleanField(default=False)
    is_registration_completed = models.BooleanField(default=False)
    
    # Soft Delete
    is_deleted = models.BooleanField(default=False)
    
    # Additional metadata
    json_data = models.JSONField(null=True, blank=True, help_text="Additional data from Excel")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'VOC New Registration'
        verbose_name_plural = 'VOC New Registrations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student_name']),
            models.Index(fields=['course']),
            models.Index(fields=['college']),
            models.Index(fields=['aadhaar_no']),
        ]
    
    def __str__(self):
        return f"{self.student_name} - {self.course} - {self.college}"


