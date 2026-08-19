"""
MBA Profile Service
Handles creation, updating, and querying of MBA student profiles.
"""
import logging
from typing import Tuple, Optional, Dict
from django.core.exceptions import ObjectDoesNotExist

from mba_sem.models import MBAStudentProfile, MBACourse, MBABatch
from accounts.models import UserAccount

logger = logging.getLogger(__name__)


class MBAProfileService:
    """Service to handle MBA student profiles and account linkages"""

    @classmethod
    def create_or_get_profile_from_user(
        cls,
        user: UserAccount,
        course: Optional[MBACourse] = None,
        batch: Optional[MBABatch] = None,
        semester: int = 1,
        **extra_fields
    ) -> Tuple[MBAStudentProfile, bool]:
        """
        Creates or retrieves an MBAStudentProfile from an existing UserAccount.
        """
        if not course:
            course = MBACourse.objects.first()
        if not batch:
            batch = MBABatch.objects.first()

        defaults = {
            "user": user,
            "roll_no": extra_fields.get("roll_no", user.username),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "mobile_no": user.phone,
            "college": user.college,
            "course": course,
            "batch": batch,
            "current_semester": semester,
            "status": extra_fields.get("status", "Regular"),
            "is_active": True,
        }
        defaults.update(extra_fields)

        profile, created = MBAStudentProfile.objects.get_or_create(
            registration_no=user.username,
            defaults=defaults
        )

        if not created and not profile.user:
            profile.user = user
            profile.save(update_fields=['user'])

        return profile, created

    @classmethod
    def get_dashboard_summary(cls, user: UserAccount) -> Dict:
        """
        Returns structured dashboard information for an MBA student.
        """
        try:
            student = MBAStudentProfile.objects.select_related(
                'course', 'batch', 'college'
            ).get(user=user)

            return {
                'student_info': {
                    'registration_no': student.registration_no,
                    'roll_no': student.roll_no,
                    'name': f"{student.first_name or ''} {student.last_name or ''}".strip(),
                    'course': student.course.name if student.course else None,
                    'college': student.college.name if student.college else None,
                    'current_semester': student.current_semester,
                    'session': student.session_str,
                    'profile_image': student.profile_image.url if student.profile_image else None,
                },
                'batch': student.batch.name if student.batch else None,
                'registration': {
                    'eligible': False,
                    'reason': 'MBA registration service not yet implemented',
                    'registration_open': False,
                }
            }
        except ObjectDoesNotExist:
            return {
                'student_info': None,
                'registration': {
                    'eligible': False,
                    'reason': 'No MBA student profile found for this user',
                    'registration_open': False,
                }
            }
