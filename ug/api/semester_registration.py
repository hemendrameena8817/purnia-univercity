"""
Student Semester Registration API Views (Class-based)

Handles student semester registration where SemesterRegistration entries already exist.
Students with PASS/PROMOTED status can register for courses in their next semester.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status

from ug.services.semester_registration_service import SemesterRegistrationService
from ug.serializers import (
    EligibilityResponseSerializer,
    AvailableCoursesResponseSerializer,
    CourseSelectionRequestSerializer,
    RegistrationResponseSerializer
)


class RegistrationEligibilityView(APIView):
    """
    Check if student is eligible to register for next semester
    
    GET /api/ug/semester-registration/eligibility/
    
    Returns eligibility status based on:
    - Current semester result (PASS/PROMOTED required)
    - Existence of SemesterRegistration for next semester
    - Registration window status (is_open)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check registration eligibility for logged-in student"""
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


class AvailableCoursesView(APIView):
    """
    Get available courses for semester registration
    
    GET /api/ug/semester-registration/available-courses/?semester=3RD
    
    Returns:
    - Major courses (filtered by student's department)
    - Minor courses (auto-assigned from 1st semester)
    - MDC courses (auto-assigned from 1st semester)
    - Elective courses (student can choose)
    - AECC courses (student can choose)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get available courses for semester registration"""
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


class SubmitRegistrationView(APIView):
    """
    Submit course selections for semester registration
    
    POST /api/ug/semester-registration/submit/
    
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

    Creates StudentCourseAssessment entries for:
    - Selected major courses
    - Auto-assigned minor courses (from 1st semester)
    - Auto-assigned MDC courses (from 1st semester)
    - Selected elective courses
    - Selected AECC courses
    
    Updates SemesterRegistration.status to 'REGISTERED'
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Submit course selections and create registrations"""
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
            
            # Validate and create registrations
            result = SemesterRegistrationService.create_course_registrations(
                student, semester, selections
            )
            
            return Response(result, status=status.HTTP_200_OK)
        
        except ValueError as e:
            # Validation error from service layer
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
