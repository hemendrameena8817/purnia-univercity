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

class BCAHonsCourse(models.Model):
    """
    Represents a specific BCA Hons Course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True) 
    course_code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    discipline_code = models.CharField(max_length=255, null=True, blank=True)
    duration_years = models.PositiveIntegerField(default=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed BCA Hons Course"

class BCAHonsSession(models.Model):
    """
    Academic Session for BCA Hons.
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

class BCAHonsBatch(models.Model):
    """
    Represents a batch of students in a BCA Hons program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text='Batch name e.g., 2022-2025')
    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BCA Hons Batch'
        verbose_name_plural = 'BCA Hons Batches'
        ordering = ['name']

    def __str__(self):
        return self.name

# 2. Student & Course Master Models
class BCAHonsStudentProfile(models.Model):
    """
    BCA Hons Student profile linked to a UserAccount.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='bca_hons_student_profile',
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
        related_name='bca_hons_students',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        BCAHonsCourse,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    batch = models.ForeignKey(
        BCAHonsBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    current_year = models.PositiveIntegerField(null=True, blank=True) # 1, 2, 3
    session_str = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STUDENT_STATUS_CHOICES, default='Regular')

    profile_image = models.ImageField(upload_to='bca_hons_students/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='bca_hons_students/signatures/', null=True, blank=True)

    part_1_marks = models.CharField(max_length=50, null=True, blank=True)
    part_2_marks = models.CharField(max_length=50, null=True, blank=True)
    part_3_marks = models.CharField(max_length=50, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BCA Hons Student Profile'
        verbose_name_plural = 'BCA Hons Student Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.registration_no}) ({self.roll_no})"

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

class BCAHonsCourseStructure(models.Model):
    """
    Represents the course structure configuration for BCA Hons.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course = models.ForeignKey(
        BCAHonsCourse,
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
        verbose_name = 'BCA Hons Course Structure'
        verbose_name_plural = 'BCA Hons Course Structures'

    def __str__(self):
        return f"{self.course_name} ({self.course_code}) - {self.year}"

class BCAHonsCommonCourseStructure(models.Model):
    """
    Common structure template for BCA Hons.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course = models.ForeignKey(
        BCAHonsCourse,
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
    paper_type = models.CharField(max_length=20, null=True, blank=True, help_text='Honours/Subsidiary/Composition')
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BCA Hons Common Course Structure'
        verbose_name_plural = 'BCA Hons Common Course Structures'
        ordering = ['year', 'course_name']

    def __str__(self):
        return f"{self.year} - {self.course_name}"

class BCAHonsExam(models.Model):
    """
    Overall Examination Event for BCA Hons.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)            # BCA Hons Part 1 Examination
    year = models.PositiveIntegerField(null=True, blank=True)              # 1, 2, 3
    session = models.CharField(max_length=20, null=True, blank=True)        # 2022-25
    exam_month_year = models.CharField(max_length=20, null=True, blank=True) 
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unnamed Exam'} ({self.session or 'No Session'})"

class BCAHonsExamCenterMapping(models.Model):
    """
    Center Fixation for BCA Hons.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        BCAHonsExam,
        on_delete=models.CASCADE,
        related_name='bca_hons_center_mappings'
    )
    center = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='bca_hons_as_center_mappings'
    )
    attached_colleges = models.ManyToManyField(
        'colleges.College',
        related_name='bca_hons_exam_centers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BCA Hons Exam Center Mapping'
        verbose_name_plural = 'BCA Hons Exam Center Mappings'
        unique_together = ('exam', 'center')

    def __str__(self):
        return f"{self.exam.name} @ {self.center.name}"


class BCAHonsExamSchedule(models.Model):
    """
    Exam Routine for BCA Hons.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        BCAHonsExam, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    common_course_structure = models.ForeignKey(
        BCAHonsCommonCourseStructure, 
        on_delete=models.CASCADE, 
        related_name='bca_hons_exam_schedules',
        null=True,
        blank=True
    )
    exam_date = models.DateField(null=True, blank=True)
    exam_time = models.CharField(max_length=100, null=True, blank=True)
    sitting = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BCA Hons Exam Schedule'
        verbose_name_plural = 'BCA Hons Exam Schedules'
        ordering = ['exam_date', 'exam_time']

    def __str__(self):
        return f"{self.exam.name} - {self.common_course_structure.code if self.common_course_structure else 'N/A'} ({self.exam_date})"

class BCAHonsYearRegistration(models.Model):
    """
    Year Registration for BCA Hons Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BCAHonsStudentProfile,
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
        verbose_name = 'BCA Hons Year Registration'
        verbose_name_plural = 'BCA Hons Year Registrations'

    def __str__(self):
        return f"{self.student} - Year {self.year}"

class BCAHonsExamRegistration(models.Model):
    """
    Exam Registration for BCA Hons Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BCAHonsStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_registrations'
    )
    exam = models.ForeignKey(
        BCAHonsExam,
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
        BCAHonsCommonCourseStructure,
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
        verbose_name = 'BCA Hons Exam Registration'
        verbose_name_plural = 'BCA Hons Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student}"

class BCAHonsStudentAssessment(models.Model):
    """
    Detailed marks per subject and assessment label for BCA Hons.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BCAHonsStudentProfile,
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
        BCAHonsBatch,
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
        verbose_name = 'BCA Hons Student Assessment'
        verbose_name_plural = 'BCA Hons Student Assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'year'], name='bca_idx_stud_year'),
            models.Index(fields=['batch', 'year'], name='bca_idx_batch_year'),
            models.Index(fields=['course_code', 'year'], name='bca_idx_course_year'),
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

class BCAHonsExamResult(models.Model):
    """
    Final summary result for a BCA Hons Year.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BCAHonsStudentProfile,
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
        verbose_name = 'BCA Hons Exam Result'
        verbose_name_plural = 'BCA Hons Exam Results'
        unique_together = ('student', 'year', 'session')
        indexes = [
            models.Index(fields=['student', 'year']),
            models.Index(fields=['year_result']),
        ]

    def __str__(self):
        return f"{self.student} | Year {self.year} | {self.year_result}"


class BCAHonsStudentCourseAssessment(models.Model):
    """
    Year-wise assessment + marks for a student course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    bca_hons_exam = models.ForeignKey(BCAHonsExam, on_delete=models.PROTECT, null=True)
    course_name = models.CharField(max_length=250, null=True, blank=True)
    student = models.ForeignKey(
        BCAHonsStudentProfile,
        on_delete=models.CASCADE,
        related_name='bca_hons_student_course_assessment'
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    course_code = models.CharField(max_length=20, null=True, blank=True)
    paper_code = models.CharField(max_length=20, null=True, blank=True, db_index=True)

    year = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    label = models.CharField(max_length=100, db_index=True)
    session = models.ForeignKey(
        BCAHonsSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    batch = models.ForeignKey(
        BCAHonsBatch,
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
        verbose_name = 'BCA Hons Student Course Assessment'
        verbose_name_plural = 'BCA Hons Student Course Assessments'
        ordering = ['-created_at']
        unique_together = ('student', 'paper_code', 'year', 'label', 'exam_type', 'session')
        indexes = [
            # Student-based queries
            models.Index(fields=['student', 'year'], name='bcah_idx_student_year'),
            models.Index(fields=['batch', 'year'], name='bcah_idx_batch_year'),
            models.Index(fields=['paper_code', 'year'], name='bcah_idx_paper_year'),
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
