from django.db import models
import uuid
from django.conf import settings
from .choices import (
    YEAR_RESULT_CHOICES,
    STUDENT_STATUS_CHOICES,
    GENDER_CHOICES,
    EXAM_TYPE_CHOICES,
    ASSESSMENT_LABEL_CHOICES,
    PROMOTION_STATUS_CHOICES,
    PAPER_TYPE_CHOICES
)

# 1. Master Structure Models

class BBACourse(models.Model):
    """
    Represents a specific BBA Course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True) 
    course_code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    discipline_code = models.CharField(max_length=255, null=True, blank=True)
    duration_years = models.PositiveIntegerField(default=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed BBA Course"

class BBASession(models.Model):
    """
    Academic Session for BBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=20, null=True, blank=True)  # 2021-24
    start_year = models.PositiveIntegerField(null=True, blank=True)
    end_year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Session"

class BBABatch(models.Model):
    """
    Represents a batch of students in a BBA program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text='Batch name e.g., 2022-2025')
    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Batch'
        verbose_name_plural = 'BBA Batches'
        ordering = ['name']

    def __str__(self):
        return self.name

# 2. Student & Course Master Models
class BBAStudentProfile(models.Model):
    """
    BBA Student profile linked to a UserAccount.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='bba_student_profile',
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
        related_name='bba_students',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        BBACourse,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    batch = models.ForeignKey(
        BBABatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    current_year = models.PositiveIntegerField(null=True, blank=True) # 1, 2, 3
    session_str = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STUDENT_STATUS_CHOICES, default='Regular')

    profile_image = models.ImageField(upload_to='bba_students/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='bba_students/signatures/', null=True, blank=True)

    part_1_marks = models.CharField(max_length=50, null=True, blank=True)
    part_2_marks = models.CharField(max_length=50, null=True, blank=True)
    part_3_marks = models.CharField(max_length=50, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Student Profile'
        verbose_name_plural = 'BBA Student Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.registration_no}) ({self.roll_no})"

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

class BBACourseStructure(models.Model):
    """
    Represents the course structure configuration for BBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course = models.ForeignKey(
        BBACourse,
        on_delete=models.CASCADE,
        related_name='course_structures',
        null=True,
        blank=True
    )
    course_name = models.CharField(max_length=500, null=True, blank=True, help_text="Subject Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True)
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type") 
    course_code = models.CharField(max_length=50, null=True, blank=True, help_text="Course Code")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    description = models.TextField(null=True, blank=True)
    label = models.CharField(max_length=100, null=True, blank=True, choices=ASSESSMENT_LABEL_CHOICES)
    
    year = models.CharField(max_length=20, null=True, blank=True, help_text="Year/Part")
    
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Course Structure'
        verbose_name_plural = 'BBA Course Structures'

    def __str__(self):
        return f"{self.course_name} ({self.course_code}) - {self.year}"

class BBACommonCourseStructure(models.Model):
    """
    Common structure template for BBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course = models.ForeignKey(
        BBACourse,
        on_delete=models.CASCADE,
        related_name='subjects',
        null=True,
        blank=True
    )
    year = models.CharField(max_length=50) # Part 1, Part 2, Part 3
    course_name = models.CharField(max_length=255)
    course_type = models.CharField(max_length=50)
    marks = models.PositiveIntegerField(default=100)
    code  = models.CharField(max_length=20, null=True, blank=True)
    paper_type = models.CharField(max_length=20, null=True, blank=True, choices=PAPER_TYPE_CHOICES, help_text='Honours/Subsidiary')
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Common Course Structure'
        verbose_name_plural = 'BBA Common Course Structures'
        ordering = ['year', 'course_name']

    def __str__(self):
        return f"{self.year} - {self.course_name}"

class BBAExam(models.Model):
    """
    Overall Examination Event for BBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)            # BBA Part 1 Examination
    year = models.PositiveIntegerField(null=True, blank=True)              # 1, 2, 3
    session = models.CharField(max_length=20, null=True, blank=True)        # 2022-25
    exam_month_year = models.CharField(max_length=20, null=True, blank=True) 
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unnamed Exam'} ({self.session or 'No Session'})"

class BBAExamCenterMapping(models.Model):
    """
    Center Fixation for BBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        BBAExam,
        on_delete=models.CASCADE,
        related_name='bba_center_mappings'
    )
    center = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='bba_as_center_mappings'
    )
    attached_colleges = models.ManyToManyField(
        'colleges.College',
        related_name='bba_exam_centers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Exam Center Mapping'
        verbose_name_plural = 'BBA Exam Center Mappings'
        unique_together = ('exam', 'center')

    def __str__(self):
        return f"{self.exam.name} @ {self.center.name}"


class BBAExamSchedule(models.Model):
    """
    Exam Routine for BBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        BBAExam, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    common_course_structure = models.ForeignKey(
        BBACommonCourseStructure, 
        on_delete=models.CASCADE, 
        related_name='bba_exam_schedules',
        null=True,
        blank=True
    )
    exam_date = models.DateField(null=True, blank=True)
    exam_time = models.CharField(max_length=100, null=True, blank=True)
    sitting = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Exam Schedule'
        verbose_name_plural = 'BBA Exam Schedules'
        ordering = ['exam_date', 'exam_time']

    def __str__(self):
        return f"{self.exam.name} - {self.common_course_structure.code if self.common_course_structure else 'N/A'} ({self.exam_date})"

class BBAYearRegistration(models.Model):
    """
    Year Registration for BBA Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BBAStudentProfile,
        on_delete=models.CASCADE,
        related_name='year_registrations'
    )
    year = models.IntegerField(null=True, blank=True) # 1, 2, 3
    is_open = models.BooleanField(default=False)
    status = models.CharField(max_length=10, null=True, blank=True)
    exam_eligible = models.BooleanField(default=False)
    remarks = models.TextField(null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Year Registration'
        verbose_name_plural = 'BBA Year Registrations'

    def __str__(self):
        return f"{self.student} - Year {self.year}"

class BBAExamRegistration(models.Model):
    """
    Exam Registration for BBA Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BBAStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_registrations'
    )
    exam = models.ForeignKey(
        BBAExam,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        default='REGULAR'
    )
    exam_subjects = models.ManyToManyField(
        BBACommonCourseStructure,
        blank=True,
    )
    fees = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Exam Registration'
        verbose_name_plural = 'BBA Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student}"

class BBAStudentAssessment(models.Model):
    """
    Detailed marks per subject and assessment label for BBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BBAStudentProfile,
        on_delete=models.CASCADE,
        related_name='course_assessments'
    )
    course_name = models.CharField(max_length=250, null=True, blank=True)
    course_type = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    course_code = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    year = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    label = models.CharField(max_length=200, db_index=True, choices=ASSESSMENT_LABEL_CHOICES)
    session = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    batch = models.ForeignKey(
        BBABatch,
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
    ind_is_absent = models.BooleanField(default=False, db_index=True)
    ind_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_is_pass = models.BooleanField(null=True, blank=True)

    #### Aggregated Marks ####
    comb_max_marks = models.IntegerField(null=True, blank=True)
    comb_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comb_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    #### Year Summary ####
    year_result = models.CharField(max_length=20, null=True, blank=True, choices=YEAR_RESULT_CHOICES)
    next_year_status = models.CharField(max_length=20, null=True, blank=True, choices=PROMOTION_STATUS_CHOICES)

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'BBA Student Assessment'
        verbose_name_plural = 'BBA Student Assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'year'], name='idx_bba_stud_year'),
            models.Index(fields=['batch', 'year'], name='idx_bba_batch_year'),
            models.Index(fields=['course_code', 'year'], name='idx_bba_course_year'),
        ]
        
    def save(self, *args, **kwargs):
        if self.ind_marks_obtained is not None and self.ind_max_marks is not None:
            if self.ind_marks_obtained > self.ind_max_marks:
                raise ValueError(f"Marks ({self.ind_marks_obtained}) > Max ({self.ind_max_marks})")
        if self.ind_marks_obtained is not None and self.ind_pass_marks is not None:
            self.ind_is_pass = self.ind_marks_obtained >= self.ind_pass_marks if not self.ind_is_absent else False
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.student} | {self.year} | {self.label}"

class BBAExamResult(models.Model):
    """
    Final summary result for a BBA Year.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BBAStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_results'
    )
    year = models.CharField(max_length=10, db_index=True)
    session = models.CharField(max_length=10, db_index=True)
    year_result = models.CharField(
        max_length=20,
        db_index=True,
        choices=YEAR_RESULT_CHOICES
    )
    total_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    next_year = models.PositiveIntegerField(null=True, blank=True)
    next_year_status = models.CharField(max_length=15, null=True, blank=True, choices=PROMOTION_STATUS_CHOICES)
    is_legacy = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BBA Exam Result'
        verbose_name_plural = 'BBA Exam Results'
        unique_together = ('student', 'year', 'session')
        indexes = [
            models.Index(fields=['student', 'year']),
            models.Index(fields=['year_result']),
        ]

    def __str__(self):
        return f"{self.student} | Year {self.year} | {self.year_result}"


class BBAStudentCourseAssessment(models.Model):
    """
    Year-wise assessment + marks for a student course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    bba_exam = models.ForeignKey(BBAExam, on_delete=models.PROTECT, null=True)
    course_name = models.CharField(max_length=250, null=True, blank=True)
    student = models.ForeignKey(
        BBAStudentProfile,
        on_delete=models.CASCADE,
        related_name='bba_student_course_assessment'
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    course_code = models.CharField(max_length=20, null=True, blank=True)
    paper_code = models.CharField(max_length=20, null=True, blank=True, db_index=True)

    year = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    label = models.CharField(max_length=100, db_index=True)
    session = models.ForeignKey(
        BBASession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    batch = models.ForeignKey(
        BBABatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    college_code = models.CharField(max_length=10, null=True, blank=True)
    exam_type = models.CharField(max_length=10, null=True, blank=True, db_index=True)

    attendance = models.CharField(max_length=10, null=True, blank=True)

    ####Individual####
    ind_max_marks = models.IntegerField(null=True, blank=True)
    ind_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_is_absent = models.BooleanField(default=False, db_index=True)
    ind_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ind_is_pass = models.BooleanField(null=True, blank=True)
    ####Individual####

    ####combined####
    comb_max_marks = models.IntegerField(null=True, blank=True)
    comb_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comb_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comb_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comb_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ####combined####

    ####year####
    year_max_marks = models.IntegerField(null=True, blank=True)
    year_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    year_result = models.CharField(max_length=10, null=True, blank=True)
    next_year_status = models.CharField(max_length=10, null=True, blank=True)
    ####year####

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'BBA Student Course Assessment'
        verbose_name_plural = 'BBA Student Course Assessments'
        ordering = ['-created_at']
        unique_together = ('student', 'paper_code', 'year', 'label', 'exam_type', 'session')
        indexes = [
            models.Index(fields=['student', 'year'], name='bba_idx_student_year'),
            models.Index(fields=['batch', 'year'], name='bba_idx_batch_year'),
            models.Index(fields=['paper_code', 'year'], name='bba_idx_paper_year'),
        ]

    def save(self, *args, **kwargs):
        if self.ind_marks_obtained is not None and self.ind_max_marks is not None:
            if self.ind_marks_obtained > self.ind_max_marks:
                raise ValueError(f"Marks ({self.ind_marks_obtained}) > Max ({self.ind_max_marks})")
        
        if self.ind_marks_obtained is not None and self.ind_pass_marks is not None:
            if self.ind_is_absent:
                self.ind_is_pass = False
            else:
                self.ind_is_pass = self.ind_marks_obtained >= self.ind_pass_marks
        
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.student} | Year {self.year} | {self.label}"
