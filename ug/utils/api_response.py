"""
API Response Utilities

Helper functions for creating standardized API responses.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message=None, http_status=status.HTTP_200_OK):
    """
    Create a success response
    
    Args:
        data: Response data (dict)
        message: Success message
        http_status: HTTP status code (default: 200)
    
    Returns:
        Response object with status='success'
    """
    response_data = {'status': 'success'}
    
    if data:
        response_data.update(data)
    
    if message:
        response_data['message'] = message
    
    return Response(response_data, status=http_status)


def error_response(error, message=None, error_code=None, http_status=status.HTTP_400_BAD_REQUEST, **kwargs):
    """
    Create an error response
    
    Args:
        error: Error title/summary
        message: Detailed error message
        error_code: Standard error code
        http_status: HTTP status code (default: 400)
        **kwargs: Additional fields to include in response
    
    Returns:
        Response object with status='error'
    """
    response_data = {
        'status': 'error',
        'error': error
    }
    
    if message:
        response_data['message'] = message
    
    if error_code:
        response_data['error_code'] = error_code
    
    # Add any additional fields
    response_data.update(kwargs)
    
    return Response(response_data, status=http_status)


# Specific error response helpers
def already_registered_response(semester):
    return success_response(
        data={
            'already_registered': True,
            'info': 'No action needed'
        },
        message=f'You are already registered for semester {semester}. Your registration is complete.'
    )


def not_eligible_response(reason=None, message=None):
    """Student not eligible for registration - HTTP 403"""
    return error_response(
        error='Not eligible for registration',
        message=message or 'You are not eligible for registration',
        error_code='NOT_ELIGIBLE',
        http_status=status.HTTP_403_FORBIDDEN,
        reason=reason
    )


def validation_error_response(message):
    return error_response(
        error='Validation failed',
        message=message,
        error_code='VALIDATION_ERROR',
        http_status=status.HTTP_400_BAD_REQUEST
    )


def profile_not_found_response():
    return error_response(
        error='Student profile not found for this user',
        error_code='PROFILE_NOT_FOUND',
        http_status=status.HTTP_400_BAD_REQUEST
    )


def internal_error_response(message=None):
    """Internal server error - HTTP 500"""
    return error_response(
        error='Internal server error',
        message=message or 'An unexpected error occurred',
        error_code='INTERNAL_ERROR',
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def missing_field_response(field_name):
    """Missing required field - HTTP 400"""
    return error_response(
        error='Missing required field',
        message=f'{field_name} field is required',
        error_code='MISSING_REQUIRED_FIELD',
        http_status=status.HTTP_400_BAD_REQUEST
    )


def invalid_data_response(message):
    """Invalid data - HTTP 400"""
    return error_response(
        error='Invalid data',
        message=message,
        error_code='INVALID_DATA',
        http_status=status.HTTP_400_BAD_REQUEST
    )
