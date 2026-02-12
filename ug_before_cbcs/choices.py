from django.db import models

PART_CHOICES = [
    ('PART1', 'Part I'),
    ('PART2', 'Part II'),
    ('PART3', 'Part III'),
]

SUBJECT_TYPE_CHOICES = [
    ('HONOURS', 'Honours'),
    ('SUBSIDIARY', 'Subsidiary'),
    ('COMPOSITION', 'Composition'),
    ('GENERAL_STUDIES', 'General Studies'),
    ('GENERAL', 'General (for Pass Course)'),
]

RESULT_STATUS_CHOICES = [
    ('PASS', 'PASS'),
    ('PASS_WITH_HONS', 'PASS WITH HONS'),
    ('PROMOTED', 'PROMOTED'),
    ('FAIL', 'FAIL'),
    ('ABSENT', 'ABSENT'),
    ('PENDING', 'PENDING'),
    ('EXPELLED', 'EXPELLED'),
]

EXAM_TYPE_CHOICES = [
    ('REGULAR', 'Regular'),
    ('BACK', 'Back/Ex-Regular'),
    ('IMPROVEMENT', 'Improvement'),
]

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]
