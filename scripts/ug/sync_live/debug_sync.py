import os
import sys
import django
from pathlib import Path
from django.db import connections

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import SemesterRegistration

def debug():
    print("\nFetching Source Registration...")
    reg = SemesterRegistration.objects.using('default').select_related('student', 'student__user', 'batch', 'student__batch').first()
    if reg:
        print(f"  Reg Batch: {reg.batch.name if reg.batch else 'None'}")
        print(f"  Student Batch: {reg.student.batch.name if reg.student.batch else 'None'}")
        print(f"  Student UID: {reg.student.uid}")
        
if __name__ == "__main__":
    debug()
