# File: mba_sem/data/data_loaders/export_mba_student_profiles.py

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")

import django
django.setup()

from mba_sem.models import MBAStudentProfile


def export_mba_student_profiles(output_file="mba_student_profiles_export.json"):

    print("🚀 Exporting MBA Student Profiles...\n")

    queryset = MBAStudentProfile.objects.select_related(
        "user", "college", "course", "batch"
    )

    data = []

    for obj in queryset:

        record = {
            "uid": str(obj.uid),
            "username": obj.user.username if obj.user else None,
            "registration_no": obj.registration_no,
            "roll_no": obj.roll_no,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "hindi_name": obj.hindi_name,
            "father_name": obj.father_name,
            "mother_name": obj.mother_name,
            "date_of_birth": obj.date_of_birth.isoformat() if obj.date_of_birth else None,
            "gender": obj.gender,
            "mobile_no": obj.mobile_no,
            "address": obj.address,
            "aadhar_no": obj.aadhar_no,
            "college_code": obj.college.college_code if obj.college else None,
            "course_name": obj.course.name if obj.course else None,
            "batch_name": obj.batch.name if obj.batch else None,
            "current_semester": obj.current_semester,
            "session_str": obj.session_str,
            "status": obj.status,
            "profile_image": obj.profile_image.name if obj.profile_image else None,
            "signature": obj.signature.name if obj.signature else None,
            "is_active": obj.is_active,
            "json_data": obj.json_data,
        }

        data.append(record)

    output_path = Path(__file__).resolve().parent / output_file

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Exported {len(data)} student profiles → {output_path}")


if __name__ == "__main__":
    export_mba_student_profiles()