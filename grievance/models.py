import uuid
from django.db import models
from django.utils import timezone


ACTIVITY_STATUS_CHOICES = [
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
    ('canceled', 'Canceled'),
]

class GrievanceCategory(models.Model):
    """
    Dynamic categories for grievances.
    Allows admin to add/edit/remove categories without code changes.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Unique code for the category (e.g., 'academic', 'hostel')")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_assigned_to_college = models.BooleanField(default=True, help_text="Default to college level handling")
    is_assigned_to_university = models.BooleanField(default=False, help_text="Default to university level handling")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which to display categories")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Grievance Category'
        verbose_name_plural = 'Grievance Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class Grievance(models.Model):
    """
    Grievance/Complaint system for users.
    Auto-generates unique grievance number in format: GRVXXXXXXXXXX
    """
    
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    grievance_number = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    
    # User Information
    user = models.ForeignKey(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='grievances',
        null=True,
        blank=True
    )
    contact_person_name = models.CharField(max_length=255, null=True, blank=True) 
    contact_person_phone_number = models.CharField(max_length=15, null=True, blank=True)
    is_assigned_to_college = models.BooleanField(default=True)
    is_assigned_to_university = models.BooleanField(default=False)
    
    is_grievance_resolved = models.BooleanField(default=False)
    final_remark = models.TextField(null=True, blank=True)

    # Grievance Details
    category = models.ForeignKey(
        GrievanceCategory,
        on_delete=models.PROTECT,
        related_name='grievances',
        help_text="Category of the grievance"
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    # Note: Attachments are now in separate GrievanceAttachment model
    
    # Status and Assignment
    status = models.CharField(max_length=20, choices=ACTIVITY_STATUS_CHOICES, default='open')
    
    # Auto-assigned to student's college
    assigned_to_college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='grievances',
        null=True,
        blank=True
    )
    
    # Can be escalated to university
    escalated_to_university = models.BooleanField(default=False)
    assigned_to_university = models.ForeignKey(
        'university.University',
        on_delete=models.CASCADE,
        related_name='grievances',
        null=True,
        blank=True
    )
    
    # Handling
    handled_by = models.ForeignKey(
        'accounts.UserAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_grievances'
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  
    modified_by = models.ForeignKey(
        'accounts.UserAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_grievances',
        help_text="User who last modified this grievance"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Soft Delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.UserAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_grievances'
    )
    
    # Metadata
    json_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Grievance'
        verbose_name_plural = 'Grievances'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['grievance_number']),
            models.Index(fields=['status']),
            models.Index(fields=['-submitted_at']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate grievance number if not exists
        if not self.grievance_number:
            self.grievance_number = self.generate_grievance_number()
        
        # Initial routing based on Category flags
        if self._state.adding:
            self.is_assigned_to_college = self.category.is_assigned_to_college
            self.is_assigned_to_university = self.category.is_assigned_to_university
            
        # Standard Resolution Logic
        if self.status in ['resolved', 'canceled']:
            self.is_grievance_resolved = True
            if self.status == 'resolved' and not self.resolved_at:
                self.resolved_at = timezone.now()
        else:
            self.is_grievance_resolved = False

        # Auto-assign to user's college for tracking
        if not self.assigned_to_college and self.user:
            if hasattr(self.user, 'get_college'):
                self.assigned_to_college = self.user.get_college()
        
        super().save(*args, **kwargs)
    
    def generate_grievance_number(self):
        """Generate unique grievance number in sequence format GRV000001"""
        # Get count of all grievances to determine next sequential number.
        # We start with count + 1 and increment if we hit a collision
        sequence_number = Grievance.objects.all().count() + 1
        
        while True:
            grievance_number = f"GRV{sequence_number:06d}"
            # Check if it already exists to ensure uniqueness
            if not Grievance.objects.filter(grievance_number=grievance_number).exists():
                return grievance_number
            sequence_number += 1
    
    def escalate_to_university(self):
        """Escalate grievance to university level"""
        self.escalated_to_university = True
        self.status = 'escalated'
        if self.user and hasattr(self.user, 'get_college'):
            college = self.user.get_college()
            if college:
                self.assigned_to_university = college.university
        self.save()
    
    def delete(self, using=None, keep_parents=False, soft=True, deleted_by=None):
        """Override delete to implement soft delete by default"""
        if soft:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            if deleted_by:
                self.deleted_by = deleted_by
            self.save()
        else:
            # Hard delete (use with caution)
            super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """Restore a soft-deleted grievance"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    
    def __str__(self):
        return f"{self.grievance_number} - {self.subject}"


class GrievanceComment(models.Model):
    """
    Comments/Updates on grievances by college or university staff
    """
    
    COMMENT_TYPE_CHOICES = [
        ('comment', 'Comment'),
        ('status_update', 'Status Update'),
        ('escalation', 'Escalation'),
        ('resolution', 'Resolution'),
    ]
    
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    grievance = models.ForeignKey(
        Grievance,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    # Who commented
    commented_by = models.ForeignKey(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='grievance_comments'
    )
    
    # Comment details
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPE_CHOICES, default='comment')
    comment = models.TextField()
    
    # Status change tracking
    previous_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    
    # Note: Attachments are now in separate GrievanceAttachment model
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata
    is_internal = models.BooleanField(default=True) 
    json_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Grievance Comment'
        verbose_name_plural = 'Grievance Comments'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on {self.grievance.grievance_number} by {self.commented_by.username}"


class GrievanceAttachment(models.Model):
    """
    Attachments for grievances and comments.
    Supports multiple attachments per grievance/comment.
    """
    
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Link to grievance (optional until grievance is created)
    grievance = models.ForeignKey(
        Grievance,
        on_delete=models.CASCADE,
        related_name='attachments',
        null=True,
        blank=True,
        help_text="Linked when grievance is created"
    )
    
    # Link to comment (optional - if attachment is added with a comment)
    comment = models.ForeignKey(
        GrievanceComment,
        on_delete=models.CASCADE,
        related_name='attachments',
        null=True,
        blank=True,
        help_text="If this attachment is part of a comment"
    )
    
    # File details
    file = models.FileField(upload_to='grievances/attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255, help_text="Original filename")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=100, help_text="MIME type")
    
    # Uploaded by
    uploaded_by = models.ForeignKey(
        'accounts.UserAccount',
        on_delete=models.SET_NULL,
        null=True,
        related_name='grievance_attachments'
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Metadata
    description = models.CharField(max_length=255, blank=True, null=True, help_text="Optional description of the file")
    json_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Grievance Attachment'
        verbose_name_plural = 'Grievance Attachments'
        ordering = ['uploaded_at']
    
    def save(self, *args, **kwargs):
        """Auto-populate file metadata"""
        if self.file:
            # Get original filename
            if not self.file_name:
                self.file_name = self.file.name
            
            # Get file size
            if not self.file_size:
                self.file_size = self.file.size
            
            # Get MIME type
            if not self.file_type:
                import mimetypes
                self.file_type = mimetypes.guess_type(self.file.name)[0] or 'application/octet-stream'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.file_name} - {self.grievance.grievance_number}"
