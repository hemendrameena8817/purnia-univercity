from django.core.exceptions import ValidationError
from ug.models import UGStudentProfile
from pg.models import PGStudentProfile
from colleges.models import College

def verify_student_college_profile(user, college_uid, active_profile):
    """
    Verify if the user has a valid profile for the specified college based on active_profile.
    
    Args:
        user: UserAccount instance
        college_uid: UID of the college
        active_profile: Current active profile type ('ug_profile', 'pg_profile', etc.)
        
    Returns:
        The college instance if verification is successful.
        
    Raises:
        ValidationError if verification fails.
    """
    try:
        college = College.objects.get(uid=college_uid)
    except College.DoesNotExist:
        raise ValidationError("Invalid college UID.")

    if active_profile == 'ug_profile':
        try:
            profile = UGStudentProfile.objects.get(user=user)
            if profile.college != college:
                raise ValidationError("You are not registered in this college for UG course.")
        except UGStudentProfile.DoesNotExist:
            raise ValidationError("UG Student profile not found for this user.")
            
    elif active_profile == 'pg_profile':
        try:
            profile = PGStudentProfile.objects.get(user=user)
            if profile.college != college:
                raise ValidationError("You are not registered in this college for PG course.")
        except PGStudentProfile.DoesNotExist:
            raise ValidationError("PG Student profile not found for this user.")
    
    else:
        # If other profiles are added later, handle them here or raise generic error
        raise ValidationError(f"Unsupported profile type: {active_profile}")

    return college
