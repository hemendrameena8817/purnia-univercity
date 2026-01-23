import uuid
from django.db import models

class PGCourseStructure(models.Model):
    """
    Represents the course structure for a program.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True, help_text="Course Name")
    department = models.ForeignKey(
        'university.Department',
        on_delete=models.CASCADE,
        related_name='pg_course_structures'
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type")
    code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    max_credit = models.IntegerField(null=True, blank=True, help_text="Course Credit")
    max_marks = models.IntegerField(null=True, blank=True, help_text="Course Marks")

    min_mark = models.IntegerField(null=True, blank=True, help_text="Pass Mark")
    min_credit = models.IntegerField(null=True, blank=True, help_text="Min Credit")


    description = models.TextField(null=True, blank=True, help_text="Course Description")
    label = models.CharField(max_length=100, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")
   
    semester = models.IntegerField(null=True, blank=True, help_text="Semester")
    json_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Course Structure'
        verbose_name_plural = 'Course Structures'

    def __str__(self):
        return f"{self.department.name} - {self.course_type}"


class PGStudentCourseAssessment(models.Model):
    """
    Semester-wise assessment + marks for a student course
    using flexible labels (CIA-Theory, ESE-Practical, etc.)
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='pg_course_assessments'
    )
    course_type = models.CharField(max_length=20, null=True, blank=True, help_text="Course Type")
    code = models.CharField(max_length=20, null=True, blank=True, help_text="Course Code")
    semester = models.IntegerField(null=True, blank=True, help_text="Semester")

    max_credit = models.IntegerField(null=True, blank=True, help_text="Course Credit")
    max_marks = models.IntegerField(null=True, blank=True, help_text="Course Marks")

    min_mark = models.IntegerField(null=True, blank=True, help_text="Min Mark")
    min_credit = models.IntegerField(null=True, blank=True, help_text="Min Credit")

    description = models.TextField(null=True, blank=True, help_text="Course Description")
    label = models.CharField(max_length=100, help_text="Assessment label (e.g. CIA-Theory, ESE-Practical)")

    marks_obtained = models.IntegerField(null=True, blank=True, help_text="Marks Obtained")
    credit_obtained = models.IntegerField(null=True, blank=True, help_text="Credit Obtained")

    grade = models.CharField(max_length=10, null=True, blank=True, help_text="Grade")
    numeric_grade = models.IntegerField(null=True, blank=True, help_text="Numeric Grade")

    is_absent = models.BooleanField(default=False, help_text="Is Absent")
    exam_type = models.CharField(max_length=10, null=True, blank=True, help_text="Type Regular/Back")

    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    exam_result = models.CharField(max_length=10, null=True, blank=True, help_text="Status pass/fail/promoted")

    batch = models.CharField(max_length=10, null=True, blank=True, help_text="Batch")
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Student Course Assessment'
        verbose_name_plural = 'Student Course Assessments'

    def __str__(self):
        return f"{self.student} | Sem {self.semester} | {self.label}"


class PGSemesterRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='pg_semester_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True, help_text="Start Date")
    end_date = models.DateTimeField(null=True, blank=True, help_text="End Date")
    is_open = models.BooleanField(default=False, help_text="Is Open")
    sem = models.IntegerField(null=True, blank=True, help_text="Semester")
    status = models.CharField(max_length=10, null=True, blank=True, help_text="Status open/closed")
    exam_eligible = models.BooleanField(default=False, help_text="Eligible for Exam")
    remarks = models.TextField(null=True, blank=True, help_text="Remarks")
    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Semester Registration'
        verbose_name_plural = 'Semester Registrations'

    def __str__(self):
        return f"{self.student}"


class PGExamRegistration(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='pg_exam_registrations'
    )
    start_date = models.DateTimeField(null=True, blank=True, help_text="Start Date")
    end_date = models.DateTimeField(null=True, blank=True, help_text="End Date")
    is_open = models.BooleanField(default=False, help_text="Is Open")
    fees = models.IntegerField(null=True, blank=True, help_text="Fees")
    sem = models.IntegerField(null=True, blank=True, help_text="Semester")
    status = models.CharField(max_length=10, null=True, blank=True, help_text="Status")
    session = models.CharField(max_length=10, null=True, blank=True, help_text="Session")
    json_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Exam Registration'
        verbose_name_plural = 'Exam Registrations'

    def __str__(self):
        return f"{self.student}"
