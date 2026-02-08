from storages.backends.s3boto3 import S3Boto3Storage

class PrivateMediaStorage(S3Boto3Storage):
    default_acl = None          # IMPORTANT
    file_overwrite = False
    custom_domain = None        # Prevent accidental public URLs


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
    file_overwrite = True
