import uuid
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings
from .options import CASTE_CHOICES, GENDER_CHOICES
from pup_umis_backend.storage_backends import MediaStorage, DocumentStorage, ProfilePhotoStorage
from pup_umis_backend.upload_paths import unique_file_path

class NewRegistrationCourse(models.Model):
    """
    Local course model for Vocational registrations.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True)
    registration_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class NewRegistrationBatch(models.Model):
    """
    Local batch model for Vocational registrations.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'
        ordering = ['-name']

    def __str__(self):
        return self.name


class NewRegistrationSession(models.Model):
    """
    Local session model for Vocational registrations.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'
        ordering = ['-name']

    def __str__(self):
        return self.name


class NewRegistration(models.Model):
    """
    Model to store Vocational Course new registration data imported from Excel.
    """
    
    # UUID for unique identification
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    
    # Profile Images
    profile_picture = models.ImageField(
        upload_to=unique_file_path('voc_registrations/images/'),
        storage=MediaStorage(),
        null=True,
        blank=True
    )
    signature = models.ImageField(
        upload_to=unique_file_path('voc_registrations/signatures/'),
        storage=MediaStorage(),
        null=True,
        blank=True
    )
        
    # Certificates (PDF or Image)
    migration_certificate = models.FileField(
        upload_to=unique_file_path('voc_registrations/certificates/'),
        storage=DocumentStorage(),
        null=True,
        blank=True
    )
    registration_certificate = models.FileField(
        upload_to=unique_file_path('voc_registrations/certificates/'),
        storage=DocumentStorage(),
        null=True,
        blank=True
    )
    
    # Student Information
    student_name = models.CharField(max_length=255, help_text="Student name in English")
    student_name_hindi = models.CharField(max_length=255, null=True, blank=True, help_text="Student name in Hindi")
    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    caste = models.CharField(max_length=255, choices=CASTE_CHOICES, null=True, blank=True)
    dob = models.DateField(null=True, blank=True, help_text="Date of Birth")
    
    course = models.ForeignKey(
        NewRegistrationCourse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrations',
        help_text="Vocational Course"
    )
    batch = models.ForeignKey(
        NewRegistrationBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrations',
        help_text="Vocational Batch"
    )
    session = models.ForeignKey(
        NewRegistrationSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrations',
        help_text="Vocational Session"
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
    old_registration_no = models.CharField(max_length=255, null=True, blank=True)

    is_account_created = models.BooleanField(default=False)
    is_registration_completed = models.BooleanField(default=False)
    registration_number = models.CharField(max_length=50, null=True, blank=True, unique=True, help_text="Generated unique registration number")
    sr_no = models.IntegerField(null=True, blank=True, help_text="Serial number (last 5 digits of registration number)")

    
    # Soft Delete
    is_deleted = models.BooleanField(default=False)
    
    # Additional metadata
    json_data = models.JSONField(null=True, blank=True, help_text="Additional data from Excel")
    
    registration_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when registration was completed")

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
            models.Index(fields=['-sr_no']), 
        ]
    
    def save(self, *args, **kwargs):
        # Auto-set registration_at when is_registration_completed becomes True
        if self.is_registration_completed and not self.registration_at:
            self.registration_at = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student_name} - {self.course} - {self.college}"


class RegistrationPayment(models.Model):
    """
    Model to track payments for Vocational Course registrations via CC Avenue.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('ABORTED', 'Aborted'),
    ]

    registration = models.ForeignKey(
        NewRegistration,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    order_id = models.CharField(max_length=100, unique=True, help_text="Unique order ID sent to CC Avenue")
    tracking_id = models.CharField(max_length=100, null=True, blank=True, help_text="CC Avenue tracking ID")
    bank_ref_no = models.CharField(max_length=100, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    payment_mode = models.CharField(max_length=50, null=True, blank=True)
    card_name = models.CharField(max_length=50, null=True, blank=True)
    
    # Raw response from CC Avenue
    raw_response = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'VOC Registration Payment'
        verbose_name_plural = 'VOC Registration Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_id} - {self.registration.student_name} - {self.payment_status}"

