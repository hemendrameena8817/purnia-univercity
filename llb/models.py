from django.db import models
import uuid
from pup_umis_backend.options import GENDER_CHOICES, CASTE_CHOICES


class LLBCourse(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)  
    duration_years = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

from django.conf import settings

class LLBSession(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=20)  # 2021-24
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class LLBBatch(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=50)  
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class LLBStudentProfile(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="llb_profile"
    )

    roll_no = models.CharField(max_length=20, unique=True)
    registration_no = models.CharField(max_length=30, unique=True)

    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)

    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.PROTECT,
        related_name='llb_students'
    )

    course = models.ForeignKey(
        LLBCourse,
        on_delete=models.PROTECT
    )

    batch = models.ForeignKey(
        LLBBatch,
        on_delete=models.PROTECT
    )

    hindi_name = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True) 
    aadhar_no = models.CharField(max_length=12, null=True, blank=True) 
    category = models.CharField(max_length=50, choices=CASTE_CHOICES, null=True, blank=True) 
    status = models.CharField(max_length=50, null=True, blank=True) 
    profile_image = models.ImageField(upload_to='llb/profiles/', null=True, blank=True)
    signature = models.ImageField(upload_to='llb/signatures/', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.roll_no} - {self.user.get_full_name()}"

class LLBCourseStructure(models.Model):
    """Common course structure for LLB subjects"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    full_marks = models.PositiveIntegerField(default=100)
    pass_marks = models.PositiveIntegerField(default=33)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class LLBExam(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)  
    semester = models.PositiveIntegerField(null=True, blank=True)         # 4
    session = models.CharField(max_length=20, null=True, blank=True)
    batch = models.ForeignKey(
        LLBBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )   
    exam_month_year = models.CharField(max_length=20) 
    publication_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class LLBStudentExamResult(models.Model):
    """Exam result summary for LLB students"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        LLBStudentProfile,
        on_delete=models.CASCADE,
        related_name='exam_results'
    )

    exam = models.ForeignKey(
        LLBExam,
        on_delete=models.CASCADE,
        related_name='exam_results'
    )
    
    exam_center = models.CharField(max_length=255, blank=True, null=True) # M L A College, Kasba

    total_marks = models.PositiveIntegerField(default=0)
    grace = models.PositiveIntegerField(null=True, blank=True)
    result_status = models.CharField(
        max_length=500,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.roll_no} - {self.exam.name}"


class LLBStudentAssessment(models.Model):
    """Simple assessment entry for backward compatibility"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam_result = models.ForeignKey(
        LLBStudentExamResult,
        on_delete=models.CASCADE,
        related_name='assessments',
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        LLBCourseStructure,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    paper_code = models.CharField(max_length=10, null=True, blank=True)
    marks_obtained = models.PositiveIntegerField(null=True, blank=True)
    total_secured_mark = models.PositiveIntegerField(null=True, blank=True)
    total_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=30, null=True, blank=True)
    subject_result = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        subject_name = self.subject.name if self.subject else "No Subject"
        return f"{subject_name} ({self.paper_code}) - {self.marks_obtained}"


class LLBStudentCourseAssessment(models.Model):
    """
    Semester-wise assessment + marks for a student course
    using flexible labels (CIA-Theory, ESE-Practical, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam_result = models.ForeignKey(LLBStudentExamResult, on_delete=models.PROTECT, null=True)
    course_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Name")
    course_short_name = models.CharField(max_length=250, null=True, blank=True, help_text="Course Short Name")
    student = models.ForeignKey(
        LLBStudentProfile,
        on_delete=models.CASCADE,
        related_name='llb_student_course_assessment'
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Course Type")
    course_code = models.CharField(max_length=100, null=True, blank=True, help_text="Course Code")
    paper_code = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Paper Code")

    semester = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Semester")
    label = models.CharField(max_length=100, db_index=True, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
    session = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Session")
    batch = models.ForeignKey(
        LLBBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    college_code = models.CharField(max_length=10, null=True, blank=True, help_text="College Code")
    exam_type = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Type Regular/Back")

    # Individual assessment fields
    ind_max_marks = models.IntegerField(null=True, blank=True, help_text="Individual MAX MARKS")
    ind_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual PASS MARKS")
    ind_is_absent = models.BooleanField(default=False, db_index=True, help_text="Is Absent")
    ind_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual MARKS OBTAINED")
    ind_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual GRACE MARKS OBTAINED")
    ind_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual FINAL MARKS OBTAINED")
    ind_is_pass = models.BooleanField(null=True, blank=True, help_text="Is Pass")

    # Combined fields
    comb_max_marks = models.IntegerField(null=True, blank=True, help_text="Total MAX MARKS")
    comb_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total PASS MARKS")
    comb_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total MARKS OBTAINED")
    comb_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total GRACE MARKS OBTAINED")
    comb_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total FINAL MARKS OBTAINED")
    comb_is_pass = models.BooleanField(null=True, blank=True, help_text="Is Pass")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.roll_no} - {self.course_name} ({self.label})"


class LLBExamCenterMapping(models.Model):
    """Maps exams to centers and attached colleges"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exams = models.ManyToManyField(LLBExam, related_name='center_mappings')
    center = models.ForeignKey('colleges.College', on_delete=models.CASCADE, related_name='llb_as_center_mappings')
    attached_colleges = models.ManyToManyField('colleges.College', related_name='llb_exam_centers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LLBExamSchedule(models.Model):
    """Exam routine/datesheet"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exam = models.ForeignKey(LLBExam, on_delete=models.CASCADE, related_name='schedules')
    subject = models.ForeignKey(LLBCourseStructure, on_delete=models.CASCADE, related_name='exam_schedules')
    exam_date = models.DateField(null=True, blank=True)
    exam_time = models.CharField(max_length=100, null=True, blank=True)
    sitting = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LLBYearRegistration(models.Model):
    """Year-wise student registration"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(LLBStudentProfile, on_delete=models.CASCADE, related_name='year_registrations')
    year = models.IntegerField(null=True, blank=True)
    session = models.CharField(max_length=20, null=True, blank=True)
    is_open = models.BooleanField(default=False)
    exam_eligible = models.BooleanField(default=False)
    status = models.CharField(max_length=20, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LLBExamRegistration(models.Model):
    """Exam registration for students"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(LLBStudentProfile, on_delete=models.CASCADE, related_name='exam_registrations')
    exam = models.ForeignKey(LLBExam, on_delete=models.CASCADE, related_name='registrations')
    exam_type = models.CharField(max_length=20, default='REGULAR')  # REGULAR, BACKLOG, IMPROVEMENT
    year = models.IntegerField(null=True, blank=True)
    fees = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)