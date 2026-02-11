import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage

try:
    from storages.backends.s3boto3 import S3Boto3Storage
    _s3_available = True
except ImportError:
    _s3_available = False


def _use_s3():
    """Check if S3 storage should be used (i.e. bucket name is configured)."""
    return _s3_available and getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)


class PrivateMediaStorage:
    """
    Factory-style storage: returns S3Boto3Storage in production,
    FileSystemStorage in local development.
    """
    location = ""

    def __new__(cls, *args, **kwargs):
        if _use_s3():
            instance = S3Boto3Storage.__new__(S3Boto3Storage)
            S3Boto3Storage.__init__(instance, *args, **kwargs)
            instance.default_acl = None
            instance.file_overwrite = False
            instance.custom_domain = None
            instance.location = cls.location
            return instance
        else:
            media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            
            location = os.path.join(media_root, cls.location)
            # Ensure base_url has a trailing slash and uses forward slashes
            base_url = f"{media_url.rstrip('/')}/{cls.location.strip('/')}/"
            
            instance = FileSystemStorage(location=location, base_url=base_url)
            return instance


class MediaStorage(PrivateMediaStorage):
    location = "media/uploads"


class DocumentStorage(PrivateMediaStorage):
    location = "documents"


class StudentDocumentStorage(PrivateMediaStorage):
    location = "students/documents"


class ProfilePhotoStorage(PrivateMediaStorage):
    location = "profiles/photos"


class GrievanceAttachmentStorage(PrivateMediaStorage):
    location = "grievances/attachments"


class ExamDocumentStorage(PrivateMediaStorage):
    location = "exams/documents"


class TemporaryStorage(PrivateMediaStorage):
    location = "temp"
