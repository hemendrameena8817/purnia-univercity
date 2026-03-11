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
    """Individual course structure for LLB subjects (CIA and ESE separate)"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    full_marks = models.PositiveIntegerField(default=100)
    pass_marks = models.PositiveIntegerField(default=33)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class CommonCourseStructure(models.Model):
    """Combined course structure for LLB subjects (one entry per subject)"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, help_text="Subject Name (e.g., Constitutional Law-I)")
    course_code = models.CharField(max_length=100, help_text="Course Code")
    full_marks = models.PositiveIntegerField(help_text="Total Full Marks (CIA + ESE)")
    pass_marks = models.PositiveIntegerField(help_text="Total Pass Marks")
    cia_max_marks = models.PositiveIntegerField(help_text="CIA Maximum Marks")
    ese_max_marks = models.PositiveIntegerField(help_text="ESE Maximum Marks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.course_code})"

class LLBExam(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)        
    semester = models.CharField(max_length=20, null=True, blank=True, help_text="Semester Code from staging")
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

    total_marks = models.PositiveIntegerField(default=0)
    grace = models.PositiveIntegerField(null=True, blank=True)
    result_status = models.CharField(
        max_length=500,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.roll_no} - {self.exam.name}"

class LLBStudentCourseAssessment(models.Model):
    """
    Detailed marks per subject and assessment label for LLB (following MCA pattern).
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        LLBStudentProfile,
        on_delete=models.CASCADE,
        related_name='course_assessments'
    )
    course = models.ForeignKey(
        LLBCourse,
        on_delete=models.CASCADE,
        related_name='student_assessments_course',
        null=True,
        blank=True
    )
    course_structure = models.ForeignKey(
        LLBCourseStructure,
        on_delete=models.CASCADE,
        related_name='student_assessments_course_structure',
        null=True,
        blank=True
    )
    exam = models.ForeignKey(
        LLBExam, 
        on_delete=models.CASCADE, 
        related_name='student_assessments_exam',
        null=True, 
        blank=True
    )
    exam_result = models.ForeignKey(
        LLBStudentExamResult, 
        on_delete=models.CASCADE, 
        related_name='student_assessments_result',
        null=True, 
        blank=True
    )
    label = models.CharField(max_length=200, db_index=True, help_text="Assessment label (e.g., CIA, ESE, CIA-Theory)")
    semester = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="Semester of the assessment, e.g., '1', '2'")
    session = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Session")
    batch = models.ForeignKey(
        LLBBatch,
        on_delete=models.CASCADE,
        related_name='student_assessments',
        null=True,
        blank=True
    )
    college_code = models.CharField(max_length=10, null=True, blank=True, help_text="College Code")
    exam_type = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="Type Regular/Back")
    paper_code = models.CharField(max_length=20, null=True, blank=True, help_text="Paper Code for this assessment")

    #### Individual Marks ####
    ind_max_marks = models.IntegerField(null=True, blank=True, help_text="Individual MAX MARKS")
    ind_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual PASS MARKS")
    ind_is_absent = models.BooleanField(default=False, db_index=True, help_text="Is Absent")
    ind_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual MARKS OBTAINED")
    ind_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual GRACE MARKS OBTAINED")
    ind_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Individual FINAL MARKS OBTAINED")
    ind_is_pass = models.BooleanField(null=True, blank=True, help_text="Is Pass")

    #### Combined/Aggregated Marks ####
    comb_max_marks = models.IntegerField(null=True, blank=True, help_text="Combined MAX MARKS")
    comb_pass_marks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Combined PASS MARKS")
    comb_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Combined MARKS OBTAINED")
    comb_grace_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Combined GRACE MARKS OBTAINED")
    comb_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Combined FINAL MARKS OBTAINED")
    comb_is_pass = models.BooleanField(null=True, blank=True, help_text="Combined Is Pass")

    #### Course Summary ####
    course_max_marks = models.IntegerField(null=True, blank=True, help_text="Course Total MAX MARKS")
    course_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course Total MARKS OBTAINED")
    course_final_marks_obtained = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course Final MARKS OBTAINED")

    #### Result Status ####
    subject_result = models.CharField(max_length=10, null=True, blank=True, help_text="Subject Result (PASS/FAIL)")
    grade = models.CharField(max_length=30, null=True, blank=True, help_text="Grade")
    
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'LLB Student Assessment'
        verbose_name_plural = 'LLB Student Assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'course_structure'], name='idx_llb_stud_struct'),
            models.Index(fields=['batch', 'course_structure'], name='idx_llb_batch_struct'),
            models.Index(fields=['exam'], name='idx_llb_exam'),
        ]
        
    def save(self, *args, **kwargs):
        if self.ind_marks_obtained is not None and self.ind_max_marks is not None:
            if self.ind_marks_obtained > self.ind_max_marks:
                raise ValueError(f"Marks ({self.ind_marks_obtained}) > Max ({self.ind_max_marks})")
        
        # Calculate pass status including grace marks
        if self.ind_marks_obtained is not None and self.ind_pass_marks is not None:
            grace = self.ind_grace_obtained or 0
            total_for_pass = self.ind_marks_obtained + grace
            self.ind_is_pass = total_for_pass >= self.ind_pass_marks if not self.ind_is_absent else False
            
        super().save(*args, **kwargs)
        
    def __str__(self):
        sem = self.semester or 'N/A'
        return f"{self.student} | {sem} | {self.label}"

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