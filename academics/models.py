import uuid
from django.db import models


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
        'university.University',
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


class Degree(models.Model):
    """
    Represents a Degree type (e.g., Bachelor of Computer Applications, Master of Business Administration).
    Programs are mapped to Degrees.
    """
    DEGREE_LEVEL_CHOICES = [
        ('UG', 'Undergraduate'),
        ('PG', 'Postgraduate'),
    ]

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, unique=True, help_text='e.g., B.Tech, M.Tech, MCA')
    degree_level = models.CharField(max_length=20, choices=DEGREE_LEVEL_CHOICES)
    total_semesters = models.PositiveIntegerField()
    total_years = models.PositiveIntegerField()

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Degree'
        verbose_name_plural = 'Degrees'
        ordering = ['degree_level', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_degree_level_display()})"


class Batch(models.Model):
    """
    Represents a student batch (admission year to graduation year).
    Example: 2024-2028 for a 4-year program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=50, unique=True, help_text='e.g., 2024-2028')
    start_year = models.PositiveIntegerField(help_text='Admission year')
    end_year = models.PositiveIntegerField(help_text='Graduation year')
    is_active = models.BooleanField(default=True)

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'
        ordering = ['-start_year']

    def __str__(self):
        return self.name


class Session(models.Model):
    """
    Represents an academic session/year.
    Example: 2024-2025
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=50, unique=True, help_text='e.g., 2024-2025')
    start_date = models.DateField(help_text='Session start date')
    end_date = models.DateField(help_text='Session end date')
    is_current = models.BooleanField(default=False, help_text='Is this the current active session?')

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class Semester(models.Model):
    """
    Represents a semester within a session.
    Example: Semester 1, Semester 2, etc.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    number = models.PositiveIntegerField(help_text='Semester number (1, 2, 3...)')
    name = models.CharField(max_length=50, blank=True, help_text='Optional name e.g., First Semester')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Semester'
        verbose_name_plural = 'Semesters'
        ordering = ['number']

    def __str__(self):
        return f"Semester {self.number}" if not self.name else self.name


class Program(models.Model):
    """
    Represents an Academic Program offered by a College.
    A Program is linked to a Degree (e.g., BCA program under Bachelor of Computer Applications degree).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, help_text='Program name e.g., BCA (Hons), MBA Finance')
    short_name = models.CharField(max_length=50, help_text='e.g., BCA, MBA, B.Tech')
    # Link to Degree
    degree = models.ForeignKey(
        Degree,
        on_delete=models.CASCADE,
        related_name='programs'
    )

    department = models.ForeignKey(
        'colleges.Department',
        on_delete=models.CASCADE,
        related_name='programs',
        null=True,
        blank=True
    )

    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='programs'
    )

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'

    def __str__(self):
        return f"{self.name} ({self.degree.short_name})"

    @property
    def degree_level(self):
        return self.degree.degree_level

    @property
    def total_semesters(self):
        return self.degree.total_semesters

    @property
    def total_years(self):
        return self.degree.total_years


class CourseType(models.Model):
    """
    Represents a course type/category.
    Examples: MJC (Major Course), MNC (Minor Course), SEC, VAC, AEC, GE.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=100, unique=True, help_text='e.g., Major Course, Minor Course')
    code = models.CharField(max_length=20, unique=True, help_text='e.g., MJC, MNC, SEC, VAC')
    credits = models.PositiveIntegerField(default=0, help_text='Default credits for this course type')
    description = models.TextField(blank=True, null=True)

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Course Type'
        verbose_name_plural = 'Course Types'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"





class Course(models.Model):
    """
    Represents a Course/Subject within a Program.
    Courses are offered in specific semesters of a program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    # Course Type (MJC, MNC, SEC, etc.)
    course_type = models.ForeignKey(
        CourseType,
        on_delete=models.SET_NULL,
        related_name='courses',
        null=True,
        blank=True
    )

    # Academic details

    semester = models.PositiveIntegerField(help_text='Semester in which this course is offered')

    # Relationships
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='courses'
    )

    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )

    # Optional: Which professor teaches this course
    professor = models.ForeignKey(
        'Professor',
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
        unique_together = ['program', 'code']

    def __str__(self):
        return f"{self.code} - {self.name} (Sem {self.semester})"

    @property
    def effective_credits(self):
        """Returns course credits, falling back to course type default if 0"""
        if self.credits > 0:
            return self.credits
        return self.course_type.credits if self.course_type else 0


class Designation(models.Model):
    """
    Represents academic designations for professors.
    Examples: Assistant Professor, Associate Professor, Professor, HOD, Dean.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=20, blank=True, null=True)
    level = models.PositiveIntegerField(default=1, help_text='Seniority level (1=lowest)')

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Designation'
        verbose_name_plural = 'Designations'
        ordering = ['level', 'name']

    def __str__(self):
        return self.name


class Professor(models.Model):
    """
    Professor/Teacher in a Department.
    Basic user information comes from linked UserAccount.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Link to UserAccount (optional - professor may or may not have login access)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.SET_NULL,
        related_name='professor_profile',
        null=True,
        blank=True
    )

    # Professor-specific fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        related_name='professors',
        null=True,
        blank=True
    )

    department = models.ForeignKey(
        'colleges.Department',
        on_delete=models.CASCADE,
        related_name='professors'
    )

    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='professors'
    )

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Professor'
        verbose_name_plural = 'Professors'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        if self.user:
            return self.user.get_full_name()
        return f"{self.first_name} {self.last_name}"

