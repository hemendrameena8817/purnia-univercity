from rest_framework.permissions import BasePermission


class IsExamCenterUser(BasePermission):
    """
    Allows access only to college users whose college is registered
    as an EXAM CENTER in PGExamCenterMapping.

    This means:
    - college_user   ✅  (only if their college is a CENTER)
    - attached/regular college users  ❌
    - students, admins, others        ❌

    Used for center attendance APIs.
    """
    message = "Access denied. Only exam center college users can access this endpoint."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Must be a college user
        if getattr(request.user, 'user_type', None) != 'college_user':
            return False

        # Get the college linked to this user
        try:
            college = request.user.college_profile.college
        except AttributeError:
            return False

        # Check if this college is registered as a CENTER in any PGExamCenterMapping
        from pg.models import PGExamCenterMapping
        return PGExamCenterMapping.objects.filter(center=college).exists()
