import uuid
from django.db import models


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
        'university.Department',
        on_delete=models.CASCADE,
        related_name='programs',
        null=True,
        blank=True
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


class CourseSlot(models.Model):
    """
    Represents a course slot in a semester curriculum.
    Example: MJC-1 in Semester 1, SEC-2 in Semester 3, etc.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=100, help_text='e.g., Major Course 1, SEC 2')
    
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name='course_slots'
    )
    
    course_type = models.ForeignKey(
        CourseType,
        on_delete=models.CASCADE,
        related_name='course_slots'
    )
    
    sequence_number = models.PositiveIntegerField(help_text='Sequence number (1, 2, 3...)')
    sequence_name = models.CharField(max_length=50, blank=True, null=True, help_text='e.g., MJC-1, SEC-2')
    
    credits = models.PositiveIntegerField(default=0)
    marks = models.PositiveIntegerField(default=100, help_text='Total marks for this slot')

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Course Slot'
        verbose_name_plural = 'Course Slots'
        ordering = ['semester', 'course_type', 'sequence_number']
        # unique_together = ['semester', 'course_type', 'sequence_number']

    def __str__(self):
        return f"{self.sequence_name or self.name} - Sem {self.semester.number}"


class Course(models.Model):
    """
    Represents a Course/Subject offered by a Department.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    department = models.ForeignKey(
        'university.Department',
        on_delete=models.CASCADE,
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
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProgramCourseStructure(models.Model):
    """
    Maps courses to course slots within a program's curriculum structure.
    Example: BCA Program -> MJC-1 slot in Sem 1 -> Introduction to Programming course
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='course_structure'
    )

    course_slot = models.ForeignKey(
        CourseSlot,
        on_delete=models.CASCADE,
        related_name='program_courses'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='program_structures'
    )

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Program Course Structure'
        verbose_name_plural = 'Program Course Structures'
        ordering = ['program', 'course_slot']
        # unique_together = ['program', 'course_slot', 'course']

    def __str__(self):
        return f"{self.program.short_name} - {self.course_slot.sequence_name} - {self.course.code}"


class BatchCourseStructure(models.Model):
    """
    Maps courses to course slots within a batch's curriculum structure.
    Similar to ProgramCourseStructure but specific to a batch.
    Example: BCA 2024-2028 batch -> MJC-1 slot in Sem 1 -> Introduction to Programming course
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='course_structure'
    )

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='batch_course_structure'
    )

    course_slot = models.ForeignKey(
        CourseSlot,
        on_delete=models.CASCADE,
        related_name='batch_courses'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='batch_structures'
    )

    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Batch Course Structure'
        verbose_name_plural = 'Batch Course Structures'
        ordering = ['batch', 'program', 'course_slot']
        # unique_together = ['batch', 'program', 'course_slot', 'course']

    def __str__(self):
        return f"{self.batch.name} - {self.program.short_name} - {self.course_slot.sequence_name} - {self.course.code}"


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
        'university.Department',
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