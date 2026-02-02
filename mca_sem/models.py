from django.db import models
import uuid
from django.conf import settings

class MCACourse(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)  
    duration_years = models.PositiveIntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class MCASession(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=20)  # 2021-23
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class MCABatch(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=50)  # 2021 Admission
    admission_year = models.PositiveIntegerField()

    session = models.ForeignKey(
        MCASession,
        on_delete=models.PROTECT,
        related_name='batches'
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.session.name})"

class MCAStudentProfile(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mca_profile"
    )

    roll_no = models.CharField(max_length=20, unique=True)
    registration_no = models.CharField(max_length=30, unique=True)

    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)

    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.PROTECT,
        related_name='mca_students'
    )

    course = models.ForeignKey(
        MCACourse,
        on_delete=models.PROTECT
    )

    batch = models.ForeignKey(
        MCABatch,
        on_delete=models.PROTECT
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.roll_no} - {self.user.get_full_name() if self.user else 'No User'}"

class MCASubject(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)  
    paper_code = models.CharField(max_length=10)  
    full_marks = models.PositiveIntegerField(default=100)
    pass_marks = models.PositiveIntegerField(default=33)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.paper_code})"

class MCAExam(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)  
    session = models.CharField(max_length=20)  # 2021-23
    exam_month_year = models.CharField(max_length=20)  # July 2022
    publication_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class MCAResult(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        MCAStudentProfile,
        on_delete=models.CASCADE,
        related_name='results'
    )

    exam = models.ForeignKey(
        MCAExam,
        on_delete=models.CASCADE,
        related_name='results'
    )
    
    exam_center = models.CharField(max_length=255, blank=True, null=True) 

    total_marks = models.PositiveIntegerField(default=0)
    grace = models.PositiveIntegerField(null=True, blank=True)
    result_status = models.CharField(
        max_length=500,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.roll_no} - {self.exam.name}"

class MCAResultDetail(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    result = models.ForeignKey(
        MCAResult,
        on_delete=models.CASCADE,
        related_name='details',
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        MCASubject,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    marks_obtained = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        subject_name = self.subject.name if self.subject else "No Subject"
        return f"{subject_name} - {self.marks_obtained}"
