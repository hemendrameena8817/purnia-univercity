import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import UserAccount
from mba_sem.services.profile_service import MBAProfileService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserAccount)
def auto_create_mba_student_profile(sender, instance, created, **kwargs):
    """
    Automatically creates MBAStudentProfile when a student UserAccount
    with current_profile in ('mba', 'mba_sem') is created.
    """
    if created and instance.user_type == 'student' and instance.current_profile in ('mba', 'mba_sem'):
        try:
            profile, is_new = MBAProfileService.create_or_get_profile_from_user(instance)
            if is_new:
                logger.info(f"Auto-created MBAStudentProfile for user: {instance.username}")
        except Exception as e:
            logger.error(f"Error auto-creating MBA profile for user {instance.username}: {str(e)}")
