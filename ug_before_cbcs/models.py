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

# 1. Master Structure Models

class UGBeforeCBCSCourse(models.Model):
    """Represents a Degree like B.A. (Hons.), B.Sc. (Hons.), B.Com. (Hons.) etc."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255) # Bachelor of Arts (Hons.)
    course_code = models.CharField(max_length=50, null=True, blank=True) # BA, BSC
    duration_years = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UGBeforeCBCSDiscipline(models.Model):
    """Represents an Honours/General subject like Political Science, Physics, etc."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    course = models.ForeignKey(UGBeforeCBCSCourse, on_delete=models.CASCADE, related_name='disciplines')
    name = models.CharField(max_length=255) # Political Science
    code = models.CharField(max_length=50, null=True, blank=True) # PSY, HIN
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Before CBCS Discipline'
        verbose_name_plural = 'UG Before CBCS Disciplines'

    def __str__(self):
        return f"{self.name} ({self.course.course_code})"

class UGBeforeCBCSSession(models.Model):
    """Academic Session (e.g., 2021-24)"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=50) # 2021-24
    start_year = models.PositiveIntegerField(null=True, blank=True)
    end_year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UGBeforeCBCSBatch(models.Model):
    """Represents a specific batch of students."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255) # Batch 2021
    session = models.ForeignKey(UGBeforeCBCSSession, on_delete=models.CASCADE, related_name='batches')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# 2. Subject & Structure Models

class UGBeforeCBCSSubject(models.Model):
    """Master list of all papers/subjects."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255) # History, Paper-I, Geography Practical
    code = models.CharField(max_length=100, null=True, blank=True) # BA301
    paper_number = models.CharField(max_length=50, null=True, blank=True) # Paper-I, Paper-II
    subject_type = models.CharField(max_length=20, choices=SUBJECT_TYPE_CHOICES, null=True, blank=True)
    has_practical = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class UGBeforeCBCSCourseStructure(models.Model):
    """Links Discipline + Part to specific Subjects/Papers."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    discipline = models.ForeignKey(UGBeforeCBCSDiscipline, on_delete=models.CASCADE, related_name='structures')
    part = models.CharField(max_length=10, choices=PART_CHOICES)
    subject = models.ForeignKey(UGBeforeCBCSSubject, on_delete=models.CASCADE)
    subject_type = models.CharField(max_length=20, choices=SUBJECT_TYPE_CHOICES)
    
    # Marks configuration for this subject in this part
    theory_max_marks = models.IntegerField(default=100)
    theory_pass_marks = models.IntegerField(default=33)
    practical_max_marks = models.IntegerField(default=0)
    practical_pass_marks = models.IntegerField(default=0)
    aggregate_pass_marks = models.IntegerField(default=33)

    class Meta:
        verbose_name = 'UG Before CBCS Course Structure'
        verbose_name_plural = 'UG Before CBCS Course Structures'
        unique_together = ('discipline', 'part', 'subject')

    def __str__(self):
        return f"{self.discipline.name} - {self.part} - {self.subject.name}"

# 3. Student Profile

class UGBeforeCBCSStudentProfile(models.Model):
    """Student profile for Non-CBCS UG students."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        'accounts.UserAccount',
        on_delete=models.CASCADE,
        related_name='ug_before_cbcs_profile'
    )
    # Registration & Identity
    registration_no = models.CharField(max_length=100, unique=True)
    roll_no = models.CharField(max_length=100, null=True, blank=True)
    student_name = models.CharField(max_length=255)
    student_name_hindi = models.CharField(max_length=255, null=True, blank=True)
    fathers_name = models.CharField(max_length=255, null=True, blank=True)
    mothers_name = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    
    # Academic Association
    college = models.ForeignKey('colleges.College', on_delete=models.SET_NULL, null=True, related_name='ug_before_cbcs_students')
    course = models.ForeignKey(UGBeforeCBCSCourse, on_delete=models.SET_NULL, null=True)
    discipline = models.ForeignKey(UGBeforeCBCSDiscipline, on_delete=models.SET_NULL, null=True)
    batch = models.ForeignKey(UGBeforeCBCSBatch, on_delete=models.SET_NULL, null=True)
    session = models.ForeignKey(UGBeforeCBCSSession, on_delete=models.SET_NULL, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.registration_no} - {self.student_name}"

# 4. Exam & Assessment Models

class UGBeforeCBCSExam(models.Model):
    """Represents a specific Examination event."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255) # Bachelor of Arts (Hons.) Part-I Examination 2022
    part = models.CharField(max_length=10, choices=PART_CHOICES)
    exam_year = models.PositiveIntegerField() # 2022
    exam_month_year = models.CharField(max_length=100, null=True, blank=True) # JANUARY 2023
    publication_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.exam_year})"

class UGBeforeCBCSExamRegistration(models.Model):
    """Student's registration for a specific exam."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(UGBeforeCBCSStudentProfile, on_delete=models.CASCADE, related_name='exam_registrations')
    exam = models.ForeignKey(UGBeforeCBCSExam, on_delete=models.CASCADE, related_name='registrations')
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='REGULAR')
    college_at_exam = models.ForeignKey('colleges.College', on_delete=models.SET_NULL, null=True, related_name='ug_before_cbcs_exam_registrations')
    center = models.ForeignKey('colleges.College', on_delete=models.SET_NULL, null=True, related_name='ug_before_cbcs_exam_centers')
    
    # Registration details
    is_ex_regular = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, default='PENDING') 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.registration_no} - {self.exam.name}"

class UGBeforeCBCSStudentAssessment(models.Model):
    """Detailed marks per paper."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    registration = models.ForeignKey(UGBeforeCBCSExamRegistration, on_delete=models.CASCADE, related_name='assessments')
    subject = models.ForeignKey(UGBeforeCBCSSubject, on_delete=models.CASCADE)
    subject_type = models.CharField(max_length=20, choices=SUBJECT_TYPE_CHOICES)
    
    # Marks Obtained from Staging
    theory_marks = models.CharField(max_length=50, null=True, blank=True) # CharField to handle strings like 'ABS'
    practical_marks = models.CharField(max_length=50, null=True, blank=True)
    sessional_marks = models.CharField(max_length=50, null=True, blank=True)
    
    marks_secured = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_marks = models.IntegerField(null=True, blank=True)
    pass_marks = models.IntegerField(null=True, blank=True)
    
    # Capture the aggregated total if provided in staging
    subject_total_mark = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    is_absent = models.BooleanField(default=False)
    subject_result = models.CharField(max_length=50, null=True, blank=True) # PASS, FAIL
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Before CBCS Student Assessment'
        verbose_name_plural = 'UG Before CBCS Student Assessments'

    def __str__(self):
        return f"{self.registration.student.student_name} - {self.subject.name}"

class UGBeforeCBCSExamResult(models.Model):
    """Final summary result for a student in Part I, II, or III."""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    registration = models.OneToOneField(UGBeforeCBCSExamRegistration, on_delete=models.CASCADE, related_name='result_summary')
    
    grand_total_max = models.IntegerField(null=True, blank=True)
    grand_total_secured = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Specific fields for marksheets
    hons_total_max = models.IntegerField(null=True, blank=True)
    hons_total_secured = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    result_status = models.CharField(max_length=100, choices=RESULT_STATUS_CHOICES, null=True, blank=True)
    final_result_text = models.CharField(max_length=255, null=True, blank=True) # e.g., "PASS WITH HONS"
    
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'UG Before CBCS Exam Result'
        verbose_name_plural = 'UG Before CBCS Exam Results'

    def __str__(self):
        return f"{self.registration.student.student_name} - {self.result_status}"
