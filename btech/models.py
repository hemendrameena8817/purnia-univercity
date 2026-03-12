from django.db import models
import uuid
from django.conf import settings
from pup_umis_backend.storage_backends import MediaStorage
from pup_umis_backend.upload_paths import unique_file_path
from .choices import (
    YEAR_RESULT_CHOICES,
    STUDENT_STATUS_CHOICES,
    GENDER_CHOICES,
    EXAM_TYPE_CHOICES,
    ASSESSMENT_LABEL_CHOICES,
    PROMOTION_STATUS_CHOICES,
)

# 1. Master Structure Models
class BTechCourse(models.Model):
    """
    Represents a specific BTech Course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)  
    duration_years = models.PositiveIntegerField(default=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Course"

class BTechBranch(models.Model):
    """
    Represents a branch in BTech (e.g., Mechanical Engineering, CSE, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)  # Mechanical Engineering
    code = models.CharField(max_length=20, null=True, blank=True) # ME, CSE
    course = models.ForeignKey(
        BTechCourse,
        on_delete=models.CASCADE,
        related_name='branches'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BTech Branch'
        verbose_name_plural = 'BTech Branches'

    def __str__(self):
        return f"{self.name} ({self.code})"

class BTechSession(models.Model):
    """
    Academic Session for BTech.
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

class BTechBatch(models.Model):
    """
    Represents a batch of students in an BTech program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, help_text='Batch name e.g., 2022-2024')
    session = models.ForeignKey(
        BTechSession,
        on_delete=models.PROTECT,
        related_name='batches',
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        BTechBranch,
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
        verbose_name = 'BTech Batch'
        verbose_name_plural = 'BTech Batches'
        ordering = ['name']

    def __str__(self):
        return self.name

# 2. Student & Course Master Models
class BTechStudentProfile(models.Model):
    """
    BTech Student profile linked to a UserAccount.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='btech_student_profile',
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
    apaar_id = models.CharField(max_length=20, null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    
    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='btech_students',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        BTechCourse,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    batch = models.ForeignKey(
        BTechBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        BTechBranch,
        on_delete=models.PROTECT,
        related_name='students',
        null=True,
        blank=True
    )
    
    current_year = models.PositiveIntegerField(null=True, blank=True)
    session_str = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STUDENT_STATUS_CHOICES, default='REGULAR')

    profile_image = models.ImageField(storage=MediaStorage(), upload_to=unique_file_path('btech_students/profiles/'), null=True, blank=True)
    signature = models.ImageField(storage=MediaStorage(), upload_to=unique_file_path('btech_students/signatures/'), null=True, blank=True)
    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BTech Student Profile'
        verbose_name_plural = 'BTech Student Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.registration_no})"

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

class BTechCourseStructure(models.Model):
    """
    Represents the course structure configuration for an BTech program.
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
    
    year = models.CharField(max_length=20, null=True, blank=True, help_text="Year")
    branch = models.ForeignKey(
        BTechBranch,
        on_delete=models.CASCADE,
        related_name='course_structures',
        null=True,
        blank=True
    )
    
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BTech Course Structure'
        verbose_name_plural = 'BTech Course Structures'

    def __str__(self):
        return f"{self.course_name} ({self.course_code}) - {self.year}"

class BTechCommonCourseStructure(models.Model):
    """
    Common structure template for BTech.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    year = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    course_type = models.CharField(max_length=50)
    ltp = models.CharField(max_length=20, null=True, blank=True)
    marks = models.PositiveIntegerField(default=100)
    code  = models.CharField(max_length=20, null=True, blank=True)
    branch = models.ForeignKey(
        BTechBranch,
        on_delete=models.CASCADE,
        related_name='common_course_structures',
        null=True,
        blank=True
    )
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BTech Common Course Structure'
        verbose_name_plural = 'BTech Common Course Structures'
        ordering = ['year', 'course_name']

    def __str__(self):
        return f"{self.year} - {self.course_name}"

class BTechExam(models.Model):
    """
    Represents the overall Examination Event (e.g. BTech 4th Sem June 2024).
    Contains the global schedule shared by all centers.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)            # BTech 4th Semester Examination
    year = models.PositiveIntegerField(null=True, blank=True)         # 4
    session = models.CharField(max_length=20, null=True, blank=True)        # 2022-24
    batch = models.CharField(max_length=20, null=True, blank=True)  
    exam_month_year = models.CharField(max_length=20, null=True, blank=True) # June 2024
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unnamed Exam'} ({self.session or 'No Session'})"

class BTechExamCenterMapping(models.Model):
    """
    Center Fixation: Maps an Exam + Center to one or more Colleges.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exams = models.ManyToManyField(
        BTechExam,
        related_name='center_mappings'
    )
    center = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='btech_as_center_mappings'
    )
    # The colleges whose students will go to this center for this specific exam
    attached_colleges = models.ManyToManyField(
        'colleges.College',
        related_name='btech_exam_centers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BTech Exam Center Mapping'
        verbose_name_plural = 'BTech Exam Center Mappings'

    def __str__(self):
        exam_count = self.exams.count()
        return f"{self.center.name} ({exam_count} Exams)"


class BTechExamSchedule(models.Model):
    """
    Exam Routine/Datesheet for BTech.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        BTechExam, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    # Changed from BTechSubject to BTechCourseStructure
    common_course_structure = models.ForeignKey(
        BTechCommonCourseStructure, 
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
        verbose_name = 'BTech Exam Schedule'
        verbose_name_plural = 'BTech Exam Schedules'
        # unique_together = ('exam', 'course_structure')
        ordering = ['exam_date', 'exam_time']

    def __str__(self):
        return f"{self.exam.name} - {self.common_course_structure.code if self.common_course_structure else 'N/A'} ({self.exam_date})"

class BTechYearRegistration(models.Model):
    """
    Year Registration for BTech Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BTechStudentProfile,
        on_delete=models.CASCADE,
        related_name='year_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=False)
    year = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    exam_eligible = models.BooleanField(default=False)
    remarks = models.TextField(null=True, blank=True)
    session = models.CharField(max_length=20, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BTech Year Registration'
        verbose_name_plural = 'BTech Year Registrations'

    def __str__(self):
        return f"{self.student}"

class BTechExamRegistration(models.Model):
    """
    Exam Registration for BTech Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BTechStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_registrations'
    )
    exam = models.ForeignKey(
        'BTechExam',
        on_delete=models.CASCADE,
        related_name='registrations',
        null=True,
        blank=True
    )
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        default='REGULAR'
    )
    backlog_subjects = models.ManyToManyField(
        'BTechCommonCourseStructure',
        blank=True,
        related_name='backlog_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=False)
    fees = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BTech Exam Registration'
        verbose_name_plural = 'BTech Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student} - {self.exam_type} - Year {self.year}"

# 4. Result & Assessment Models
class BTechStudentAssessment(models.Model):
    """
    Detailed marks per subject and assessment label for BTech.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BTechStudentProfile,
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
        BTechBatch,
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
    year_result = models.CharField(max_length=20, null=True, blank=True, choices=YEAR_RESULT_CHOICES)
    next_year_status = models.CharField(max_length=20, null=True, blank=True, choices=PROMOTION_STATUS_CHOICES)

    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'BTech Student Assessment'
        verbose_name_plural = 'BTech Student Assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'year'], name='idx_btech_stud_year'),
            models.Index(fields=['batch', 'year'], name='idx_btech_batch_year'),
            models.Index(fields=['course_code', 'year'], name='idx_btech_course_year'),
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

class BTechExamResult(models.Model):
    """
    Final summary result for an BTech Semester.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        BTechStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_results'
    )
    year = models.CharField(max_length=10, db_index=True)
    session = models.CharField(max_length=10, db_index=True)
    cia_pass = models.BooleanField(null=True, blank=True)
    ese_pass = models.BooleanField(null=True, blank=True)
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
        verbose_name = 'BTech Exam Result'
        verbose_name_plural = 'BTech Exam Results'
        unique_together = ('student', 'year', 'session')
        indexes = [
            models.Index(fields=['student', 'year']),
            models.Index(fields=['year_result']),
        ]

    def __str__(self):
        return f"{self.student} | Year {self.year} | {self.year_result}"
