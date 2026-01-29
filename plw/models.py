from django.db import models


class PLWCourse(models.Model):
    name = models.CharField(max_length=255)  # Bachelor of Law (LL.B.)
    duration_years = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name

from django.conf import settings

class PLWSession(models.Model):
    name = models.CharField(max_length=20)  # 2021-24
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PLWBatch(models.Model):
    name = models.CharField(max_length=50)  # 2021 Admission
    admission_year = models.PositiveIntegerField()

    session = models.ForeignKey(
        PLWSession,
        on_delete=models.PROTECT,
        related_name='batches'
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.session.name})"

class PLWStudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="plw_profile"
    )

    roll_no = models.CharField(max_length=20, unique=True)
    registration_no = models.CharField(max_length=30, unique=True)

    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)

    college = models.ForeignKey(
        'colleges.College',
        on_delete=models.PROTECT,
        related_name='plw_students'
    )

    course = models.ForeignKey(
        PLWCourse,
        on_delete=models.PROTECT
    )

    batch = models.ForeignKey(
        PLWBatch,
        on_delete=models.PROTECT
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.roll_no} - {self.user.get_full_name()}"

class PLWSubject(models.Model):
    name = models.CharField(max_length=255)  # English-I, Political Science-I
    paper_code = models.CharField(max_length=10)  # I, II, III
    full_marks = models.PositiveIntegerField(default=100)
    pass_marks = models.PositiveIntegerField(default=33)

    def __str__(self):
        return f"{self.name} ({self.paper_code})"


class PLWExam(models.Model):
    name = models.CharField(max_length=255)  
    session = models.CharField(max_length=20)  # 2021-24
    exam_month_year = models.CharField(max_length=20)  # July 2022
    publication_date = models.DateField()

    def __str__(self):
        return self.name

class PLWResult(models.Model):
    student = models.ForeignKey(
        PLWStudentProfile,
        on_delete=models.CASCADE,
        related_name='results'
    )

    exam = models.ForeignKey(
        PLWExam,
        on_delete=models.CASCADE,
        related_name='results'
    )
    
    exam_center = models.CharField(max_length=255, blank=True, null=True) # M L A College, Kasba

    total_marks = models.PositiveIntegerField(default=0)
    result_status = models.CharField(
        max_length=500,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.roll_no} - {self.exam.name}"


class PLWResultDetail(models.Model):
    result = models.ForeignKey(
        PLWResult,
        on_delete=models.CASCADE,
        related_name='details',
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        PLWSubject,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    marks_obtained = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        subject_name = self.subject.name if self.subject else "No Subject"
        return f"{subject_name} - {self.marks_obtained}"
