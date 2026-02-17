"""
Custom permissions for role-based access control.
"""
from rest_framework import permissions


class IsUniversityAdmin(permissions.BasePermission):
    """
    Permission for university admin users only.
    """
    message = "Only university administrators can access this resource."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type == "university_admin"
        )


class IsCollegeUser(permissions.BasePermission):
    """
    Permission for college admin or staff users.
    Students cannot access college endpoints.
    """
    message = "Only college administrators or staff can access this resource."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user is a college type
        if request.user.user_type != "college_user":
            return False
        
        # Ensure they have a college profile
        return hasattr(request.user, 'college_profile') and request.user.college_profile is not None




class IsStudent(permissions.BasePermission):
    """
    Permission for student users only.
    College users cannot access student endpoints.
    """
    message = "Only students can access this resource."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.user_type == "student"


class IsStudentOrReadOnly(permissions.BasePermission):
    """
    Students have full access, others have read-only access.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_authenticated and 
            request.user.user_type == "student"
        )


class CanManageStudents(permissions.BasePermission):
    """
    Permission for users who can manage students (based on CollegeUserProfile permissions).
    """
    message = "You don't have permission to manage students."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # University admin can manage all
        if request.user.user_type == "university_admin":
            return True
        
        # Check college user permissions
        if hasattr(request.user, 'college_profile') and request.user.college_profile:
            return request.user.college_profile.can_manage_students
        
        return False


class CanManageMarks(permissions.BasePermission):
    """
    Permission for users who can manage marks.
    """
    message = "You don't have permission to manage marks."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type == "university_admin":
            return True
        
        if hasattr(request.user, 'college_profile') and request.user.college_profile:
            return request.user.college_profile.can_manage_marks
        
        return False


class CanVerifyData(permissions.BasePermission):
    """
    Permission for users who can verify data.
    """
    message = "You don't have permission to verify data."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type == "university_admin":
            return True
        
        if hasattr(request.user, 'college_profile') and request.user.college_profile:
            return request.user.college_profile.can_verify_data
        
        return False


class CanApproveCertificates(permissions.BasePermission):
    """
    Permission for users who can approve certificates.
    """
    message = "You don't have permission to approve certificates."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type == "university_admin":
            return True
        
        if hasattr(request.user, 'college_profile') and request.user.college_profile:
            return request.user.college_profile.can_approve_certificates
        
        return False


class IsSameCollege(permissions.BasePermission):
    """
    Object-level permission to ensure college users can only access 
    resources belonging to their own college.
    """
    message = "You can only access resources from your own college."

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # University admin can access all
        if request.user.user_type == "university_admin":
            return True
        
        # Get user's college
        user_college = request.user.get_college()
        if not user_college:
            return False
        
        # Get object's college (handle different model types)
        obj_college = None
        if hasattr(obj, 'college'):
            obj_college = obj.college
        elif hasattr(obj, 'college_id'):
            obj_college = obj
        
        return user_college.id == obj_college.id if obj_college else False


class CanManageVocRegistration(permissions.BasePermission):
    """
    Permission for university admin users who have access to VOC registration module.
    """
    message = "You don't have permission to manage Vocational Registrations."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superuser always has access
        if request.user.is_superuser:
            return True
            
        # Check if user is university admin and has the specific permission in their profile
        if request.user.user_type == "university_admin":
            return (
                hasattr(request.user, 'university_profile') and 
                request.user.university_profile.can_manage_voc_registration
            )
        
        return False
