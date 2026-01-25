import uuid
from django.db import models


class PGFaculty(models.Model):
    """
    Represents a PG Faculty/School division.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    university = models.ForeignKey(
        'university.University',
        on_delete=models.CASCADE,
        related_name='pg_faculties'
    )

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Faculty'
        verbose_name_plural = 'PG Faculties'
        ordering = ['name']

    def __str__(self):
        return self.name


class PGDepartment(models.Model):
    """
    Represents a PG Department within a Faculty.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=50, null=True, blank=True)
    head_of_department = models.CharField(max_length=255, blank=True, null=True)

    faculty = models.ForeignKey(
        PGFaculty,
        on_delete=models.CASCADE,
        related_name='departments'
    )

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Department'
        verbose_name_plural = 'PG Departments'

    def __str__(self):
        return f"{self.name} ({self.faculty.short_name or self.faculty.name})"


class PGDegree(models.Model):
    """
    Represents a PG Degree type (e.g., Master of Arts, Master of Science).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, unique=True, help_text='e.g., M.A., M.Sc., M.Com., MBA, MCA')
    short_name = models.CharField(max_length=50, null=True, blank=True, help_text='e.g., MA, MSc')
    total_semesters = models.PositiveIntegerField(default=4)
    total_years = models.PositiveIntegerField(default=2)

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Degree'
        verbose_name_plural = 'PG Degrees'
        ordering = ['name']

    def __str__(self):
        return self.name


class PGProgram(models.Model):
    """
    Represents a PG Academic Program (e.g., M.A. History, M.Sc. Physics).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, help_text='Program name e.g., M.A. History')
    short_name = models.CharField(max_length=50, null=True, blank=True, help_text='e.g., MA History')

    degree = models.ForeignKey(
        PGDegree,
        on_delete=models.CASCADE,
        related_name='programs'
    )

    department = models.ForeignKey(
        PGDepartment,
        on_delete=models.CASCADE,
        related_name='programs',
        null=True,
        blank=True
    )

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Program'
        verbose_name_plural = 'PG Programs'

    def __str__(self):
        return f"{self.name}"

    @property
    def total_semesters(self):
        return self.degree.total_semesters

    @property
    def total_years(self):
        return self.degree.total_years


class PGBatch(models.Model):
    """
    Represents a batch of students in a program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, help_text='Batch name e.g., 2023-2025')
    program = models.ForeignKey(
        PGProgram,
        on_delete=models.CASCADE,
        related_name='batches',
        null=True,
        blank=True
    )
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Batch'
        verbose_name_plural = 'PG Batches'
        ordering = ['name']

    def __str__(self):
        return self.name

class PGStudentProfile(models.Model):
    """
    PG Student profile linked to a UserAccount.
    Contains postgrad-specific course selections: CC, SEC, EC.
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
        related_name='pg_student_profile'
    )

    # Student-specific Information
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    hindi_name = models.CharField(max_length=250, null=True, blank=True)
    
    registration_no = models.CharField(max_length=50, unique=True, db_index=True)
    address = models.TextField(null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    aadhar_no = models.CharField(max_length=12, null=True, blank=True)
    apaar_id = models.CharField(max_length=12, blank=True, null=True)
    mobile_no = models.CharField(max_length=15, null=True, blank=True)
    migration_submitted = models.BooleanField(default=False)
    last_university = models.CharField(max_length=100, null=True, blank=True)

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    caste = models.CharField(max_length=20, null=True, blank=True)
    # enrollment_date = models.DateField(null=True, blank=True)
    roll_no = models.CharField(max_length=50, null=True, blank=True)
    batch = models.CharField(max_length=50, null=True, blank=True)

    # Family Information
    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)

    # Academic Information
    current_semester = models.PositiveIntegerField(null=True, blank=True)
    session = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    # Relationships
    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='pg_students',
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        PGDepartment,
        on_delete=models.CASCADE,
        related_name='students',
        null=True,
        blank=True
    )
    program = models.ForeignKey(
        PGProgram,
        on_delete=models.CASCADE,
        related_name='students',
        null=True,
        blank=True
    )
    degree = models.ForeignKey(
        PGDegree,
        on_delete=models.CASCADE,
        related_name='students',
        null=True,
        blank=True
    )

    # PG-specific course selections
    cc_course = models.CharField(max_length=250, null=True, blank=True, help_text="Core Course (CC)")
    sec_course = models.CharField(max_length=250, null=True, blank=True, help_text="Skill Enhancement Course (SEC)")
    ec_course = models.CharField(max_length=250, null=True, blank=True, help_text="Elective Course (EC)")

    # Documents
    profile_image = models.ImageField(upload_to='pg_students/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='pg_students/signatures/', null=True, blank=True)

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Student Profile'
        verbose_name_plural = 'PG Student Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.registration_no})"

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()


class PGCourseStructure(models.Model):
    """
    Represents the course structure for a program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True, help_text="Course Name")
    department = models.ForeignKey(
        PGDepartment,
        on_delete=models.CASCADE,
        related_name='course_structures',
        null=True,
        blank=True
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type")
    code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    paper_code = models.CharField(max_length=20, null=True, blank=True, help_text="Paper Code")
    max_credit = models.IntegerField(null=True, blank=True, help_text="Course Credit")
    max_marks = models.IntegerField(null=True, blank=True, help_text="Course Marks")

    min_mark = models.IntegerField(null=True, blank=True, help_text="Pass Mark")
    min_credit = models.IntegerField(null=True, blank=True, help_text="Min Credit")

    description = models.TextField(null=True, blank=True, help_text="Course Description")
    label = models.CharField(max_length=100, null=True, blank=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
   
    semester = models.CharField(max_length=20, null=True, blank=True, help_text="Semester")
    batch = models.ForeignKey(
        PGBatch,
        on_delete=models.CASCADE,
        related_name='course_structures',
        null=True,
        blank=True
    )
    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Course Structure'
        verbose_name_plural = 'PG Course Structures'

    def __str__(self):
        return f"{self.department.name} - {self.course_type}"


class PGStudentCourseAssessment(models.Model):
    """
    Semester-wise assessment + marks for a student course
    using flexible labels (CIA-Theory, ESE-Practical, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Name")
    student = models.ForeignKey(
        'pg.PGStudentProfile',
        on_delete=models.CASCADE,
        related_name='course_assessments',
        help_text="Student"
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type")
    code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    paper_code = models.CharField(max_length=20, null=True, blank=True, help_text="Paper Code")
    semester = models.CharField(max_length=20, null=True, blank=True, help_text="Semester")

    max_credit = models.IntegerField(null=True, blank=True, help_text="Course Credit")
    max_marks = models.IntegerField(null=True, blank=True, help_text="Course Marks")

    min_mark = models.IntegerField(null=True, blank=True, help_text="Min Mark")
    min_credit = models.IntegerField(null=True, blank=True, help_text="Min Credit")

    description = models.TextField(null=True, blank=True, help_text="Course Description")
    label = models.CharField(max_length=100, null=True, blank=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")

    marks_obtained = models.IntegerField(null=True, blank=True, help_text="Marks Obtained")
    credit_obtained = models.IntegerField(null=True, blank=True, help_text="Credit Obtained")

    grade = models.CharField(max_length=10, null=True, blank=True, help_text="Grade")
    numeric_grade = models.IntegerField(null=True, blank=True, help_text="Numeric Grade")

    is_absent = models.BooleanField(default=False, help_text="Is Absent")
    exam_type = models.CharField(max_length=10, null=True, blank=True, help_text="Type Regular/Back")

    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    exam_result = models.CharField(max_length=10, null=True, blank=True, help_text="Status pass/fail/promoted")
    batch = models.ForeignKey(
        PGBatch,
        on_delete=models.CASCADE,
        related_name='pg_student_assessments',
        null=True,
        blank=True
    )

    department = models.ForeignKey(
        PGDepartment,
        on_delete=models.CASCADE,
        related_name='pg_student_assessments',
        null=True,
        blank=True
    )

    degree = models.CharField(max_length=20, null=True, blank=True)
    attendance = models.CharField(max_length=10, null=True, blank=True, help_text="Attendance")
    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")
    
    class Meta:
        verbose_name = 'PG Student Course Assessment'
        verbose_name_plural = 'PG Student Course Assessments'
        ordering = ['-created_at']
        unique_together = ('student', 'course_type', 'semester', 'label', 'exam_type')
        
    def __str__(self):
        return f"{self.student} | Sem {self.semester} | {self.label}"


class PGSemesterRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'pg.PGStudentProfile',
        on_delete=models.CASCADE,
        related_name='semester_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True, help_text="Start Date")
    end_date = models.DateTimeField(null=True, blank=True, help_text="End Date")
    is_open = models.BooleanField(default=False, help_text="Is Open")
    sem = models.IntegerField(null=True, blank=True, help_text="Semester")
    status = models.CharField(max_length=10, null=True, blank=True, help_text="Status open/closed")
    exam_eligible = models.BooleanField(default=False, help_text="Eligible for Exam")
    remarks = models.TextField(null=True, blank=True, help_text="Remarks")
    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")

    class Meta:
        verbose_name = 'PG Semester Registration'
        verbose_name_plural = 'PG Semester Registrations'

    def __str__(self):
        return f"{self.student}"


class PGExamRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'pg.PGStudentProfile',
        on_delete=models.CASCADE,
        related_name='exam_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True, help_text="Start Date")
    end_date = models.DateTimeField(null=True, blank=True, help_text="End Date")
    is_open = models.BooleanField(default=False, help_text="Is Open")
    fees = models.IntegerField(null=True, blank=True, help_text="Fees")
    sem = models.IntegerField(null=True, blank=True, help_text="Semester")
    status = models.CharField(max_length=10, null=True, blank=True, help_text="Status")
    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")

    class Meta:
        verbose_name = 'PG Exam Registration'
        verbose_name_plural = 'PG Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student}"