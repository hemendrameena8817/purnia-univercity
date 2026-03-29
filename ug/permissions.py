from rest_framework.permissions import BasePermission


class IsExamCenterUser(BasePermission):
    """
    Allows access only to college users whose college is registered
    as an EXAM CENTER in UGExamCenterMapping.

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

        # Must be a college user and have a linked college
        if getattr(request.user, 'user_type', None) != 'college_user' or not request.user.college:
            return False

        # Check if this college is registered as a CENTER in any UGExamCenterMapping
        from .models import UGExamCenterMapping
        return UGExamCenterMapping.objects.filter(center=request.user.college).exists()
