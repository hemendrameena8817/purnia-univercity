# pup_umis_backend/upload_paths.py
import uuid
import os
from datetime import datetime

def unique_file_path(prefix):
    """
    Generate unique file path with date organization and UUID filename
    
    Args:
        prefix: Base path prefix (e.g., 'voc_registrations/images/')
    
    Returns:
        Function that generates: prefix/YYYY/MM/uuid.ext
        Example: voc_registrations/images/2024/02/a1b2c3d4e5f6g7h8.jpg
    """
    def _path(instance, filename):
        ext = os.path.splitext(filename)[1]
        now = datetime.now()
        return (
            f"{prefix}/"
            f"{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}{now.minute:02d}{now.second:02d}/"
            f"{uuid.uuid4().hex}{ext}"
        )
    return _path
