from django.db import transaction
from django.utils import timezone
from ..models import NewRegistration

def generate_registration_number(instance, session=None, college=None):
    """
    Implementation of the Purnea University generation formula:
    XX(Session) + XX(College) + Code(U/P/V/B) + XXXXX(Serial)
    
    This function should be called within a transaction if possible, 
    but it handles its own atomic block for the serial number increment.
    """
    # 1. Determine the ingredients
    # If not provided, fallback to instance attributes
    # course_type is deprecated, we derive from course
    
    session = session or instance.session
    college = college or instance.college
    course = instance.course

    if not all([course, college]):
        raise ValueError("Course and College are required to generate a registration number.")

    # 2. SESSION CODE: Last two digits of the current year
    session_year = str(timezone.now().year)
    session_code = session_year[2:]

    # 3. COLLEGE CODE: Last two digits of OU ID (college_code)
    if not college.college_code:
        raise ValueError("College code is required to generate a registration number.")
    
    col_code = str(college.college_code)
    college_suffix = col_code[-2:] if len(col_code) >= 2 else col_code.zfill(2)

    # 4. COURSE CODE mapping
    # Logic: If course is B.Ed, use 'B', otherwise 'V' (Vocational)
    # We check course code or name
    if getattr(course, 'code', '').upper() == 'BED' or 'B.Ed' in getattr(course, 'name', ''):
        course_code = 'B'
    else:
        course_code = 'V'

    prefix = f"{session_code}{college_suffix}{course_code}"

    # 5. THREAD-SAFE GENERATION
    # We must lock a parent object (College) to ensure serial execution even if no registrations exist yet.
    # We must also SAVE the registration number before releasing the lock.
    with transaction.atomic():
        # Lock the College row to serialize generation for this college
        # This prevents two threads from both seeing "0 records" and creating 00001
        _ = college.__class__.objects.select_for_update().get(pk=college.pk)

        # Now safe to query max number for this prefix (college/course specific)
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
        
        # Generate GLOBAL sr_no (university-wide counter)
        # This is independent of college/course and tracks total registrations
        last_global_reg = NewRegistration.objects.filter(
            sr_no__isnull=False
        ).order_by('-sr_no').only('sr_no').first()
        
        if last_global_reg and last_global_reg.sr_no:
            global_sr_no = last_global_reg.sr_no + 1
        else:
            global_sr_no = 1
        
        # SAVE IMMEDIATELY to reserve this number before releasing lock
        instance.registration_number = final_number
        instance.sr_no = global_sr_no  # Global university-wide serial number
        instance.save(update_fields=['registration_number', 'sr_no'])
        
        return final_number
