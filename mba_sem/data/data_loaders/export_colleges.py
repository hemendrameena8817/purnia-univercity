# File: scripts/export_colleges.py

import os
import sys
import json
from pathlib import Path


def get_project_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent
    raise Exception("manage.py not found")


BASE_DIR = get_project_root()
sys.path.append(str(BASE_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pup_umis_backend.settings"
)

import django
django.setup()

from colleges.models import College


def export_colleges(output_file="colleges_full_export.json"):

    print("🚀 Exporting Colleges...\n")

    queryset = College.objects.select_related("university").prefetch_related("degree_offered")

    data = []

    for obj in queryset:
        record = {
            "uid": str(obj.uid),
            "name": obj.name,
            "short_name": obj.short_name,
            "college_code": obj.college_code,
            "center_code": obj.center_code,
            "address": obj.address,
            "principal": obj.principal,
            "contact_no": obj.contact_no,
            "email": obj.email,
            "founded": obj.founded.isoformat() if obj.founded else None,
            "website": obj.website,
            "logo": obj.logo.name if obj.logo else None,
            "college_name_hindi": obj.college_name_hindi,
            "college_name_krutidev": obj.college_name_krutidev,
            "university": obj.university.name if obj.university else None,
            "degrees": list(obj.degree_offered.values_list("name", flat=True)),
            "is_active": obj.is_active,
            "json_data": obj.json_data,
        }

        data.append(record)

    output_path = BASE_DIR / output_file

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Export completed → {output_path}")
    print(f"📦 Total Records: {len(data)}")


if __name__ == "__main__":
    export_colleges()