"""
UG App - Choices and Enums

Centralized location for all Django model choices and enums.
"""

# Semester Result Status
SEMESTER_RESULT_CHOICES = (
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
    ('CIA-Theory', 'CIA Theory'),
    ('CIA-Practical', 'CIA Practical'),
    ('ESE-Theory', 'ESE Theory'),
    ('ESE-Practical', 'ESE Practical'),
)

# Promotion Status
PROMOTION_STATUS_CHOICES = (
    ('ELIGIBLE', 'Eligible'),
    ('NOT_ELIGIBLE', 'Not Eligible'),
)

# Semester Choices
SEMESTER_CHOICES = (
    ('1ST', '1st Semester'),
    ('2ND', '2nd Semester'),
    ('3RD', '3rd Semester'),
    ('4TH', '4th Semester'),
    ('5TH', '5th Semester'),
    ('6TH', '6th Semester'),
)

# Grade Choices (from official grading system)
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
