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

import json
from django.db import transaction
from ug.services.semester_registration_service import (
    SemesterRegistrationService, STATUS_REGISTERED
)
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
    RegistrationResponseSerializer,
    SubmitRegistrationSerializer
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
            
            # Check eligibility
            eligibility = SemesterRegistrationService.check_registration_eligibility(student)
            
            # Determine registration status
            already_registered = eligibility.get('already_registered', False)
            registration_status = STATUS_REGISTERED if already_registered else None
            
            # If not eligible AND not already registered, block
            if not eligibility['eligible'] and not already_registered:
                return Response(
                    {
                        'error': 'Not eligible for registration',
                        'reason': eligibility.get('reason')
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verify semester matches next semester
            expected_semester = SemesterRegistrationService.SEMESTER_NUM_TO_TEXT.get(
                eligibility['next_semester']
            )
            
            if semester != expected_semester:
                return Response(
                    {
                        'error': f"Can only view courses for semester ({expected_semester})",
                        'current_semester': eligibility['current_semester'],
                        'next_semester': eligibility['next_semester']
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get available courses (with is_registered flags if already registered)
            courses_data = SemesterRegistrationService.get_available_courses(
                student, semester, registration_status=registration_status
            )
            
            # Add student and college information
            # Build absolute URLs
            img_url = student.profile_image.url if student.profile_image else None
            if img_url and not img_url.startswith('http'):
                img_url = request.build_absolute_uri(img_url)
                
            sig_url = student.signature.url if student.signature else None
            if sig_url and not sig_url.startswith('http'):
                sig_url = request.build_absolute_uri(sig_url)

            student_info = {
                'applicant_name': student.first_name or '',
                'college_name': student.user.college.name if student.user.college else None,
                'college_code': student.user.college.college_code if student.user.college else None,
                'profile_image': img_url,
                'signature': sig_url
            }
            
            # Add student info, registration window, and message to response
            courses_data['student_info'] = student_info
            courses_data['registration_window'] = eligibility.get('registration_window', {})
            courses_data['registration_open'] = eligibility.get('registration_open', False)
            
            if already_registered:
                courses_data['message'] = eligibility.get('message', 'You are already registered for this semester')
            
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
    
    Implementation:
    - Uses SubmitRegistrationSerializer for robust validation (handling multipart/form-data)
    - Delegates processing to `SemesterRegistrationService.process_registration_submission`
    - Atomic transaction ensures profile update and registration happen together
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Submit assessment UIDs, profile image, signature and create registrations"""
        try:
            # Get student profile
            student = request.user.ug_student_profile
            
            # Use Serializer for robust parsing & validation
            serializer = SubmitRegistrationSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)
                
            validated_data = serializer.validated_data
            
            # Delegate logic to service
            # Delegate logic to service
            result = SemesterRegistrationService.process_registration_submission(
                student=student,
                semester=validated_data['semester'],
                assessment_uids=validated_data.get('assessment_uids'),
                profile_image=validated_data.get('profile_image'),
                signature=validated_data.get('signature'),
                gender=validated_data.get('gender')
            )
            
            # Ensure proper absolute URLs
            if result.get('profile_image') and not result['profile_image'].startswith('http'):
                result['profile_image'] = request.build_absolute_uri(result['profile_image'])
                
            if result.get('signature') and not result['signature'].startswith('http'):
                result['signature'] = request.build_absolute_uri(result['signature'])
            
            return Response(result, status=status.HTTP_200_OK)
        
        except ValueError as e:
            error_message = str(e)
            if "already registered" in error_message.lower():
                return already_registered_response(request.data.get('semester'))
            return validation_error_response(error_message)
        except AttributeError:
            return profile_not_found_response()
        except Exception as e:
            return internal_error_response(str(e))
