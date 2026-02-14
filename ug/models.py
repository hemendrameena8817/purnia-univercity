import uuid
from django.db import models

from .choices import (
    SEMESTER_RESULT_CHOICES,
    STUDENT_STATUS_CHOICES,
    GENDER_CHOICES,
    EXAM_TYPE_CHOICES,
    PROMOTION_STATUS_CHOICES,
    REGISTRATION_STATUS_CHOICES,
)
from pup_umis_backend.storage_backends import DocumentStorage, MediaStorage
from pup_umis_backend.upload_paths import unique_file_path

class UGFaculty(models.Model):
    """
    Represents a UG Faculty/School division.
    Examples: Faculty of Science, Faculty of Humanities, Faculty of Commerce.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    university = models.ForeignKey(
        'university.University',
        on_delete=models.CASCADE,
        related_name='ug_faculties'
    )
    departments = models.ManyToManyField(
        'ug.UGDepartment',
        related_name='faculties',
        null=True,
        blank=True
    )
    is_publish = models.BooleanField(default=False)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Faculty'
        verbose_name_plural = 'UG Faculties'
        ordering = ['name']

    def __str__(self):
        return self.name


class UGDepartment(models.Model):
    """
    Represents a UG Department within a Faculty.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, null=True, blank=True, help_text='e.g., History, Physics, Economics')
    code = models.CharField(max_length=50, null=True, blank=True)
    head_of_department = models.CharField(max_length=255, blank=True, null=True)

    # faculty = models.ForeignKey(
    #     UGFaculty,
    #     on_delete=models.CASCADE,
    #     related_name='departments'
    # )
    is_publish = models.BooleanField(default=False)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Department'
        verbose_name_plural = 'UG Departments'

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name


class UGDegree(models.Model):
    """
    Represents a UG Degree type (e.g., Bachelor of Arts, Bachelor of Science).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, unique=True, help_text='e.g., B.A., B.Sc., B.Com., BCA')
    short_name = models.CharField(max_length=50, null=True, blank=True, help_text='e.g., BA, BSc')
    total_semesters = models.PositiveIntegerField(default=8)
    total_years = models.PositiveIntegerField(default=4)

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Degree'
        verbose_name_plural = 'UG Degrees'
        ordering = ['name']

    def __str__(self):
        return self.name


class UGProgram(models.Model):
    """
    Represents a UG Academic Program (e.g., B.A. History, B.Sc. Physics).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    name = models.CharField(max_length=255, help_text='Program name e.g., B.A. (Hons) History')
    short_name = models.CharField(max_length=50, null=True, blank=True, help_text='e.g., BA History')

    degree = models.ForeignKey(
        UGDegree,
        on_delete=models.CASCADE,
        related_name='programs'
    )

    department = models.ForeignKey(
        UGDepartment,
        on_delete=models.CASCADE,
        related_name='programs',
        null=True,
        blank=True
    )

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Program'
        verbose_name_plural = 'UG Programs'

    def __str__(self):
        return f"{self.name}"

    @property
    def total_semesters(self):
        return self.degree.total_semesters

    @property
    def total_years(self):
        return self.degree.total_years


class UGBatch(models.Model):
    """
    Represents a batch of students in a program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, help_text='Batch name e.g., 2022-2026')
    program = models.ForeignKey(
        UGProgram,
        on_delete=models.CASCADE,
        related_name='batches',
        null=True,
        blank=True
    )
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Batch'
        verbose_name_plural = 'UG Batches'
        ordering = ['name']

    def __str__(self):
        return self.name

class UGStudentProfile(models.Model):
    """
    UG Student profile linked to a UserAccount.
    Contains undergrad-specific course selections: Major, Minor, MDC.
    """

    
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Link to UserAccount
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='ug_student_profile'
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
    enrollment_date = models.DateField(null=True, blank=True)
    roll_no = models.CharField(max_length=50, null=True, blank=True)
    batch = models.ForeignKey(
        UGBatch,
        on_delete=models.SET_NULL,
        related_name='students',
        null=True,
        blank=True,
        help_text="Student Batch"
    )

    # Family Information
    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)

    # Academic Information
    current_semester = models.PositiveIntegerField(null=True, blank=True)
    session = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STUDENT_STATUS_CHOICES, default='Active')

    # Relationships
    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='ug_students',
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        UGDepartment,
        on_delete=models.CASCADE,
        related_name='students',
        null=True,
        blank=True
    )
    program = models.ForeignKey(
        UGProgram,
        on_delete=models.CASCADE,
        related_name='students',
        null=True,
        blank=True
    )
    degree = models.ForeignKey(
        UGDegree,
        on_delete=models.CASCADE,
        related_name='students',
        null=True,
        blank=True
    )

    # UG-specific course selections (CBCS)
    major_course = models.ForeignKey(UGDepartment, on_delete=models.CASCADE, related_name='major_courses', null=True, blank=True)
    minor_course = models.ForeignKey(UGDepartment, on_delete=models.CASCADE, related_name='minor_courses', null=True, blank=True)
    mdc_course = models.ForeignKey(UGDepartment, on_delete=models.CASCADE, related_name='mdc_courses', null=True, blank=True)
    # major_course = models.CharField(max_length=250, null=True, blank=True, help_text="Major Core Course (MJC)")
    # minor_course = models.CharField(max_length=250, null=True, blank=True, help_text="Minor Core Course (MIC)")
    # mdc_course = models.CharField(max_length=250, null=True, blank=True, help_text="Multi-Disciplinary Course (MDC)")

    # Documents
    profile_image = models.ImageField(storage=DocumentStorage(), upload_to=unique_file_path('ug_students/profiles/'), null=True, blank=True)
    signature = models.ImageField(storage=DocumentStorage(), upload_to=unique_file_path('ug_students/signatures/'), null=True, blank=True)
    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Student Profile'
        verbose_name_plural = 'UG Student Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.registration_no})"

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

class CourseStructure(models.Model):
    """
    Represents the course structure for a program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course_name = models.CharField(max_length=500, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Short Name (e.g., 'IM' for 'Introductory Microeconomics').")
    department = models.ForeignKey(
        UGDepartment,
        on_delete=models.CASCADE,
        related_name='course_structures',
        null=True,
        blank=True
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type")
    course_code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    paper_code = models.CharField(max_length=20, null=True, blank=True, help_text="Paper Code")
    max_credit = models.IntegerField(null=True, blank=True, help_text="Course Credit")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course Marks")

    min_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Pass Mark")

    description = models.TextField(null=True, blank=True, help_text="Course Description")
    label = models.CharField(max_length=100, null=True, blank=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
   
    semester = models.CharField(max_length=20, null=True, blank=True, help_text="Semester")
    batch = models.ForeignKey(
        UGBatch,
        on_delete=models.CASCADE,
        related_name='course_structures',
        null=True,
        blank=True
    )
    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Course Structure'
        verbose_name_plural = 'Course Structures'

    def __str__(self):
        return f"{self.course_type}"


class StudentCourseAssessment(models.Model):
    """
    Semester-wise assessment + marks for a student course
    using flexible labels (CIA-Theory, ESE-Practical, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Short Name (e.g., 'IM' for 'Introductory Microeconomics').")
    student = models.ForeignKey(
        'ug.UGStudentProfile',
        on_delete=models.CASCADE,
        related_name='course_assessments',
        help_text="Student"
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Course Type")
    course_code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    paper_code = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Paper Code")

    semester = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Semester")
    label = models.CharField(max_length=100, db_index=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
    department = models.ForeignKey(
        UGDepartment,
        on_delete=models.CASCADE,
        related_name='student_assessments',
        null=True,
        blank=True
    )
    degree = models.CharField(max_length=20, null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Session")
    batch = models.ForeignKey(
        UGBatch,
        on_delete=models.CASCADE,
        related_name='student_assessments',
        null=True,
        blank=True
    )
    college_code = models.CharField(max_length=10, null=True, blank=True, help_text="College Code")
    exam_type = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Type Regular/Back")

    ###attendance###
    attendance = models.CharField(max_length=10, null=True, blank=True, help_text="Attendance")
    ###attendance###

    ####Individual####
    ind_max_marks = models.IntegerField(null=True, blank=True, help_text="Individual MAX MARKS")
    ind_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual PASS MARKS")
    ind_is_absent = models.BooleanField(default=True, db_index=True, help_text="Is Absent")
    ind_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual MARKS OBTAINED")
    ind_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual GRACE MARKS OBTAINED")
    ind_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual FINAL MARKS OBTAINED")
    ind_is_pass = models.BooleanField(null=True, blank=True, help_text="Is Pass")
    ####Individual####

    ####combined####
    comb_max_marks = models.IntegerField(null=True, blank=True, help_text="Total MAX MARKS")
    comb_max_credits = models.IntegerField(null=True, blank=True, help_text="Total MAX CREDIT")
    comb_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total PASS MARKS")
    comb_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total MARKS OBTAINED")
    comb_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total GRACE MARKS OBTAINED")
    comb_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total FINAL MARKS OBTAINED")
    comb_credit_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total CREDIT OBTAINED")
    comb_numeric_grade = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total NUMERIC GRADE")
    comb_letter_grade = models.CharField(max_length=10, null=True, blank=True, help_text="Total LETTER GRADE")
    comb_grade_point = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total GRADE POINT")
    ####combined####

    ####course####
    course_max_marks = models.IntegerField(null=True, blank=True, help_text="Course MAX MARKS")
    course_max_credits = models.IntegerField(null=True, blank=True, help_text="Course MAX CREDIT")
    course_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course PASS MARKS")
    course_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course MARKS OBTAINED")
    course_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course GRACE MARKS")
    course_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course FINAL MARKS OBTAINED")
    course_credit_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course CREDIT OBTAINED")
    course_grade_point = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course GRADE POINT")
    ####course####
 
    ####semester####
    sem_max_credit = models.IntegerField(null=True, blank=True, help_text="Semester MAX CREDIT")
    sem_credit_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Semester CREDIT OBTAINED")
    sgpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Semester GRADE POINT")
    sem_result = models.CharField(max_length=10, null=True, blank=True, help_text="Semester Result eg: pass/fail/promoted")
    next_sem_status = models.CharField(max_length=10, null=True, blank=True, help_text="Next Semester Status eg: eligible/not eligible")
    sem_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Semester GRACE MARKS OBTAINED")
    ####semester####

    #####temp#####
    temp_total_gp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total GRADE POINT")
    #####temp#####

    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")
    
    class Meta:
        verbose_name = 'Student Course Assessment'
        verbose_name_plural = 'Student Course Assessments'
        ordering = ['-created_at']
        # unique_together = ('student', 'code', 'semester', 'label', 'exam_type', 'session')
        
        # Composite indexes for common query patterns
        indexes = [
            # Student-based queries
            models.Index(fields=['student', 'semester'], name='idx_student_sem'),
            models.Index(fields=['student', 'semester', 'label'], name='idx_stud_sem_label'),
            
            # Department-based queries (for faculty reports via department FK)
            models.Index(fields=['department', 'semester'], name='idx_dept_sem'),
            models.Index(fields=['department', 'semester', 'label'], name='idx_dept_sem_label'),
            
            # Batch-based queries
            models.Index(fields=['batch', 'semester'], name='idx_batch_sem'),
            
            # Course-based queries
            models.Index(fields=['paper_code', 'semester'], name='idx_paper_sem'),
            models.Index(fields=['semester', 'label'], name='idx_sem_label'),
            
            # CRITICAL: Registration duplicate checking (30k students optimization)
            # Includes exam_type to differentiate regular vs back exams
            models.Index(fields=['student', 'semester', 'session', 'paper_code', 'label', 'exam_type'], 
                        name='idx_reg_dup_check'),
        ]


        
    def save(self, *args, **kwargs):
        """
        Override save to validate and calculate pass/fail status
        """
        # Step 1: Validate ind_marks_obtained doesn't exceed ind_max_marks
        if self.ind_marks_obtained is not None and self.ind_max_marks is not None:
            if self.ind_marks_obtained > self.ind_max_marks:
                raise ValueError(
                    f"Individual marks obtained ({self.ind_marks_obtained}) "
                    f"cannot exceed maximum marks ({self.ind_max_marks})"
                )
        
        # Step 2: Calculate ind_is_pass based on ind_pass_marks
        if self.ind_marks_obtained is not None and self.ind_pass_marks is not None:
            # If absent, mark as fail
            if self.ind_is_absent:
                self.ind_is_pass = False
            else:
                # Pass if marks obtained >= pass marks
                self.ind_is_pass = self.ind_marks_obtained >= self.ind_pass_marks
        elif self.ind_is_absent:
            # If absent but no marks data, still mark as fail
            self.ind_is_pass = False
        
        # Call parent save
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.student} | Sem {self.semester} | {self.label}"


class UGExamResult(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    student = models.ForeignKey(
        'ug.UGStudentProfile',
        on_delete=models.CASCADE,
        related_name='exam_results'
    )

    semester = models.CharField(max_length=10, db_index=True)
    session = models.CharField(max_length=10, db_index=True)

    # CIA / ESE STATUS
    cia_pass = models.BooleanField(null=True, blank=True)
    ese_pass = models.BooleanField(null=True, blank=True)

    # FINAL SEM RESULT
    semester_result = models.CharField(
        max_length=20,
        db_index=True,
        choices=SEMESTER_RESULT_CHOICES,
        help_text="Semester result status (PASS / FAIL / PROMOTED / ABSENT / DISQUALIFIED etc.)"
    )

    # CREDIT & SGPA
    semester_max_credit = models.PositiveIntegerField()
    semester_credit_earned = models.PositiveIntegerField()

    sgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    # PROMOTION
    next_semester = models.PositiveIntegerField(null=True, blank=True)
    next_sem_status = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        help_text="Next semester status (ELIGIBLE / NOT_ELIGIBLE / etc.)"
    )

    # META
    is_legacy = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Exam Result'
        verbose_name_plural = 'Exam Results'
        unique_together = ('student', 'semester', 'session')
        indexes = [
            models.Index(fields=['student', 'semester']),
            models.Index(fields=['semester', 'session']),
            models.Index(fields=['semester_result']),
        ]


class SemesterRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'ug.UGStudentProfile',
        on_delete=models.CASCADE,
        related_name='semester_registrations'
    )
    batch = models.ForeignKey(
        'ug.UGBatch',
        on_delete=models.SET_NULL,
        related_name='semester_registrations',
        null=True,
        blank=True,
        help_text="Student Batch"
    )
    start_date = models.DateTimeField(null=True, blank=True, help_text="Start Date")
    end_date = models.DateTimeField(null=True, blank=True, help_text="End Date")
    is_open = models.BooleanField(default=False, help_text="Is Open")
    sem = models.IntegerField(null=True, blank=True, help_text="Semester")
    status = models.CharField(max_length=15, choices=REGISTRATION_STATUS_CHOICES, default='PENDING', help_text="Registration Status")
    exam_eligible = models.BooleanField(default=False, help_text="Eligible for Exam")
    remarks = models.TextField(null=True, blank=True, help_text="Remarks")
    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")

    class Meta:
        verbose_name = 'Semester Registration'
        verbose_name_plural = 'Semester Registrations'
        
        indexes = [
            models.Index(fields=['student', 'sem', 'status'], 
                        name='idx_eligibility_check_v2'),
            models.Index(fields=['batch', 'sem', 'status'],
                        name='idx_batch_sem_status'),
        ]


    def __str__(self):
        return f"{self.student}"


class ExamRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'ug.UGStudentProfile',
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
        verbose_name = 'Exam Registration'
        verbose_name_plural = 'Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student}"

class CommonCourseStructure(models.Model):
    """
    Represents the common course structure for a semester (CBCS).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    semester = models.CharField(max_length=50, help_text="e.g., Semester-I")
    course_name = models.CharField(max_length=255, help_text="e.g., Major Course 1")
    course_type = models.CharField(max_length=50, help_text="e.g., MJC-1")
    ltp = models.CharField(max_length=20, null=True, blank=True, help_text="L-T-P e.g., 6-1-0")
    credit = models.PositiveIntegerField(default=0)
    marks = models.PositiveIntegerField(default=100)
    code  = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Common Course Structure'
        verbose_name_plural = 'Common Course Structures'
        ordering = ['semester', 'course_name']

    def __str__(self):
        return f"{self.semester} - {self.course_type} ({self.course_name})"
