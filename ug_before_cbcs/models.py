from django.db import models
import uuid
from django.conf import settings
from .choices import (
    PART_CHOICES,
    SUBJECT_TYPE_CHOICES,
    RESULT_STATUS_CHOICES,
    EXAM_TYPE_CHOICES,
    GENDER_CHOICES,
)

# ============================================================================
# SIMPLIFIED UG BEFORE CBCS MODELS - COVERS ALL STAGING COLUMNS
# ============================================================================
# This is a SUPER SIMPLIFIED structure for historical/legacy UG (Non-CBCS) data.
# Only 3 tables: StudentProfile, Exam, and StudentResult
# NO separate tables for Subject, Course, Discipline, Batch, Session, ExamSummary
# All data from staging.UGResultCurrent is preserved in StudentResult table.
# ============================================================================


class UGBeforeCBCSStudentProfile(models.Model):
    """
    Student Profile - ONE record per student.
    Links to existing UserAccount and College.
    Stores basic student identity and academic association.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='ug_before_cbcs_profile'
    )
    
    # Identity (from staging)
    registration_no = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text='College Registration Number (college_reg_no from staging)'
    )
    roll_no = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='College Roll Number (college_roll_no from staging)'
    )
    student_name = models.CharField(max_length=255)
    student_name_hindi = models.CharField(max_length=255, null=True, blank=True)
    fathers_name = models.CharField(max_length=255, null=True, blank=True)
    mothers_name = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    
    # Academic Association (stored as codes, no FK to separate tables)
    college = models.ForeignKey(
        'colleges.College', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='ug_before_cbcs_students'
    )
    course_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Course code: BA, BSC, BCOM, etc.'
    )
    discipline_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Discipline code: PSY, HIN, PHY, etc.'
    )
    
    # Original staging IDs (for reference)
    source_user_id = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        help_text='Original user_id from staging'
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'UG Before CBCS Student Profile'
        verbose_name_plural = 'UG Before CBCS Student Profiles'
        indexes = [
            models.Index(fields=['registration_no']),
            models.Index(fields=['roll_no']),
            models.Index(fields=['college', 'course_code']),
        ]
    
    def __str__(self):
        return f"{self.registration_no} - {self.student_name}"





class UGBeforeCBCSExam(models.Model):
    """
    Exam Event - Represents a specific examination.
    Includes batch, session, part, year (NO separate tables).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Exam Identity
    name = models.CharField(
        max_length=255,
        help_text='Exam name: e.g., B.A. (Hons.) Part-I Exam 2022'
    )
    exam_code = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text='Unique exam identifier (auto-generated from batch+session+part)'
    )
    
    # Part & Year (NO separate tables)
    part = models.CharField(
        max_length=10, 
        choices=PART_CHOICES,
        help_text='Part: PART1, PART2, PART3'
    )
    semester_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Semester code from staging: 1ST, 2ND, 3RD'
    )
    exam_year = models.PositiveIntegerField(
        help_text='Exam year: 2022, 2023, etc.'
    )
    exam_month_year = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='Exam month and year: JANUARY 2023'
    )
    
    # Session & Batch (stored as strings, NO separate tables)
    session_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Session code from staging: 2021-24'
    )
    batch_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Batch code from staging: 2021'
    )
    
    # Course/Discipline (stored as codes)
    course_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Course code: BA, BSC, BCOM'
    )
    discipline_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Discipline code: PSY, HIN, PHY'
    )

    centre_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Examination centre name'
    )
    
    # Publication
    publication_date = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'UG Before CBCS Exam'
        verbose_name_plural = 'UG Before CBCS Exams'
        indexes = [
            models.Index(fields=['exam_code']),
            models.Index(fields=['part', 'exam_year']),
            models.Index(fields=['batch_code', 'session_code']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.exam_year})"


class UGBeforeCBCSStudentResult(models.Model):
    """
    Student's Result - ONE record per student per subject per exam.
    Stores ALL 42 columns from staging.UGResultCurrent.
    Includes subject details, marks, and summary data.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Relationships
    student = models.ForeignKey(
        UGBeforeCBCSStudentProfile, 
        on_delete=models.CASCADE, 
        related_name='results'
    )
    exam = models.ForeignKey(
        UGBeforeCBCSExam, 
        on_delete=models.CASCADE, 
        related_name='results'
    )
    
    # ========== SUBJECT DETAILS (No separate Subject table) ==========
    paper_code = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Paper code from staging'
    )
    subject_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Subject code from staging'
    )
    subject_name = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Full subject/paper name'
    )
    temp_paper_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Temporary paper code from staging'
    )
    paper_code_correction = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='Paper code correction from staging'
    )
    subject_code_correction = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='Subject code correction from staging'
    )
    paper_type_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Paper type code from staging (HONS, SUB, etc.)'
    )
    
    # Exam Type & Status
    exam_type = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Exam type: REGULAR, BACK, IMPROVEMENT'
    )
    exam_type_his = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Exam type history from staging'
    )
    is_ex_regular = models.BooleanField(
        default=False,
        help_text='Is Ex-Regular student (from ExRegular_chk)'
    )
    status = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Status from staging'
    )
    
    # Marks (CharField to handle 'ABS', 'UFM', etc.)
    theory = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Theory marks (can be numeric or ABS, UFM, etc.)'
    )
    practical = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Practical marks (pra from staging)'
    )
    sessional = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Sessional marks'
    )
    
    # Calculated/Secured Marks
    mark_secured = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Marks secured (can be numeric or text)'
    )
    mark_secured_history = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Mark secured history from staging'
    )
    subject_total_mark = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Subject total mark'
    )
    maximum_mark = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Maximum marks for this subject'
    )
    pass_mark = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Pass marks for this subject'
    )
    
    # Subject Results (ALL variants from staging)
    subject_result = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Subject result: PASS, FAIL, etc.'
    )
    subject_result_1 = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Subject result variant 1 from staging'
    )
    subject_result_2 = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Subject result variant 2 from staging'
    )
    sub_reult_com = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Subject result combined from staging'
    )
    
    # Additional Fields
    is_absent = models.BooleanField(default=False)
    grace_chk = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Grace marks check from staging'
    )
    remark = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Remarks from staging'
    )
    student_check = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Student check flag from staging'
    )
    
    # ========== EXAM SUMMARY DATA (No separate ExamSummary table) ==========
    # These fields store aggregated data per student per exam
    grand_total_mark = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Grand total maximum marks'
    )
    total_secured_mark = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Total secured marks'
    )
    total_secured_mark_1 = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Total secured marks variant 1 from staging'
    )
    total_secured_mark_2 = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Total secured marks variant 2 from staging'
    )
    hon = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Honours indicator/total from staging'
    )
    total_per = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Total percentage from staging'
    )
    grade = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Grade from staging'
    )
    final_result = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='Final result: PASS, FAIL, PASS WITH HONS, etc.'
    )
    agreegate = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text='Aggregate/Division (typo from staging preserved)'
    )
    aggregate_hindi = models.TextField(
        null=True, 
        blank=True,
        help_text='Aggregate in Hindi from staging'
    )
    record_status = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Record status from staging'
    )
    record_status_check = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Record status check from staging'
    )
    subject_count = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Subject count from staging'
    )
    
    # Source tracking
    source_id = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        help_text='Original id from staging'
    )
    
    # For tracking which student profile this belongs to (denormalized for faster queries)
    
    # Center Institute Mapping fields from center_institute_map_purnea (filtered by course_code=PG)
    center_code = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Center code from center_institute_map_purnea'
    )
    center_name = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Center name from center_institute_map_purnea'
    )
    center_institute_batch_code = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Batch code from center_institute_map_purnea'
    )
    center_institute_course_code = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Course code from center_institute_map_purnea (e.g., PG)'
    )
    center_institute_semester_code = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Semester code from center_institute_map_purnea'
    )
    center_institute_institute_code = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Institute code from center_institute_map_purnea'
    )
    center_institute_institute_name = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Institute name from center_institute_map_purnea'
    )
    center_institute_record_status = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Record status from center_institute_map_purnea'
    )
    center_institute_exam_type = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Exam type from center_institute_map_purnea'
    )
    center_institute_session_code = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Session code from center_institute_map_purnea'
    )
    center_institute_is_sem = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Is semester flag from center_institute_map_purnea'
    )
    registration_no = models.CharField(
        max_length=100,
        db_index=True,
        null=True,
        blank=True,
        help_text='Denormalized registration number for faster lookups'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'UG Before CBCS Student Result'
        verbose_name_plural = 'UG Before CBCS Student Results'
        indexes = [
            models.Index(fields=['student', 'exam']),
            models.Index(fields=['exam', 'paper_code']),
            models.Index(fields=['registration_no', 'paper_code']),
            models.Index(fields=['paper_code']),
        ]
    
    def __str__(self):
        return f"{self.student.student_name} - {self.subject_name} - {self.exam.name}"


class UGBeforeCBCSExamCenterMapping(models.Model):
    """
    Maps an Exam to a specific Examination Center for a particular Student's College.
    One exam can have different centers for different colleges.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(
        UGBeforeCBCSExam, 
        on_delete=models.CASCADE, 
        related_name='center_mappings'
    )
    student_college = models.ForeignKey(
        'colleges.College', 
        on_delete=models.CASCADE, 
        related_name='ug_before_cbcs_student_center_mappings'
    )
    center_college = models.ForeignKey(
        'colleges.College', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ug_before_cbcs_as_center_mappings',
        help_text='The college that acts as the examination center'
    )
    center_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Fallback center name if center_college is not set'
    )
    center_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Optional center code'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Before CBCS Exam Center Mapping'
        verbose_name_plural = 'UG Before CBCS Exam Center Mappings'
        unique_together = ('exam', 'student_college')

    def __str__(self):
        center_str = self.center_college.name if self.center_college else self.center_name
        return f"{self.exam.name} - {self.student_college.name} -> {center_str}"


class UGBeforeCBCSStatistics(models.Model):
    """
    Stores pre-calculated statistical overview data to avoid
    heavy database queries on every dashboard load.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    data = models.JSONField(help_text='The statistics JSON structure', null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Before CBCS Statistics'
        verbose_name_plural = 'UG Before CBCS Statistics'

    def __str__(self):
        return f"UG Before CBCS Stats - {self.last_updated.strftime('%Y-%m-%d %H:%M')}"
