"""
Student Semester Registration API Views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ug.services.semester_registration_service import SemesterRegistrationService
from ug.serializers.registration_serializers import (
    EligibilityResponseSerializer,
    AvailableCoursesResponseSerializer,
    CourseSelectionRequestSerializer,
    RegistrationResponseSerializer
)


@swagger_auto_schema(
    method='get',
    operation_description="Check if student is eligible to register for next semester",
    responses={
        200: EligibilityResponseSerializer,
        400: "Bad Request",
        403: "Not eligible for registration"
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_registration_eligibility(request):
    """
    Check if the logged-in student can register for next semester
    
    Returns eligibility status, current semester, next semester, and registration window details
    """
    try:
        # Get student profile
        student = request.user.ug_student_profile
        
        # Check eligibility
        result = SemesterRegistrationService.check_registration_eligibility(student)
        
        # Return appropriate status code
        if result['eligible']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_403_FORBIDDEN)
    
    except AttributeError:
        return Response(
            {'error': 'Student profile not found for this user'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='get',
    operation_description="Get available courses for semester registration",
    manual_parameters=[
        openapi.Parameter(
            'semester',
            openapi.IN_QUERY,
            description="Semester to register for (e.g., '3RD', '4TH')",
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    responses={
        200: AvailableCoursesResponseSerializer,
        400: "Bad Request",
        403: "Not eligible for registration"
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_courses_for_registration(request):
    """
    Get list of available courses for student to register
    
    Filters major courses by department, auto-assigns minor/MDC from 1st semester,
    and provides elective options
    
    Query Parameters:
        semester: Target semester (e.g., '3RD')
    """
    try:
        # Get student profile
        student = request.user.ug_student_profile
        
        # Get target semester from query params
        semester = request.GET.get('semester')
        if not semester:
            return Response(
                {'error': 'semester parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # First check eligibility
        eligibility = SemesterRegistrationService.check_registration_eligibility(student)
        if not eligibility['eligible']:
            return Response(
                {
                    'error': 'Not eligible for registration',
                    'reason': eligibility.get('reason')
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify semester matches next semester
        if semester != f"{eligibility['next_semester']}":
            # Try to match semester code format
            semester_map = {
                1: '1ST', 2: '2ND', 3: '3RD', 4: '4TH',
                5: '5TH', 6: '6TH', 7: '7TH', 8: '8TH'
            }
            expected_semester = semester_map.get(eligibility['next_semester'])
            if semester != expected_semester:
                return Response(
                    {
                        'error': f"Can only register for next semester ({expected_semester})",
                        'current_semester': eligibility['current_semester'],
                        'next_semester': eligibility['next_semester']
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get available courses
        courses_data = SemesterRegistrationService.get_available_courses(student, semester)
        
        return Response(courses_data, status=status.HTTP_200_OK)
    
    except AttributeError:
        return Response(
            {'error': 'Student profile not found for this user'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='post',
    operation_description="Submit course selections for semester registration",
    request_body=CourseSelectionRequestSerializer,
    responses={
        200: RegistrationResponseSerializer,
        400: "Bad Request - Invalid selections",
        403: "Not eligible for registration"
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_course_registration(request):
    """
    Submit course selections and create StudentCourseAssessment entries
    
    Request Body:
        {
            "semester": "3RD",
            "session": "2024-25",
            "selections": {
                "major_courses": ["HIST301", "HIST302"],
                "elective_courses": ["GE301"],
                "aecc_courses": ["AECC301"]
            }
        }
    
    Returns: Registration confirmation with list of registered courses
    """
    try:
        # Get student profile
        student = request.user.ug_student_profile
        
        # Validate request data
        serializer = CourseSelectionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        semester = serializer.validated_data['semester']
        selections = serializer.validated_data['selections']
        
        # Check eligibility
        eligibility = SemesterRegistrationService.check_registration_eligibility(student)
        if not eligibility['eligible']:
            return Response(
                {
                    'error': 'Not eligible for registration',
                    'reason': eligibility.get('reason')
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create registrations
        result = SemesterRegistrationService.create_course_registrations(
            student, semester, selections
        )
        
        return Response(result, status=status.HTTP_200_OK)
    
    except ValueError as e:
        # Validation error
        return Response(
            {'error': 'Validation failed', 'details': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except AttributeError:
        return Response(
            {'error': 'Student profile not found for this user'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
