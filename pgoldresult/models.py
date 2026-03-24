import uuid
from django.db import models
from django.contrib.auth import get_user_model

# Import College model from colleges app
from colleges.models import College

User = get_user_model()

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]


class PGOldStudentProfile(models.Model):
    """
    PG Student Profile - ONE record per student.
    Links to existing UserAccount and College.
    Stores basic PG student identity and academic association.
    Data transferred from PGOldResult model.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='pg_old_profile',
        null=True,
        blank=True
    )
        # Student-specific Information
 
    # Identity (from PGOldResult)
    registration_no = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text='College Registration Number (college_reg_no from PGOldResult)'
    )
    roll_no = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='College Roll Number (college_roll_no from PGOldResult)'
    )
    first_name = models.CharField(max_length=255)
    hindi_name = models.CharField(max_length=255, null=True, blank=True)
    fathers_name = models.CharField(max_length=255, null=True, blank=True)
    mothers_name = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    
    # Academic Association (stored as codes, no FK to separate tables)
    college = models.ForeignKey(
        College, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='pg_old_students'
    )
    course_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Course code: PG, etc.'
    )
    discipline_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Discipline code: M21, etc.'
    )
    
    # PG Specific Fields
    pg_faculty = models.CharField(max_length=255, null=True, blank=True)
    pg_department = models.CharField(max_length=255, null=True, blank=True)
    pg_degree = models.CharField(max_length=255, null=True, blank=True)
    pg_program = models.CharField(max_length=255, null=True, blank=True)
    
    # Academic Progress
    batch_code = models.CharField(max_length=30, null=True, blank=True)
    current_semester = models.CharField(max_length=30, null=True, blank=True)
    final_result = models.CharField(max_length=50, null=True, blank=True)
    gpa = models.CharField(max_length=20, null=True, blank=True)
    cgpa = models.CharField(max_length=20, null=True, blank=True)
    total_percentage = models.CharField(max_length=20, null=True, blank=True)
    profile_image = models.ImageField(upload_to='pgold/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='pgold/signatures/', null=True, blank=True)
    # Original staging IDs (for reference)
    source_user_id = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        help_text='Original user_id from staging'
    )
    address = models.TextField(null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    caste = models.CharField(max_length=20, null=True, blank=True)
    enrollment_date = models.DateField(null=True, blank=True)
    religion = models.CharField(max_length=50, null=True, blank=True)
    nationality = models.CharField(max_length=50, null=True, blank=True)
    medium_of_student = models.CharField(max_length=50, null=True, blank=True)
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'PG Old Student Profile'
        verbose_name_plural = 'PG Old Student Profiles'
        indexes = [
            models.Index(fields=['registration_no']),
            models.Index(fields=['roll_no']),
            models.Index(fields=['college', 'course_code']),
        ]
    
    def __str__(self):
        return f"{self.registration_no} - {self.first_name}"


class PGOldResult(models.Model):
    """
    Model to store old PG result data from staging.PGResultCurrent.
    This is a copy of historical result data for batches 2023-25 and 2024-26.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Link to Student Profile
    student_profile = models.ForeignKey(
        PGOldStudentProfile,
        on_delete=models.CASCADE,
        related_name='results',
        null=True,
        blank=True,
        help_text='Link to PG Student Profile'
    )
    
    # Original table columns (all as CharField to match staging data exactly
    semester_code = models.CharField(max_length=30, null=True, blank=True)
    batch_code = models.CharField(max_length=30, null=True, blank=True)
    session_code = models.CharField(max_length=30, null=True, blank=True)
    course_code = models.CharField(max_length=30, null=True, blank=True)
    discipline_code = models.CharField(max_length=30, null=True, blank=True)
    paper_code = models.CharField(max_length=50, null=True, blank=True)
    subject_code = models.CharField(max_length=30, null=True, blank=True)
    subject_name = models.CharField(max_length=500, null=True, blank=True)
    faculty = models.CharField(max_length=30, null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    exam_type_his = models.CharField(max_length=30, null=True, blank=True)
    exam_type = models.CharField(max_length=30, null=True, blank=True)
    maximum_mark = models.CharField(max_length=20, null=True, blank=True)
    pass_mark = models.CharField(max_length=20, null=True, blank=True)
    mark_secured = models.CharField(max_length=20, null=True, blank=True)
    subject_total_mark = models.CharField(max_length=20, null=True, blank=True)
    subject_ca = models.CharField(max_length=50, null=True, blank=True)
    subject_ng = models.CharField(max_length=50, null=True, blank=True)
    subject_ce = models.CharField(max_length=50, null=True, blank=True)
    subject_gp = models.CharField(max_length=50, null=True, blank=True)
    total_ca = models.CharField(max_length=50, null=True, blank=True)
    total_ce = models.CharField(max_length=50, null=True, blank=True)
    subject_result = models.CharField(max_length=20, null=True, blank=True)
    final_result = models.CharField(max_length=50, null=True, blank=True)
    grand_total_mark = models.CharField(max_length=20, null=True, blank=True)
    total_secured_mark = models.CharField(max_length=20, null=True, blank=True)
    total_per = models.CharField(max_length=20, null=True, blank=True)
    institute_code = models.CharField(max_length=20, null=True, blank=True)
    gpa = models.CharField(max_length=50, null=True, blank=True)
    cgpa = models.CharField(max_length=50, null=True, blank=True)
    numrical_let_grad = models.CharField(max_length=50, null=True, blank=True)
    let_grad_sub = models.CharField(max_length=20, null=True, blank=True)
    let_grad = models.CharField(max_length=50, null=True, blank=True)
    dsc_grad = models.CharField(max_length=50, null=True, blank=True)
    agreegate = models.CharField(max_length=100, null=True, blank=True)
    grade = models.CharField(max_length=100, null=True, blank=True)
    record_status = models.CharField(max_length=20, null=True, blank=True)
    final_sheet_status = models.CharField(max_length=20, null=True, blank=True)
    student_name_hindi = models.CharField(max_length=100, null=True, blank=True)
    max_total_mark = models.CharField(max_length=20, null=True, blank=True)
    
    # College relationship with colleges ap

    # Meta fields
    copied_from_staging = models.BooleanField(default=True, help_text="Copied from staging.PGResultCurrent")
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'PG Old Result'
        verbose_name_plural = 'PG Old Results'
        indexes = [
            models.Index(fields=['semester_code']),
            models.Index(fields=['batch_code']),
            models.Index(fields=['session_code']),
            models.Index(fields=['course_code']),
            models.Index(fields=['institute_code']),
        ]
        
    def __str__(self):
        return f"{self.uid} - {self.subject_name} - Batch {self.batch_code}"


class PGCenterInstituteMap(models.Model):
    """
    Model to store center_institute_map_purnea data from staging.
    This is a copy of center to institute mapping data for PG course.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Original table columns (all as CharField to match staging data exactly)
    source_id = models.CharField(max_length=50, null=True, blank=True, help_text='Original id from staging')
    center_code = models.CharField(max_length=255, null=True, blank=True)
    center_name = models.CharField(max_length=255, null=True, blank=True)
    batch_code = models.CharField(max_length=255, null=True, blank=True)
    course_code = models.CharField(max_length=255, null=True, blank=True)
    semester_code = models.CharField(max_length=255, null=True, blank=True)
    institute_code = models.CharField(max_length=255, null=True, blank=True)
    institute_name = models.CharField(max_length=255, null=True, blank=True)
    record_status = models.CharField(max_length=255, null=True, blank=True)
    exam_type = models.CharField(max_length=255, null=True, blank=True)
    session_code = models.CharField(max_length=255, null=True, blank=True)
    is_sem = models.CharField(max_length=255, null=True, blank=True)

    # Meta fields
    copied_from_staging = models.BooleanField(default=True, help_text="Copied from staging.CenterInstituteMapPurnea")
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'PG Center Institute Map'
        verbose_name_plural = 'PG Center Institute Maps'
        indexes = [
            models.Index(fields=['center_code']),
            models.Index(fields=['institute_code']),
            models.Index(fields=['course_code']),
            models.Index(fields=['batch_code']),
            models.Index(fields=['session_code']),
        ]
        
    def __str__(self):
        return f"{self.center_code} - {self.institute_code} - {self.course_code}"

class PGExamMasterDump(models.Model):
    """
    Model to store exam_master data from staging.ExamMasterDump.
    Only contains records where course_code = 'PG'.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Original staging columns (all CharField to match dump exactly)
    source_id = models.CharField(max_length=255, null=True, blank=True, help_text='Original id from staging ExamMasterDump')
    exam_type = models.CharField(max_length=255, null=True, blank=True)
    exam_code = models.CharField(max_length=255, null=True, blank=True)
    exam_name = models.CharField(max_length=500, null=True, blank=True)
    batch_code = models.CharField(max_length=255, null=True, blank=True)
    session_code = models.CharField(max_length=255, null=True, blank=True)
    course_code = models.CharField(max_length=255, null=True, blank=True, default='PG')
    discipline_code = models.CharField(max_length=255, null=True, blank=True)
    semester_code = models.CharField(max_length=255, null=True, blank=True)
    publish_all = models.CharField(max_length=255, null=True, blank=True)
    actual_exam_month = models.CharField(max_length=255, null=True, blank=True)
    year = models.CharField(max_length=255, null=True, blank=True)
    sl_no = models.CharField(max_length=255, null=True, blank=True)
    exam_month = models.CharField(max_length=255, null=True, blank=True)
    exam_year = models.CharField(max_length=255, null=True, blank=True)
    exam_start_date = models.CharField(max_length=255, null=True, blank=True)
    exam_end_date = models.CharField(max_length=255, null=True, blank=True)
    apply_start_date = models.CharField(max_length=255, null=True, blank=True)
    apply_end_date = models.CharField(max_length=255, null=True, blank=True)
    exam_mark_entry_date = models.CharField(max_length=255, null=True, blank=True)
    online_payment_transaction_no = models.CharField(max_length=255, null=True, blank=True)
    omr_no = models.CharField(max_length=255, null=True, blank=True)
    template_code = models.CharField(max_length=255, null=True, blank=True)
    publish_date = models.CharField(max_length=255, null=True, blank=True)
    institute_code = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_on = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    updated_on = models.CharField(max_length=255, null=True, blank=True)
    record_status = models.CharField(max_length=255, null=True, blank=True)
    last_updated = models.CharField(max_length=255, null=True, blank=True)
    is_sem = models.CharField(max_length=255, null=True, blank=True)

    # Meta fields
    copied_from_staging = models.BooleanField(default=True, help_text='Copied from staging.ExamMasterDump where course_code=PG')
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'PG Exam Master Dump'
        verbose_name_plural = 'PG Exam Master Dumps'
        indexes = [
            models.Index(fields=['exam_code']),
            models.Index(fields=['batch_code']),
            models.Index(fields=['session_code']),
            models.Index(fields=['semester_code']),
            models.Index(fields=['discipline_code']),
            models.Index(fields=['institute_code']),
        ]

    def __str__(self):
        return f"{self.exam_code} - {self.exam_name} ({self.batch_code})"

