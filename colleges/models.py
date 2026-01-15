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


class Program(models.Model):
    """
    Represents an Academic Program (e.g., BCA, BBA, MBA).
    """
    DEGREE_LEVEL_CHOICES = [
        ('UG', 'Undergraduate'),
        ('PG', 'Postgraduate'),
    ]
    
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    total_semesters = models.PositiveIntegerField()
    degree_level = models.CharField(max_length=10, choices=DEGREE_LEVEL_CHOICES)
    total_years = models.PositiveIntegerField()
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='programs',
        null=True,
        blank=True
    )
    json_data = models.JSONField(null=True, blank=True)
    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='programs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'

    def __str__(self):
        return f"{self.name} ({self.get_degree_level_display()})"


class Course(models.Model):
    """
    Represents a Course/Subject within a Program.
    Courses are offered in specific semesters of a program.
    """
    COURSE_TYPE_CHOICES = [
        ('Theory', 'Theory'),
        ('Practical', 'Practical'),
        ('Theory + Practical', 'Theory + Practical'),
    ]
    
    COURSE_CATEGORY_CHOICES = [
        ('Major', 'Major'),
        ('Minor', 'Minor'),
        ('Foundation', 'Foundation'),
        ('SEC', 'Skill Enhancement Course'),
        ('VAC', 'Value Added Course'),
        ('AEC', 'Ability Enhancement Course'),
        ('GE', 'Generic Elective'),
    ]
    
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Academic details
    credits = models.PositiveIntegerField(default=0)
    theory_marks = models.PositiveIntegerField(default=0, help_text='Maximum theory marks')
    practical_marks = models.PositiveIntegerField(default=0, help_text='Maximum practical marks')
    internal_marks = models.PositiveIntegerField(default=0, help_text='Maximum internal/assignment marks')
    total_marks = models.PositiveIntegerField(default=100, help_text='Total maximum marks')
    passing_marks = models.PositiveIntegerField(default=40, help_text='Minimum passing marks')
    
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES, default='Theory')
    course_category = models.CharField(max_length=20, choices=COURSE_CATEGORY_CHOICES, default='Major', help_text='Major/Minor/Foundation etc.')
    semester = models.PositiveIntegerField(help_text='Semester in which this course is offered')
    
    # Relationships
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='courses'
    )
    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )
    
    # Optional: Which faculty teaches this course
    faculty = models.ForeignKey(
        'Faculty',
        on_delete=models.SET_NULL,
        related_name='courses',
        null=True,
        blank=True
    )
    
    is_elective = models.BooleanField(default=False, help_text='Is this an elective course?')
    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['program', 'semester', 'name']
        unique_together = ['program', 'code']  # Course code unique within a program

    def __str__(self):
        return f"{self.code} - {self.name} (Sem {self.semester})"


class Faculty(models.Model):
    """
    Faculty member in a Department.
    Basic user information comes from linked UserAccount.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Link to UserAccount (optional - faculty may or may not have login access)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.SET_NULL,
        related_name='faculty_profile',
        null=True,
        blank=True
    )
    
    # Faculty-specific fields (kept for faculty without user accounts)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    designation = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='faculties'
    )
    json_data = models.JSONField(null=True, blank=True)
    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='faculties'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculties'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        if self.user:
            return self.user.get_full_name()
        return f"{self.first_name} {self.last_name}"
