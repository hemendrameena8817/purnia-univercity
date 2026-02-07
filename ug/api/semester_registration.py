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
from ug.utils.api_response import (
    success_response, error_response,
    already_registered_response, not_eligible_response, 
    validation_error_response, profile_not_found_response,
    internal_error_response, missing_field_response
)
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
            
            # Add student and college information
            student_info = {
                'applicant_name': student.first_name or '',
                'college_name': student.college.name if student.college else None,
                'college_code': student.college.college_code if student.college else None
            }
            
            # Add student info to response
            courses_data['student_info'] = student_info
            
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
    Submit course registration using assessment UIDs (OPTIMIZED)
    
    POST /api/ug/semester-registration/submit/
    
    Request Body:
    {
        "semester": "3RD",
        "assessment_uids": [
            "uuid-1",
            "uuid-2",
            "uuid-3"
        ]
    }
    
    The assessment UIDs come from the available-courses API.
    
    Optimizations:
    - Uses bulk_create for performance (handles 30k+ students)
    - Fetches CourseStructure data using UIDs
    - Sets exam_type='Regular' for new registrations
    - Checks for duplicates in single bulk query
    
    Updates SemesterRegistration.status to 'REGISTERED'
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Submit assessment UIDs and create registrations"""
        try:
            # Get student profile
            student = request.user.ug_student_profile
            
            # Extract data from request
            semester = request.data.get('semester')
            assessment_uids = request.data.get('assessment_uids', [])
            
            # Validate required fields
            if not semester:
                return missing_field_response('semester')
            
            if not assessment_uids or not isinstance(assessment_uids, list):
                return validation_error_response('assessment_uids must be a non-empty list')
            
            # Check eligibility
            eligibility = SemesterRegistrationService.check_registration_eligibility(student)
            if not eligibility.get('eligible', False):
                return not_eligible_response(
                    reason=eligibility.get('reason'),
                    message=eligibility.get('message')
                )
            
            # Create registrations (optimized bulk operation)
            result = SemesterRegistrationService.create_course_registrations(
                student, semester, assessment_uids
            )
            
            # Add status to success response
            result['status'] = 'success'
            return Response(result, status=status.HTTP_200_OK)
        
        except ValueError as e:
            error_message = str(e)
            
            # Check if it's an "already registered" error
            if "already registered" in error_message.lower():
                return already_registered_response(semester)
            
            # Other validation errors (400 Bad Request)
            return validation_error_response(error_message)
        except AttributeError:
            return profile_not_found_response()
        except Exception as e:
            return internal_error_response(str(e))
