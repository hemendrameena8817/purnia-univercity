import os
import sys
import json
import django
from pathlib import Path
from io import StringIO

# ---- Project Root ----
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pup_umis_backend.settings"
)

django.setup()

from django.core.management import call_command
from accounts.models import UserAccount

data_folder = BASE_DIR / "mba_sem" / "data"

print("🚀 Starting data migration...\n")

for file in sorted(data_folder.glob("*.json")):

    print(f"➡ Loading {file.name} ...")

    # 🔹 Special handling for accounts users file
    if file.name == "02_accounts_users.json":

        with open(file, "r") as f:
            data = json.load(f)

        for obj in data:
            fields = obj["fields"]
            username = fields.get("username")

            if not username:
                continue

            # 🔥 Safe fields only (controlled update)
            safe_fields = {
                "password": fields.get("password"),
                "first_name": fields.get("first_name"),
                "last_name": fields.get("last_name"),
                "email": fields.get("email"),
                "phone": fields.get("phone"),
                "user_type": fields.get("user_type"),
                "is_staff": fields.get("is_staff"),
                "is_active": fields.get("is_active"),
                "is_verified": fields.get("is_verified"),
                "college": fields.get("college"),
                "current_profile": fields.get("current_profile"),
            }

            user, created = UserAccount.objects.update_or_create(
                username=username,
                defaults=safe_fields
            )

            if created:
                print(f"   ✅ Created user: {username}")
            else:
                print(f"   🔄 Updated user: {username}")

    else:
        # 🔹 Normal fixture load
        call_command(
            "loaddata",
            str(file),
            stdout=StringIO(),
            stderr=StringIO(),
        )

print("\n✅ All data loaded successfully")
