def format_django_validation_error(error):
    """
    Extracts a clean message from a Django ValidationError or generic exception.
    """
    message = getattr(error, 'message', str(error))
    if hasattr(error, 'messages') and isinstance(error.messages, list) and len(error.messages) > 0:
        message = error.messages[0]
    
    # Clean up the message for the JSON response
    message = message.strip("[]'\"")
    return message

def get_first_serializer_error(errors):
    """
    Extracts the first error message from DRF serializer.errors.
    Returns a string in the format "field: message" or just "message".
    """
    # 1. If we have an explicit 'error' key (our custom convention), use it
    if 'error' in errors:
        error_msg = errors['error']
        if isinstance(error_msg, list) and len(error_msg) > 0:
            error_msg = error_msg[0]
        return str(error_msg)
    
    # 2. Otherwise, pick the first error from any field
    if errors:
        first_field = next(iter(errors))
        first_error = errors[first_field]
        
        if isinstance(first_error, list) and len(first_error) > 0:
            error_msg = first_error[0]
        else:
            error_msg = first_error
            
        if first_field == 'non_field_errors':
            return str(error_msg)
        return f"{first_field}: {error_msg}"
        
    return "Unknown validation error"