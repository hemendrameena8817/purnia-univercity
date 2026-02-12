# pup_umis_backend/upload_paths.py
import uuid
import os
from datetime import datetime
from django.utils.deconstruct import deconstructible

@deconstructible
class UniqueFilePath:
    def __init__(self, prefix):
        self.prefix = prefix

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1]
        now = datetime.now()
        return (
            f"{self.prefix}/"
            f"{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}{now.minute:02d}{now.second:02d}/"
            f"{uuid.uuid4().hex}{ext}"
        )

def unique_file_path(prefix):
    return UniqueFilePath(prefix)

# Dummy function to satisfy old migration lookups if necessary
def _path(instance, filename):
    pass
