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

class MCACourse(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)  
    duration_years = models.PositiveIntegerField(default=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Course"

class MCASession(models.Model):
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
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=50, null=True, blank=True)  # 2021 Admission
    admission_year = models.PositiveIntegerField(null=True, blank=True)

    session = models.ForeignKey(
        MCASession,
        on_delete=models.PROTECT,
        related_name='batches',
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.session.name if self.session else 'No Session'})"

class MCAStudentProfile(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mca_profile",
        null=True,
        blank=True
    )

    roll_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    registration_no = models.CharField(max_length=30, unique=True, null=True, blank=True)

    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)

    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.PROTECT,
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

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        name = self.user.get_full_name() if self.user else "No User"
        return f"{self.roll_no if self.roll_no else 'No Roll'} - {name}"

class MCASubject(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)  
    subject_code = models.CharField(max_length=500, null=True, blank=True)  
    paper_code = models.CharField(max_length=500, null=True, blank=True)  
    semester = models.PositiveIntegerField(null=True, blank=True)
    full_marks = models.PositiveIntegerField(default=100, null=True, blank=True)
    pass_marks = models.PositiveIntegerField(default=33, null=True, blank=True)
    credit = models.PositiveIntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.paper_code})"

class MCAExam(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)  
    session = models.CharField(max_length=20, null=True, blank=True)  # 2021-23
    exam_month_year = models.CharField(max_length=20, null=True, blank=True)  # July 2022
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Exam"

class MCAExamSchedule(models.Model):
    """
    Manages the date and time for each subject/paper in a specific exam.
    This is used for generating Admit Cards and Exam Routines.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        MCAExam, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    subject = models.ForeignKey(
        MCASubject, 
        on_delete=models.CASCADE, 
        related_name='exam_schedules'
    )
    
    exam_date = models.DateField(null=True, blank=True)
    exam_time = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        help_text="e.g. 10:00 AM - 01:00 PM"
    )
    sitting = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        help_text="e.g. 1st Sitting / 2nd Sitting"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Exam Schedule'
        verbose_name_plural = 'MCA Exam Schedules'
        unique_together = ('exam', 'subject')
        ordering = ['exam_date', 'exam_time']

    def __str__(self):
        return f"{self.exam.name} - {self.subject.paper_code} ({self.exam_date})"

class MCAStudentAssessment(models.Model):
    """
    Semester-wise assessment + marks for a student course
    using flexible labels (CIA-Theory, ESE-Practical, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
        on_delete=models.CASCADE,
        related_name='course_assessments',
        help_text="Student"
    )
    subject = models.ForeignKey(
        MCASubject,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='assessments'
    )

    semester = models.CharField(max_length=200, null=True, blank=True, db_index=True, help_text="Semester")
    label = models.CharField(max_length=200, db_index=True, choices=ASSESSMENT_LABEL_CHOICES, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.CASCADE,
        related_name='mca_assessments',
        null=True,
        blank=True
    )
    degree = models.CharField(max_length=20, null=True, blank=True)
    session = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Session")
    batch = models.ForeignKey(
        MCABatch,
        on_delete=models.CASCADE,
        related_name='student_assessments',
        null=True,
        blank=True
    )
    college_code = models.CharField(max_length=10, null=True, blank=True, help_text="College Code")
    exam_type = models.CharField(max_length=200, choices=EXAM_TYPE_CHOICES, null=True, blank=True, db_index=True, help_text="Type Regular/Back")

    ###attendance###
    attendance = models.CharField(max_length=200, null=True, blank=True, help_text="Attendance")
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
    sem_result = models.CharField(max_length=20, null=True, blank=True, choices=SEMESTER_RESULT_CHOICES, help_text="Semester Result eg: pass/fail/promoted")
    next_sem_status = models.CharField(max_length=20, null=True, blank=True, choices=PROMOTION_STATUS_CHOICES, help_text="Next Semester Status eg: eligible/not eligible")
    sem_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Semester GRACE MARKS OBTAINED")
    ####semester####

    #####temp#####
    temp_total_gp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total GRADE POINT")
    #####temp#####

    json_data = models.JSONField(null=True, blank=True, help_text="JSON Data")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created At")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated At")
    
    class Meta:
        verbose_name = 'MCA Student Course Assessment'
        verbose_name_plural = 'MCA Student Course Assessments'
        ordering = ['-created_at']
        
        indexes = [
            models.Index(fields=['student', 'semester'], name='idx_mca_student_sem'),
            models.Index(fields=['student', 'semester', 'label'], name='idx_mca_stud_sem_label'),
            models.Index(fields=['college', 'semester'], name='idx_mca_college_sem'),
            models.Index(fields=['batch', 'semester'], name='idx_mca_batch_sem'),
            models.Index(fields=['subject', 'semester'], name='idx_mca_subj_sem'),
            models.Index(fields=['semester', 'label'], name='idx_mca_sem_label'),
        ]
        
    def save(self, *args, **kwargs):
        if self.ind_marks_obtained is not None and self.ind_max_marks is not None:
            if self.ind_marks_obtained > self.ind_max_marks:
                raise ValueError(
                    f"Individual marks obtained ({self.ind_marks_obtained}) "
                    f"cannot exceed maximum marks ({self.ind_max_marks})"
                )
        
        if self.ind_marks_obtained is not None and self.ind_pass_marks is not None:
            if self.ind_is_absent:
                self.ind_is_pass = False
            else:
                self.ind_is_pass = self.ind_marks_obtained >= self.ind_pass_marks
        elif self.ind_is_absent:
            self.ind_is_pass = False
        
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.student} | Sem {self.semester} | {self.label}"


class MCASemesterResult(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    student = models.ForeignKey(
        MCAStudentProfile,
        on_delete=models.CASCADE,
        related_name='semester_results'
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
        help_text="Semester result status"
    )

    # CREDIT & SGPA
    semester_max_credit = models.PositiveIntegerField(null=True, blank=True)
    semester_credit_earned = models.PositiveIntegerField(null=True, blank=True)

    sgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    # PROMOTION
    next_semester = models.PositiveIntegerField(null=True, blank=True)
    next_sem_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=PROMOTION_STATUS_CHOICES,
        help_text="Next semester status"
    )

    # META
    is_legacy = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MCA Semester Result'
        verbose_name_plural = 'MCA Semester Results'
        unique_together = ('student', 'semester', 'session')
        indexes = [
            models.Index(fields=['student', 'semester']),
            models.Index(fields=['semester', 'session']),
            models.Index(fields=['semester_result']),
        ]

    def __str__(self):
        return f"{self.student} | Sem {self.semester} | {self.semester_result}"

class MCASemesterRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
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
        verbose_name = 'MCA Semester Registration'
        verbose_name_plural = 'MCA Semester Registrations'

    def __str__(self):
        return f"{self.student} - Sem {self.sem}"


class MCAExamRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
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
        verbose_name = 'MCA Exam Registration'
        verbose_name_plural = 'MCA Exam Registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student} - Sem {self.sem}"

