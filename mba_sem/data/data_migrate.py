import os
import sys
import django
from pathlib import Path
from io import StringIO

# ---- Setup Django ----
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pup_umis_backend.settings")
django.setup()

from django.core.management import call_command
from data_loaders.user_accounts import *
from data_loaders.exam_schedule import *
from data_loaders.import_exam_center_mapping import *
from data_loaders.import_colleges import *
from data_loaders.import_mba_student_profiles import *
from data_loaders.import_mba_exam_registrations import *
from data_loaders.import_mba_student_course_assessments import *

data_folder = BASE_DIR / "mba_sem" / "data"

print("🚀 Starting data migration...\n")

for file in sorted(data_folder.glob("*.json")):
    print(f"➡ Loading {file.name} ...")

    if file.name == "02_accounts_users.json":
        load_users(file)
    elif file.name == "04_mba_exam_schedule.json":
        import_exam_schedule(file)
    elif file.name == "05_colleges_full_export.json":
        import_colleges(file)
    elif file.name == "06_mba_exam_center_mapping.json":
        import_exam_center_mapping(file)
    elif file.name == "07_mba_student_profiles_export.json":
        import_mba_student_profiles(file)
    elif file.name == "08_mba_exam_registrations_export.json":
        import_mba_exam_registrations(file)
    elif file.name == "10_mba_student_course_assessments_export.json":
        import_mba_student_course_assessments(file)
    else:
        call_command(
            "loaddata",
            str(file),
            stdout=StringIO(),
            stderr=StringIO(),
        )

print("\n✅ All data loaded successfully")
