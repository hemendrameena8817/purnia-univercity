# UG Serializers Package

# Import base serializers (student profile, department, etc.)
from ..base_serializers import (
    UGCollegeSerializer,
    UGDepartmentSerializer,
    UGDegreeSerializer,
    UGProgramSerializer,
    UGStudentProfileSerializer,
)

# Import registration serializers
from .registration_serializers import (
    CourseOptionSerializer,
    CourseGroupSerializer,
    RegistrationWindowSerializer,
    EligibilityResponseSerializer,
    AvailableCoursesResponseSerializer,
    CourseSelectionRequestSerializer,
    RegisteredCourseSerializer,
    RegistrationResponseSerializer,
)

__all__ = [
    # Base serializers
    'UGCollegeSerializer',
    'UGDepartmentSerializer',
    'UGDegreeSerializer',
    'UGProgramSerializer',
    'UGStudentProfileSerializer',
    # Registration serializers
    'CourseOptionSerializer',
    'CourseGroupSerializer',
    'RegistrationWindowSerializer',
    'EligibilityResponseSerializer',
    'AvailableCoursesResponseSerializer',
    'CourseSelectionRequestSerializer',
    'RegisteredCourseSerializer',
    'RegistrationResponseSerializer',
]
