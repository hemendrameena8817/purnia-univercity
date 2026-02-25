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
# ONLY
# MBA Finance
# MBA HR
# MBA Marketing

class MBACourse(models.Model):
    """
    Represents a specific MBA Course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True) # MBA (Marketing), MBA (HUMAN Resource) => Distinct =>CharField #pending 
    discipline_code = models.CharField(max_length=255, null=True, blank=True)
    duration_years = models.PositiveIntegerField(default=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Course"

class MBASession(models.Model):
    """
    Academic Session for MBA.
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

class MBABatch(models.Model):
    """
    Represents a batch of students in an MBA program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, help_text='Batch name e.g., 2022-2024')
    session = models.ForeignKey(
        MBASession,
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
        verbose_name = 'MBA Batch'
        verbose_name_plural = 'MBA Batches'
        ordering = ['name']

    def __str__(self):
        return self.name

# 2. Student & Course Master Models
class MBAStudentProfile(models.Model):
    """
    MBA Student profile linked to a UserAccount.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='mba_student_profile',
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
        related_name='mba_students',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        MBACourse,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    batch = models.ForeignKey(
        MBABatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    current_semester = models.PositiveIntegerField(null=True, blank=True)
    session_str = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STUDENT_STATUS_CHOICES, default='Regular')

    profile_image = models.ImageField(upload_to='mba_students/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='mba_students/signatures/', null=True, blank=True)

    sem_1_gpa = models.CharField(max_length=50, null=True, blank=True)
    sem_1_credit_earned = models.CharField(max_length=50, null=True, blank=True)
    sem_2_gpa = models.CharField(max_length=50, null=True, blank=True)
    sem_2_credit_earned = models.CharField(max_length=50, null=True, blank=True)
    sem_3_gpa = models.CharField(max_length=50, null=True, blank=True)
    sem_3_credit_earned = models.CharField(max_length=50, null=True, blank=True)
    sem_4_gpa = models.CharField(max_length=50, null=True, blank=True)
    sem_4_credit_earned = models.CharField(max_length=50, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MBA Student Profile'
        verbose_name_plural = 'MBA Student Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.registration_no}) ({self.roll_no})"

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

class MBACourseStructure(models.Model):
    """
    Represents the course structure configuration for an MBA program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course_name = models.CharField(max_length=500, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True)
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type") 
    course_code = models.CharField(max_length=50, null=True, blank=True, help_text="Course Code")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course Marks")
    min_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Pass Mark")
    
    description = models.TextField(null=True, blank=True, help_text="Course Description")
    label = models.CharField(max_length=100, null=True, blank=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)") #End CIA/SEM 101 mid, end
    
    semester = models.CharField(max_length=20, null=True, blank=True, help_text="Semester")
    
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    credit = models.PositiveIntegerField(default=100)

    class Meta:
        verbose_name = 'MBA Course Structure'
        verbose_name_plural = 'MBA Course Structures'

    def __str__(self):
        return f"{self.course_name} ({self.course_code}) - {self.semester}"

class MBACommonCourseStructure(models.Model):
    """
    Common structure template for MBA.
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
        verbose_name = 'MBA Common Course Structure'
        verbose_name_plural = 'MBA Common Course Structures'
        ordering = ['semester', 'course_name']

    def __str__(self):
        return f"{self.semester} - {self.course_name}"

class MBAExam(models.Model):
    """
    Represents the overall Examination Event (e.g. MBA 4th Sem June 2024).
    Contains the global schedule shared by all centers.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)            # MBA 4th Semester Examination
    semester = models.PositiveIntegerField(null=True, blank=True)         # 4
    session = models.CharField(max_length=20, null=True, blank=True)        # 2022-24
    exam_month_year = models.CharField(max_length=20, null=True, blank=True) # June 2024
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unnamed Exam'} ({self.session or 'No Session'})"

class MBAExamCenterMapping(models.Model):
    """
    Center Fixation: Maps an Exam + Center to one or more Colleges.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        MBAExam,
        on_delete=models.CASCADE,
        related_name='mba_center_mappings'
    )
    center = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='mba_as_center_mappings'
    )
    # The colleges whose students will go to this center for this specific exam
    attached_colleges = models.ManyToManyField(
        'colleges.College',
        related_name='mba_exam_centers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MBA Exam Center Mapping'
        verbose_name_plural = 'MBA Exam Center Mappings'
        unique_together = ('exam', 'center')

    def __str__(self):
        return f"{self.exam.name} @ {self.center.name}"


class MBAExamSchedule(models.Model):
    """
    Exam Routine/Datesheet for MBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        MBAExam, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    # Changed from MBASubject to MBACourseStructure
    common_course_structure = models.ForeignKey(
        MBACommonCourseStructure, 
        on_delete=models.CASCADE, 
        related_name='mba_exam_schedules',
        null=True,
        blank=True
    )
    exam_date = models.DateField(null=True, blank=True)
    exam_time = models.CharField(max_length=100, null=True, blank=True)
    sitting = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MBA Exam Schedule'
        verbose_name_plural = 'MBA Exam Schedules'
        # unique_together = ('exam', 'course_structure')
        ordering = ['exam_date', 'exam_time']

    def __str__(self):
        return f"{self.exam.name} - {self.common_course_structure.code if self.common_course_structure else 'N/A'} ({self.exam_date})"

class MBASemesterRegistration(models.Model):
    """
    Semester Registration for MBA Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MBAStudentProfile,
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
        verbose_name = 'MBA Semester Registration'
        verbose_name_plural = 'MBA Semester Registrations'

    def __str__(self):
        return f"{self.student}"

class MBAExamRegistration(models.Model):
    """
    Exam Registration for MBA Students.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MBAStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_registrations'
    )
    exam = models.ForeignKey(
        MBAExam,
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
        MBACommonCourseStructure,
        blank=True,
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
        verbose_name = 'MBA Exam Registration'
        verbose_name_plural = 'MBA Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student}"

# 4. Result & Assessment Models
class MBAStudentAssessment(models.Model):
    """
    Detailed marks per subject and assessment label for MBA.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MBAStudentProfile,
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
        MBABatch,
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
        verbose_name = 'MBA Student Assessment'
        verbose_name_plural = 'MBA Student Assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'semester'], name='idx_mba_stud_sem'),
            models.Index(fields=['batch', 'semester'], name='idx_mba_batch_sem'),
            models.Index(fields=['course_code', 'semester'], name='idx_mba_course_sem'),
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

class MBAExamResult(models.Model):
    """
    Final summary result for an MBA Semester.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MBAStudentProfile,
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
        verbose_name = 'MBA Exam Result'
        verbose_name_plural = 'MBA Exam Results'
        unique_together = ('student', 'semester', 'session')
        indexes = [
            models.Index(fields=['student', 'semester']),
            models.Index(fields=['semester_result']),
        ]

    def __str__(self):
        return f"{self.student} | Sem {self.semester} | {self.semester_result}"


class MBAStudentCourseAssessment(models.Model):
    """
    Semester-wise assessment + marks for a student course
    using flexible labels (CIA-Theory, ESE-Practical, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    mba_exam = models.ForeignKey(MBAExam, on_delete=models.PROTECT, null=True)
    course_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Short Name (e.g., 'IM' for 'Introductory Microeconomics').")
    student = models.ForeignKey(
        MBAStudentProfile,
        on_delete=models.CASCADE,
        help_text="Student",
        related_name='mba_student_course_assessment'
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Course Type")
    course_code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    paper_code = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Paper Code")

    semester = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Semester")
    label = models.CharField(max_length=100, db_index=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
    degree = models.CharField(max_length=20, null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Session")
    batch = models.ForeignKey(
        MBABatch,
        on_delete=models.CASCADE,
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
    ind_is_absent = models.BooleanField(default=False, db_index=True, help_text="Is Absent")
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
        verbose_name = 'MBA Student Course Assessment'
        verbose_name_plural = 'MBA Student Course Assessments'
        ordering = ['-created_at']
        unique_together = ('student', 'paper_code', 'semester', 'label', 'exam_type', 'session')
        
        # Composite indexes for common query patterns
        indexes = [
            # Student-based queries
            models.Index(fields=['student', 'semester'], name='mba_idx_student_sem'),
            models.Index(fields=['student', 'semester', 'label'], name='mba_idx_stud_sem_label'),
            
            # Department-based queries (for faculty reports via department FK)
            # models.Index(fields=['department', 'semester'], name='idx_dept_sem'),
            # models.Index(fields=['department', 'semester', 'label'], name='idx_dept_sem_label'),
            
            # Batch-based queries
            models.Index(fields=['batch', 'semester'], name='mba_idx_batch_sem'),
            
            # Course-based queries
            models.Index(fields=['paper_code', 'semester'], name='mba_idx_paper_sem'),
            models.Index(fields=['semester', 'label'], name='mba_idx_sem_label'),
            
            # CRITICAL: Registration duplicate checking (30k students optimization)
            # Includes exam_type to differentiate regular vs back exams
            models.Index(fields=['student', 'semester', 'session', 'paper_code', 'label', 'exam_type'], 
                        name='mba_idx_reg_dup_check'),
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


