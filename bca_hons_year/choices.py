"""
BCA Hons Year App - Choices and Enums
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
    ('Active', 'Active'),
    ('Suspended', 'Suspended'),
    ('Alumni', 'Alumni'),
    ('Regular','Regular')
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
    ('PRACTICAL', 'Practical'),
    ('SESSIONAL', 'Sessional'),
    ('VIVA', 'Viva'),
    ('CIA', 'CIA'),
    ('ESE', 'ESE'),
    ('ESE 2', 'ESE 2'),
)

# Promotion Status
PROMOTION_STATUS_CHOICES = (
    ('ELIGIBLE', 'Eligible'),
    ('NOT_ELIGIBLE', 'Not Eligible'),
)

# Grade Choices
GRADE_CHOICES = (
    ('I', 'First Division'),
    ('II', 'Second Division'),
    ('III', 'Third Division'),
    ('F', 'Fail'),
    ('Ab', 'Absent'),
)

PAPER_TYPE_CHOICES = (
    ('HONOURS', 'Honours'),
    ('SUBSIDIARY', 'Subsidiary'),
)