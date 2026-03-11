import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')

import django
django.setup()

from ug.models import UGStudentProfile
from accounts.models import UserAccount

profiles = UGStudentProfile.objects.select_related("user").all()

profiles_to_update = []
users_to_update = []

for p in profiles:
    user = p.user

    # update profile college
    if not p.college and user.college:
        p.college = user.college
        profiles_to_update.append(p)

    # update user current profile
    if not user.current_profile:
        user.current_profile = "ug"
        users_to_update.append(user)

# bulk update
UGStudentProfile.objects.bulk_update(profiles_to_update, ["college"], batch_size=1000)
UserAccount.objects.bulk_update(users_to_update, ["current_profile"], batch_size=1000)

print("Profiles updated:", len(profiles_to_update))
print("Users updated:", len(users_to_update))