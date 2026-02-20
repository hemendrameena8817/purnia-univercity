"""
Simple User Loader

- Create if not exists
- Update if exists
- Skip existing superusers
- Properly handle ManyToMany (groups, permissions)
"""

import json
from pathlib import Path
from django.db import transaction
from django.contrib.auth.models import Group, Permission
from accounts.models import UserAccount


@transaction.atomic
def load_users(file_path: Path) -> None:

    if not file_path.exists():
        print("❌ File not found")
        return

    data = json.loads(file_path.read_text())

    for obj in data:
        fields = obj.get("fields", {})
        username = fields.get("username")

        if not username:
            continue

        # Extract ManyToMany before update_or_create
        groups_ids = fields.pop("groups", [])
        permission_ids = fields.pop("user_permissions", [])

        # Remove ID if present
        fields.pop("id", None)

        # Check existing user
        existing_user = UserAccount.objects.filter(username=username).first()

        # Skip if existing superuser
        if existing_user and existing_user.is_superuser:
            print(f"⏭ Skipped superuser: {username}")
            continue

        # Create or update
        user, created = UserAccount.objects.update_or_create(
            username=username,
            defaults=fields
        )

        # Handle ManyToMany safely
        if groups_ids:
            user.groups.set(Group.objects.filter(id__in=groups_ids))
        else:
            user.groups.clear()

        if permission_ids:
            user.user_permissions.set(
                Permission.objects.filter(id__in=permission_ids)
            )
        else:
            user.user_permissions.clear()

        print(f"{'✅ Created' if created else '🔄 Updated'}: {username}")
