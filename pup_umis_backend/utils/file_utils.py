"""
Utility functions for the PUP UMIS Backend project.
Reusable helper functions across all apps.
"""


def get_absolute_url(file_field, request=None):
    """
    Get absolute URL for a file field (e.g., ImageField, FileField).
    
    Args:
        file_field: Django FileField or ImageField instance
        request: HTTP request object (optional, used to build absolute URI)
    
    Returns:
        str: Absolute URL if file exists and request is provided, 
             relative URL if file exists but no request,
             None if file doesn't exist
    
    Usage:
        # In serializer:
        logo_url = serializers.SerializerMethodField()
        
        def get_logo_url(self, obj):
            return get_absolute_url(obj.logo, self.context.get('request'))
    """
    if file_field:
        if request:
            return request.build_absolute_uri(file_field.url)
        return file_field.url
    return None


def get_file_size(file_field):
    """
    Get file size in bytes for a file field.
    
    Args:
        file_field: Django FileField or ImageField instance
    
    Returns:
        int: File size in bytes, or None if file doesn't exist
    """
    if file_field:
        try:
            return file_field.size
        except Exception:
            return None
    return None


def format_file_size(size_bytes):
    """
    Format file size from bytes to human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        str: Formatted size (e.g., "1.5 MB", "500 KB")
    """
    if not size_bytes:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def image_to_base64(path):
    """
    Convert an image file to a base64 string.
    
    Args:
        path: Absolute file path to the image
        
    Returns:
        str: Base64 encoded string of the image, or empty string if file not found
    """
    import os
    import base64
    
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    return ""


def generate_barcode_base64(text):
    import barcode
    from barcode.writer import ImageWriter
    import io
    import base64
    
    try:
        # Code128 is a good choice for alphanumeric data
        CODE128 = barcode.get_barcode_class('code128')
        bar = CODE128(text, writer=ImageWriter())
        
        buffer = io.BytesIO()
        bar.write(buffer, options={"write_text": False, "module_height": 5.0}) # Don't write text under barcode
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Barcode generation failed: {str(e)}")
        return ""
