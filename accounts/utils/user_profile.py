from ug.models import UGStudentProfile
from pg.models import PGStudentProfile

def get_ug_profile_data(user):
    """
    Get serialized UG student profile for a user.
    """
    if user.user_type != 'student':
        return None
    try:
        from ug.serializers import UGStudentProfileSerializer
        profile = UGStudentProfile.objects.select_related(
            'college', 'department', 'degree', 'program'
        ).filter(user=user).first()
        if profile:
            return UGStudentProfileSerializer(profile).data
    except Exception:
        pass
    return None

def get_pg_profile_data(user):
    """
    Get serialized PG student profile for a user.
    """
    if user.user_type != 'student':
        return None
    try:
        from pg.serializers import PGStudentProfileSerializer
        profile = PGStudentProfile.objects.select_related(
            'college', 'department', 'degree', 'program'
        ).filter(user=user).first()
        if profile:
            return PGStudentProfileSerializer(profile).data
    except Exception:
        pass
    return None

def get_current_profile(user):
    """
    Determine the current course profile based on status.
    Uses O(1) property access on OneToOne relations.
    """
    if user.user_type != 'student':
        return None
    
    ug_status = None
    pg_status = None
    
    # Use direct OneToOne relations (O(1))
    # If the user object was fetched with select_related, this is 0 additional queries
    if hasattr(user, 'ug_student_profile'):
        ug_status = user.ug_student_profile.is_active
        
    if hasattr(user, 'pg_student_profile'):
        pg_status = user.pg_student_profile.is_active
    
    # Priority: PG Active > UG Active > Alumni
    if pg_status:
        return 'pg_profile'
    if ug_status:
        return 'ug_profile'
    if pg_status == 'Alumni' or ug_status == 'Alumni':
        return 'alumni'
    if pg_status or ug_status:
        return 'inactive'
    
    return None
