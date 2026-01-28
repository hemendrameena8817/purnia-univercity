from django.db import transaction
from django.utils import timezone
from ..models import NewRegistration

def generate_registration_number(instance, course_type=None, session=None, college=None):
    """
    Implementation of the Purnea University generation formula:
    XX(Session) + XX(College) + Code(U/P/V/B) + XXXXX(Serial)
    
    This function should be called within a transaction if possible, 
    but it handles its own atomic block for the serial number increment.
    """
    # 1. Determine the ingredients
    # If not provided, fallback to instance attributes
    course_type = course_type or instance.course_type
    session = session or instance.session
    college = college or instance.college

    if not all([course_type, college]):
        raise ValueError("Course type and College are required to generate a registration number.")

    # 2. SESSION CODE: Last two digits of the current year
    session_year = str(timezone.now().year)
    session_code = session_year[2:]

    # 3. COLLEGE CODE: Last two digits of OU ID (college_code)
    if not college.college_code:
        raise ValueError("College code is required to generate a registration number.")
    
    col_code = str(college.college_code)
    college_suffix = col_code[-2:] if len(col_code) >= 2 else col_code.zfill(2)

    # 4. COURSE CODE mapping
    course_mapping = {
        'UG': 'U',
        'PG': 'P',
        'VOC': 'V',
        'BED': 'B'
    }
    course_code = course_mapping.get(course_type)
    if not course_code:
        raise ValueError(f"Invalid course type for generation: {course_type}")

    prefix = f"{session_code}{college_suffix}{course_code}"

    # 5. FIVE DIGIT SERIES: Thread-safe sequential count
    with transaction.atomic():
        # Select for update to block other threads from reading the same "last number"
        last_reg = NewRegistration.objects.select_for_update().filter(
            registration_number__startswith=prefix
        ).order_by('-registration_number').only('registration_number').first()

        if last_reg and last_reg.registration_number:
            try:
                # Extract the last 5 digits
                last_series = int(last_reg.registration_number[-5:])
                new_series = last_series + 1
            except (ValueError, IndexError):
                new_series = 1
        else:
            new_series = 1

        return f"{prefix}{new_series:05d}"
