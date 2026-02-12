from django.db import transaction
from django.utils import timezone
from ..models import NewRegistration

def generate_registration_number(instance, session=None, college=None):
    """
    Dispatcher for registration number generation based on course.
    Also handles non-migrated students by assigning their old_registration_no.
    """
    # 1. Handle Non-Migrated Students (Use old registration number)
    if not getattr(instance, 'migrated_from_other_university', True):
        old_no = getattr(instance, 'old_registration_no', None)
        if old_no:
            with transaction.atomic():
                # Just assign the global sr_no and save
                last_global_reg = NewRegistration.objects.filter(
                    sr_no__isnull=False
                ).order_by('-sr_no').only('sr_no').first()
                
                global_sr_no = (last_global_reg.sr_no + 1) if last_global_reg and last_global_reg.sr_no else 1
                
                instance.registration_number = old_no
                instance.sr_no = global_sr_no
                instance.save(update_fields=['registration_number', 'sr_no'])
                return old_no
        else:
            raise ValueError("Non-migrated student missing old_registration_no.")

    # 2. Handle Migrated Students (Generate new number)
    course = instance.course or getattr(instance, 'course', None)
    if not course:
        raise ValueError("Course is required to generate a registration number.")

    # Check if B.Ed
    if getattr(course, 'code', '').upper() == 'BED' or 'B.Ed' in getattr(course, 'name', ''):
        return generate_bed_registration_number(instance, session, college)
    else:
        return generate_vocational_registration_number(instance, session, college)


def generate_bed_registration_number(instance, session=None, college=None):
    """
    B.Ed Registration Number Pattern:
    XX(Session) + XX(College) + B + XXXXX(Serial)
    """
    session = session or instance.session
    college = college or instance.college
    course = instance.course

    if not all([course, college]):
        raise ValueError("Course and College are required for B.Ed registration number.")

    # 1. SESSION CODE: Last two digits of the current year
    session_year = str(timezone.now().year)
    session_code = session_year[2:]

    # 2. COLLEGE CODE: Last two digits of OU ID (college_code)
    if not college.college_code:
        raise ValueError("College code is required for B.Ed.")
    
    col_code = str(college.college_code)
    college_suffix = col_code[-2:] if len(col_code) >= 2 else col_code.zfill(2)

    # 3. COURSE CODE: B for B.Ed
    course_code = 'B'

    prefix = f"{session_code}{college_suffix}{course_code}"

    with transaction.atomic():
        college.__class__.objects.select_for_update().get(pk=college.pk)

        last_reg = NewRegistration.objects.filter(
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

        final_number = f"{prefix}{new_series:05d}"
        
        # Global sr_no increment
        last_global_reg = NewRegistration.objects.filter(
            sr_no__isnull=False
        ).order_by('-sr_no').only('sr_no').first()
        
        global_sr_no = (last_global_reg.sr_no + 1) if last_global_reg and last_global_reg.sr_no else 1
        
        instance.registration_number = final_number
        instance.sr_no = global_sr_no
        instance.save(update_fields=['registration_number', 'sr_no'])
        
        return final_number


def generate_vocational_registration_number(instance, session=None, college=None):
    """
    Vocational/Other Registration Number Pattern:
    XX(Batch Year) + CollegeCode + CourseCode(V1/V/etc) + XXXX(Serial)
    """
    session = session or instance.session
    college = college or instance.college
    course = instance.course
    batch = instance.batch

    if not all([course, college]):
        raise ValueError("Course and College are required for registration number.")

    # 1. YEAR CODE from Batch (e.g., 2025-2028 -> 25)
    if batch and batch.name and len(batch.name) >= 4:
        # e.g. "2025-2028" -> "25"
        year_code = batch.name[2:4]
    else:
        raise ValueError("Batch name is required to generate a registration number.")

    # 2. COLLEGE CODE
    col_code = str(college.college_code or "")
    if not col_code:
        raise ValueError("College code is required.")

    # 3. COURSE CODE Mapping
    # User requested BBA -> V1
    course_code_val = getattr(course, 'code', '').upper()
    if course_code_val == 'BBA':
        course_prefix = 'V1'
    elif course_code_val == 'CND':
        course_prefix = 'V2'
    elif course_code_val == 'BCA':
        course_prefix = 'V3'
    else:
        # Vocational default
        course_prefix = 'V'

    prefix = f"{year_code}{col_code}{course_prefix}"

    with transaction.atomic():
        # Lock college row
        college.__class__.objects.select_for_update().get(pk=college.pk)

        # Get last number for this specific prefix
        last_reg = NewRegistration.objects.filter(
            registration_number__startswith=prefix
        ).order_by('-registration_number').only('registration_number').first()

        if last_reg and last_reg.registration_number:
            try:
                # Extract the last 4 digits (0001, 0002...)
                last_series_str = last_reg.registration_number[-4:]
                new_series = int(last_series_str) + 1
            except (ValueError, IndexError):
                new_series = 1
        else:
            new_series = 1

        final_number = f"{prefix}{new_series:04d}"
        
        # Global sr_no increment
        last_global_reg = NewRegistration.objects.filter(
            sr_no__isnull=False
        ).order_by('-sr_no').only('sr_no').first()
        
        global_sr_no = (last_global_reg.sr_no + 1) if last_global_reg and last_global_reg.sr_no else 1
        
        instance.registration_number = final_number
        instance.sr_no = global_sr_no
        instance.save(update_fields=['registration_number', 'sr_no'])
        
        return final_number
