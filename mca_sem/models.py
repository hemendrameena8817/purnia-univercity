from django.db import models
import uuid
from django.conf import settings
from .choices import (
    SEMESTER_RESULT_CHOICES,
    STUDENT_STATUS_CHOICES,
    GENDER_CHOICES,
    EXAM_TYPE_CHOICES,
    ASSESSMENT_LABEL_CHOICES,
    PROMOTION_STATUS_CHOICES,
)

# 1. Master Structure Models
class MCACourse(models.Model):
    """
    Represents a specific MCA Course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)  
    duration_years = models.PositiveIntegerField(default=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Course"

class MCASession(models.Model):
    """
    Academic Session for MCA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=20, null=True, blank=True)  # 2021-23
    start_year = models.PositiveIntegerField(null=True, blank=True)
    end_year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Session"

class MCABatch(models.Model):
    """
    Represents a batch of students in an MCA program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, help_text='Batch name e.g., 2022-2024')
    session = models.ForeignKey(
        MCASession,
        on_delete=models.PROTECT,
        related_name='batches',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Batch'
        verbose_name_plural = 'MCA Batches'
        ordering = ['name']

    def __str__(self):
        return self.name

# 2. Student & Course Master Models
class MCAStudentProfile(models.Model):
    """
    MCA Student profile linked to a UserAccount.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='mca_student_profile',
        null=True,
        blank=True
    )
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    hindi_name = models.CharField(max_length=250, null=True, blank=True)
    registration_no = models.CharField(max_length=50, unique=True, db_index=True, null=True, blank=True)
    roll_no = models.CharField(max_length=50, null=True, blank=True)
    
    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)
    
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    mobile_no = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    aadhar_no = models.CharField(max_length=12, null=True, blank=True)
    
    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='mca_students',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        MCACourse,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    batch = models.ForeignKey(
        MCABatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    current_semester = models.PositiveIntegerField(null=True, blank=True)
    session_str = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STUDENT_STATUS_CHOICES, default='REGULAR')

    profile_image = models.ImageField(upload_to='mca_students/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='mca_students/signatures/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Student Profile'
        verbose_name_plural = 'MCA Student Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.registration_no})"

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

class MCACourseStructure(models.Model):
    """
    Represents the course structure configuration for an MCA program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course_name = models.CharField(max_length=500, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True)
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type")
    course_code = models.CharField(max_length=50, null=True, blank=True, help_text="Course Code")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course Marks")
    min_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Pass Mark")
    
    description = models.TextField(null=True, blank=True, help_text="Course Description")
    label = models.CharField(max_length=100, null=True, blank=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
    
    semester = models.CharField(max_length=20, null=True, blank=True, help_text="Semester")
    
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Course Structure'
        verbose_name_plural = 'MCA Course Structures'

    def __str__(self):
        return f"{self.course_name} ({self.course_code}) - {self.semester}"

class MCACommonCourseStructure(models.Model):
    """
    Common structure template for MCA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    semester = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    course_type = models.CharField(max_length=50)
    ltp = models.CharField(max_length=20, null=True, blank=True)
    marks = models.PositiveIntegerField(default=100)
    code  = models.CharField(max_length=20, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Common Course Structure'
        verbose_name_plural = 'MCA Common Course Structures'
        ordering = ['semester', 'course_name']

    def __str__(self):
        return f"{self.semester} - {self.course_name}"

class MCAExam(models.Model):
    """
    Represents the overall Examination Event (e.g. MCA 4th Sem June 2024).
    Contains the global schedule shared by all centers.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)            # MCA 4th Semester Examination
    semester = models.PositiveIntegerField(null=True, blank=True)         # 4
    session = models.CharField(max_length=20, null=True, blank=True)        # 2022-24
    exam_month_year = models.CharField(max_length=20, null=True, blank=True) # June 2024
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unnamed Exam'} ({self.session or 'No Session'})"

class MCAExamCenterMapping(models.Model):
    """
    Center Fixation: Maps an Exam + Center to one or more Colleges.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        MCAExam,
        on_delete=models.CASCADE,
        related_name='center_mappings'
    )
    center = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='mca_as_center_mappings'
    )
    # The colleges whose students will go to this center for this specific exam
    attached_colleges = models.ManyToManyField(
        'colleges.College',
        related_name='mca_exam_centers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Exam Center Mapping'
        verbose_name_plural = 'MCA Exam Center Mappings'
        unique_together = ('exam', 'center')

    def __str__(self):
        return f"{self.exam.name} @ {self.center.name}"


class MCAExamSchedule(models.Model):
    """
    Exam Routine/Datesheet for MCA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        MCAExam, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    # Changed from MCASubject to MCACourseStructure
    common_course_structure = models.ForeignKey(
        MCACommonCourseStructure, 
        on_delete=models.CASCADE, 
        related_name='exam_schedules',
        null=True,
        blank=True
    )
    exam_date = models.DateField(null=True, blank=True)
    exam_time = models.CharField(max_length=100, null=True, blank=True)
    sitting = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Exam Schedule'
        verbose_name_plural = 'MCA Exam Schedules'
        # unique_together = ('exam', 'course_structure')
        ordering = ['exam_date', 'exam_time']

    def __str__(self):
        return f"{self.exam.name} - {self.common_course_structure.code if self.common_course_structure else 'N/A'} ({self.exam_date})"

class MCASemesterRegistration(models.Model):
    """
    Semester Registration for MCA Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
        on_delete=models.CASCADE,
        related_name='semester_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=False)
    sem = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    exam_eligible = models.BooleanField(default=False)
    remarks = models.TextField(null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Semester Registration'
        verbose_name_plural = 'MCA Semester Registrations'

    def __str__(self):
        return f"{self.student}"

class MCAExamRegistration(models.Model):
    """
    Exam Registration for MCA Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=False)
    fees = models.IntegerField(null=True, blank=True)
    sem = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Exam Registration'
        verbose_name_plural = 'MCA Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student}"

# 4. Result & Assessment Models
class MCAStudentAssessment(models.Model):
    """
    Detailed marks per subject and assessment label for MCA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
        on_delete=models.CASCADE,
        related_name='course_assessments'
    )
    course_name = models.CharField(max_length=250, null=True, blank=True)
    course_type = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    course_code = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    semester = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    label = models.CharField(max_length=200, db_index=True, choices=ASSESSMENT_LABEL_CHOICES)
    session = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    batch = models.ForeignKey(
        MCABatch,
        on_delete=models.CASCADE,
        related_name='student_assessments',
        null=True,
        blank=True
    )
    college_code = models.CharField(max_length=200, null=True, blank=True)
    exam_type = models.CharField(max_length=200, choices=EXAM_TYPE_CHOICES, null=True, blank=True, db_index=True)
    attendance = models.CharField(max_length=200, null=True, blank=True)

    #### Marks ####
    ind_max_marks = models.IntegerField(null=True, blank=True)
    ind_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_is_absent = models.BooleanField(default=True, db_index=True)
    ind_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_is_pass = models.BooleanField(null=True, blank=True)

    #### Aggregated Marks ####
    comb_max_marks = models.IntegerField(null=True, blank=True)
    comb_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comb_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comb_numeric_grade = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comb_letter_grade = models.CharField(max_length=10, null=True, blank=True)
    comb_grade_point = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    #### Course Summary ####
    course_max_marks = models.IntegerField(null=True, blank=True)
    course_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    course_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    #### Semester Summary ####
    sem_result = models.CharField(max_length=20, null=True, blank=True, choices=SEMESTER_RESULT_CHOICES)
    next_sem_status = models.CharField(max_length=20, null=True, blank=True, choices=PROMOTION_STATUS_CHOICES)

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'MCA Student Assessment'
        verbose_name_plural = 'MCA Student Assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'semester'], name='idx_mca_stud_sem'),
            models.Index(fields=['batch', 'semester'], name='idx_mca_batch_sem'),
            models.Index(fields=['course_code', 'semester'], name='idx_mca_course_sem'),
        ]
        
    def save(self, *args, **kwargs):
        if self.ind_marks_obtained is not None and self.ind_max_marks is not None:
            if self.ind_marks_obtained > self.ind_max_marks:
                raise ValueError(f"Marks ({self.ind_marks_obtained}) > Max ({self.ind_max_marks})")
        if self.ind_marks_obtained is not None and self.ind_pass_marks is not None:
            self.ind_is_pass = self.ind_marks_obtained >= self.ind_pass_marks if not self.ind_is_absent else False
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.student} | {self.semester} | {self.label}"

class MCAExamResult(models.Model):
    """
    Final summary result for an MCA Semester.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_results'
    )
    semester = models.CharField(max_length=10, db_index=True)
    session = models.CharField(max_length=10, db_index=True)
    cia_pass = models.BooleanField(null=True, blank=True)
    ese_pass = models.BooleanField(null=True, blank=True)
    semester_result = models.CharField(
        max_length=20,
        db_index=True,
        choices=SEMESTER_RESULT_CHOICES
    )
    total_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    next_semester = models.PositiveIntegerField(null=True, blank=True)
    next_sem_status = models.CharField(max_length=15, null=True, blank=True, choices=PROMOTION_STATUS_CHOICES)
    is_legacy = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Exam Result'
        verbose_name_plural = 'MCA Exam Results'
        unique_together = ('student', 'semester', 'session')
        indexes = [
            models.Index(fields=['student', 'semester']),
            models.Index(fields=['semester_result']),
        ]

    def __str__(self):
        return f"{self.student} | Sem {self.semester} | {self.semester_result}"
