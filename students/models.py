import uuid
from django.db import models


class Student(models.Model):
    """
    Student profile linked to a UserAccount.
    Basic user information (first_name, last_name, email) comes from UserAccount.
    """

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Alumni', 'Alumni'),
    ]

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Link to UserAccount
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='student_profile'
    )

    # Student-specific Information
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    hindi_name  = models.CharField(max_length=250,null=True, blank=True)
    
    registration_no = models.CharField(max_length=50, unique=True, db_index=True)
    address = models.TextField()
    admission_date = models.DateField()
    date_of_birth = models.DateField()
    aadhar_no = models.CharField(max_length=12, null=True, blank=True)
    mobile_no = models.CharField(max_length=15,null=True,blank=True)
    migration_submitted = models.BooleanField(default=False)
    last_university = models.CharField(max_length=100, null=True, blank=True)

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    caste = models.CharField(max_length=20, null=True, blank=True)
    enrollment_date = models.DateField()
    # enrollment_no = models.CharField(max_length=50, unique=True, db_index=True)
    roll_no = models.CharField(max_length=50, unique=True, db_index=True)
    batch = models.CharField(max_length=50)

    # Family Information
    father_name = models.CharField(max_length=255)
    mother_name = models.CharField(max_length=255)

    # Academic Information
    current_semester = models.PositiveIntegerField()
    session = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    # Relationships
    college = models.ForeignKey('colleges.College', on_delete=models.CASCADE, related_name='student_college')
    department = models.ForeignKey('university.Department', on_delete=models.CASCADE, related_name='student_department', null=True, blank=True)
    program = models.ForeignKey('academics.Program', on_delete=models.CASCADE, related_name='student_program', null=True, blank=True)
    major_course = models.CharField(max_length=250, null=True, blank=True)
    minor_course = models.CharField(max_length=250, null=True, blank=True)
    mdc_course = models.CharField(max_length=250, null=True, blank=True)
    degree = models.ForeignKey('academics.Degree', on_delete=models.CASCADE, related_name='student_degree', null=True, blank=True)

    # Documents
    profile_image = models.ImageField(upload_to='students/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='students/signatures/', null=True, blank=True)

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.enrollment_no})"

    # 🔹 Proxy fields from UserAccount
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.enrollment_no})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
