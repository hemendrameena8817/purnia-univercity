"""
BTech App - Choices and Enums
"""

# Year Result Status
YEAR_RESULT_CHOICES = (
    ('PASS', 'Pass'),
    ('PROMOTED', 'Promoted'),
    ('FAIL', 'Fail'),
    ('ABSENT', 'Absent'),
    ('QUALIFIED', 'Qualified'),
    ('DISQUALIFIED', 'Disqualified'),
    ('PARTLY_QUALIFIED', 'Partly Qualified'),
)

# Student Status
STUDENT_STATUS_CHOICES = (
    ('REGULAR', 'Regular'),
    ('SUSPENDED', 'Suspended'),
    ('ALUMNI', 'Alumni'),
)

# Gender Choices
GENDER_CHOICES = (
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
)

# Exam Type
EXAM_TYPE_CHOICES = (
    ('REGULAR', 'Regular'),
    ('BACK', 'Back'),
    ('IMPROVEMENT', 'Improvement'),
)

# Assessment Labels (Standardized)
ASSESSMENT_LABEL_CHOICES = (
    ('THEORY', 'Theory'),
    ('PERIODICAL', 'Periodical Exam'),
    ('SESSIONAL', 'Sessional'),
    ('PRACTICAL', 'Practical'),
    ('PROJECT', 'Project'),
    ('SEMINAR', 'Seminar'),
)

# Promotion Status
PROMOTION_STATUS_CHOICES = (
    ('ELIGIBLE', 'Eligible'),
    ('NOT_ELIGIBLE', 'Not Eligible'),
)

# Grade Choices
GRADE_CHOICES = (
    ('O', 'Outstanding (10)'),
    ('A+', 'Excellent (9)'),
    ('A', 'Very Good (8)'),
    ('B+', 'Good (7)'),
    ('B', 'Above Average (6)'),
    ('C', 'Average (5)'),
    ('P', 'Pass (4)'),
    ('F', 'Fail (0)'),
    ('Ab', 'Absent (0)'),
)
