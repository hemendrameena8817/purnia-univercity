# File: mba_sem/data/data_loaders/export_mba_exam_registrations.py

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

from mba_sem.models import MBAExamRegistration


def export_mba_exam_registrations(output_file="mba_exam_registrations_export.json"):

    print("🚀 Exporting MBA Exam Registrations...\n")

    queryset = MBAExamRegistration.objects.select_related(
        "student", "exam"
    ).prefetch_related("exam_subjects")

    data = []

    for obj in queryset:
        record = {
            "uid": str(obj.uid),
            "registration_no": obj.student.registration_no if obj.student else None,
            "exam_name": obj.exam.name if obj.exam else None,
            "exam_type": obj.exam_type,
            "subjects_codes": list(
                obj.exam_subjects.values_list("code", flat=True)
            ),
            "start_date": obj.start_date.isoformat() if obj.start_date else None,
            "end_date": obj.end_date.isoformat() if obj.end_date else None,
            "is_open": obj.is_open,
            "fees": obj.fees,
            "sem": obj.sem,
            "status": obj.status,
            "session": obj.session,
            "json_data": obj.json_data,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }

        data.append(record)

    output_path = Path(__file__).resolve().parent / output_file

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Exported {len(data)} exam registrations → {output_path}")


if __name__ == "__main__":
    export_mba_exam_registrations()