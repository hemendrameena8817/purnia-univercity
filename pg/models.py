import uuid
from django.db import models
from pup_umis_backend.storage_backends import DocumentStorage, MediaStorage
from pup_umis_backend.upload_paths import unique_file_path

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
        related_name='departments',
        null=True,
        blank=True
    )

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Department'
        verbose_name_plural = 'PG Departments'

    def __str__(self):
        if self.faculty:
            return f"{self.name} ({self.faculty.short_name or self.faculty.name})"
        return str(self.name)


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
    enrollment_date = models.DateField(null=True, blank=True)

    roll_no = models.CharField(max_length=50, null=True, blank=True)
    batch = models.CharField(max_length=50, null=True, blank=True)
    
    # Personal Information
    religion = models.CharField(max_length=50, null=True, blank=True)
    nationality = models.CharField(max_length=50, null=True, blank=True)
    medium_of_student = models.CharField(max_length=50, null=True, blank=True)
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
    profile_image = models.ImageField(storage=MediaStorage(), upload_to=unique_file_path('pg_students/profiles/'), null=True, blank=True)
    signature = models.ImageField(storage=MediaStorage(), upload_to=unique_file_path('pg_students/signatures/'), null=True, blank=True)

    is_active = models.BooleanField(default=True)
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
    course_name = models.CharField(max_length=500, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Short Name (e.g., 'IM' for 'Introductory Microeconomics').")
    department = models.ForeignKey(
        PGDepartment,
        on_delete=models.CASCADE,
        related_name='course_structures',
        null=True,
        blank=True
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type")
    code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    course_code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    paper_code = models.CharField(max_length=20, null=True, blank=True, help_text="Paper Code")
    max_credit = models.IntegerField(null=True, blank=True, help_text="Course Credit")
    effective_credit = models.IntegerField(null=True, blank=True, help_text="Effective Credit")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course Marks")

    min_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Pass Mark")

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
        dept_name = self.department.name if self.department else "No Department"
        return f"{dept_name} - {self.course_type or 'No Type'}"


class PGStudentCourseAssessment(models.Model):
    """
    Semester-wise assessment + marks for a student course
    using flexible labels (CIA-Theory, ESE-Practical, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Short Name (e.g., 'IM' for 'Introductory Microeconomics').")
    student = models.ForeignKey(
        'pg.PGStudentProfile',
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
        PGDepartment,
        on_delete=models.CASCADE,
        related_name='pg_student_assessments',
        null=True,
        blank=True
    )
    degree = models.CharField(max_length=20, null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Session")
    batch = models.ForeignKey(
        PGBatch,
        on_delete=models.CASCADE,
        related_name='pg_student_assessments',
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
    sem_result = models.CharField(max_length=50, null=True, blank=True, help_text="Semester Result eg: pass/fail/promoted")
    next_sem_status = models.CharField(max_length=10, null=True, blank=True, help_text="Next Semester Status eg: eligible/not eligible")
    sem_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Semester GRACE MARKS OBTAINED")
    ####semester####

    #####temp#####
    temp_total_gp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total GRADE POINT")
    #####temp#####
    is_cia_fill = models.BooleanField(default=False, help_text="Is CIA Fill")
    is_ese_fill = models.BooleanField(default=False, help_text="Is ESE Fill")
    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")
    
    class Meta:
        verbose_name = 'PG Student Course Assessment'
        verbose_name_plural = 'PG Student Course Assessments'
        ordering = ['-created_at']
        # unique_together = ('student', 'course_type', 'semester', 'label', 'exam_type')
        
        # Composite indexes for common query patterns
        indexes = [
            # Student-based queries
            models.Index(fields=['student', 'semester'], name='pg_idx_student_sem'),
            models.Index(fields=['student', 'semester', 'label'], name='pg_idx_stud_sem_lbl'),
            
            # Department-based queries (for faculty reports via department FK)
            models.Index(fields=['department', 'semester'], name='pg_idx_dept_sem'),
            models.Index(fields=['department', 'semester', 'label'], name='pg_idx_dept_sem_lbl'),
            
            # Batch-based queries
            models.Index(fields=['batch', 'semester'], name='pg_idx_batch_sem'),
            
            # Course-based queries
            models.Index(fields=['paper_code', 'semester'], name='pg_idx_paper_sem'),
            models.Index(fields=['semester', 'label'], name='pg_idx_sem_label'),
        ]


        
    # def save(self, *args, **kwargs):
    #     """
    #     Override save to validate and calculate pass/fail status
    #     """
    #     # Step 1: Validate ind_marks_obtained doesn't exceed ind_max_marks
    #     if self.ind_marks_obtained is not None and self.ind_max_marks is not None:
    #         if self.ind_marks_obtained > self.ind_max_marks:
    #             raise ValueError(
    #                 f"Individual marks obtained ({self.ind_marks_obtained}) "
    #                 f"cannot exceed maximum marks ({self.ind_max_marks})"
    #             )
        
    #     # Step 2: Calculate ind_is_pass based on ind_pass_marks
    #     if self.ind_marks_obtained is not None and self.ind_pass_marks is not None:
    #         # If absent, mark as fail
    #         if self.ind_is_absent:
    #             self.ind_is_pass = False
    #         else:
    #             # Pass if marks obtained >= pass marks
    #             self.ind_is_pass = self.ind_marks_obtained >= self.ind_pass_marks
    #     elif self.ind_is_absent:
    #         # If absent but no marks data, still mark as fail
    #         self.ind_is_pass = False
        
    #     # Call parent save
    #     super().save(*args, **kwargs)
        
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


##for center mapping 
class PGExam(models.Model):
    """
    Represents the overall Examination Event (e.g. BTech 4th Sem June 2024).
    Contains the global schedule shared by all centers.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)            # PG 3rd Semester Examination
    year = models.PositiveIntegerField(null=True, blank=True)         # 3
    session = models.CharField(max_length=20, null=True, blank=True)        # 2022-24
    batch = models.CharField(max_length=20, null=True, blank=True)  
    exam_month_year = models.CharField(max_length=20, null=True, blank=True) # June 2024
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unnamed Exam'} ({self.session or 'No Session'})"

class PGExamCenterMapping(models.Model):
    """
    Center Fixation: Maps an Exam + Center to one or more Colleges.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exams = models.ManyToManyField(
        PGExam,
        related_name='pg_center_mappings'
    )
    center = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='pg_as_center_mappings'
    )
    # The colleges whose students will go to this center for this specific exam
    attached_colleges = models.ManyToManyField(
        'colleges.College',
        related_name='pg_exam_centers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Exam Center Mapping'
        verbose_name_plural = 'PG Exam Center Mappings'

    def __str__(self):
        exam_count = self.exams.count()
        return f"{self.center.name} ({exam_count} Exams)"

class PGGroup(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    department = models.ManyToManyField('PGDepartment',related_name='pg_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class PGExamSchedule(models.Model):
    """
    Exam Routine/Datesheet for BTech.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        PGExam, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    # Changed from BTechSubject to BTechCourseStructure
    common_course_structure = models.ForeignKey(
        'PGCommonCourseStructure', 
        on_delete=models.CASCADE, 
        related_name='pg_exam_schedules',
        null=True,
        blank=True
    )
    group = models.ForeignKey(
        PGGroup,
        on_delete=models.CASCADE,
        related_name='pg_exam_schedules',
        null=True,
        blank=True
    )
    exam_date = models.DateField(null=True, blank=True)
    exam_time = models.CharField(max_length=100, null=True, blank=True)
    sitting = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Exam Schedule'
        verbose_name_plural = 'PG Exam Schedules'
        # unique_together = ('exam', 'course_structure')
        ordering = ['exam_date', 'exam_time']

    def __str__(self):
        return f"{self.exam.name} - {self.common_course_structure.course_code if self.common_course_structure else 'N/A'} ({self.exam_date})"



EXAM_TYPE_CHOICES = (
    ('REGULAR', 'Regular'),
    ('BACK', 'Back'),
    ('IMPROVEMENT', 'Improvement'),
)
REGISTRATION_STATUS_CHOICES = (
    ('PENDING', 'Pending'),
    ('OPEN', 'Open'),
    ('REGISTERED', 'Registered'),
    ('CLOSED', 'Closed'),
)
class PGExamRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'pg.PGStudentProfile',
        on_delete=models.CASCADE,
        related_name='exam_registrations'
    )
    admission_receipt = models.FileField(storage=MediaStorage(), upload_to=unique_file_path('pg/admission_receipts/'), null=True, blank=True, help_text="Admission Receipt")
    start_date = models.DateTimeField(null=True, blank=True, help_text="Start Date")
    end_date = models.DateTimeField(null=True, blank=True, help_text="End Date")
    is_open = models.BooleanField(default=False, help_text="Is Open")
    fees = models.IntegerField(null=True, blank=True, help_text="Fees")
    sem = models.IntegerField(null=True, blank=True, help_text="Semester")
    status = models.CharField(max_length=15, choices=REGISTRATION_STATUS_CHOICES, default='PENDING', help_text="Registration Status")
    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='REGULAR', help_text="Exam Type",null=True,blank=True)
    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")

    class Meta:
        verbose_name = 'PG Exam Registration'
        verbose_name_plural = 'PG Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student} - {self.sem} ({self.session}) [{self.exam_type}]"


class PGCommonCourseStructure(models.Model):
    """
    Represents the common course structure for a semester (CBCS).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    departments = models.ManyToManyField('PGDepartment', blank=True, related_name='common_courses', help_text="Departments offering this common course")
    semester = models.CharField(max_length=50, help_text="e.g., Semester-I")
    course_name = models.CharField(max_length=255, help_text="e.g., CC ",blank=True,null=True)
    course_code = models.CharField(max_length=20, help_text="e.g., CC-1", null=True,blank=True)
    course_type = models.CharField(max_length=50, help_text="e.g., CC",null=True,blank=True)
    # ltp = models.CharField(max_length=20, null=True, blank=True, help_text="L-T-P e.g., 6-1-0")
    credit = models.PositiveIntegerField(default=0)
    marks = models.PositiveIntegerField(default=100)
    old_code = models.CharField(max_length=20, null=True, blank=True, help_text="eg: cc-")
    cia_marks = models.PositiveIntegerField(null=True, blank=True)
    ese_marks = models.PositiveIntegerField(null=True, blank=True)
    new_code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PGCommon Course Structure' 
        verbose_name_plural = 'PGCommon Course Structures'
        ordering = ['semester', 'course_name']

    def __str__(self):
        return f"{self.semester} - {self.course_code}"


SEMESTER_RESULT_CHOICES = [
    ('PASS', 'Pass'),
    ('FAIL', 'Fail'),
    ('PROMOTED', 'Promoted'),
    ('ABSENT', 'Absent'),
    ('DISQUALIFIED', 'Disqualified'),
    ('PARTIALDISQUALIFIED', 'Partial Disqualified'),
    ('QUALIFIED', 'Qualified'),
    ('PENDING', 'Pending'),
]


class PGExamResult(models.Model):
    """
    Stores semester exam results for PG students
    Combines CIA and ESE results to determine final semester outcome
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    student = models.ForeignKey(
        'PGStudentProfile',
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
        max_length=50,
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
        verbose_name = 'PG Exam Result'
        verbose_name_plural = 'PG Exam Results'
        unique_together = ('student', 'semester', 'session')
        indexes = [
            models.Index(fields=['student', 'semester']),
            models.Index(fields=['semester', 'session']),
            models.Index(fields=['semester_result']),
        ]

    def __str__(self):
        return f"{self.student} - Sem {self.semester} ({self.session})"


class PGExamRegistrationPayment(models.Model):
    """
    Tracks CC Avenue payments for PG exam registrations.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('ABORTED', 'Aborted'),
    ]

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    registration = models.ForeignKey(
        PGExamRegistration,
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
    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PG Exam Registration Payment'
        verbose_name_plural = 'PG Exam Registration Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_id} - {self.registration.student} - {self.payment_status}"

