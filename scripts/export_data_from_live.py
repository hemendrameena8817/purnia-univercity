import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

import pandas as pd
from django.http import HttpResponse
from django.db.models import Count

# # 👉 SemesterRegistration model import करना होगा - यह check करें कि यह किस app में है
# try:
#     from pgoldresult.models import SemesterRegistration
# except ImportError:
#     try:
#         from pg.models import SemesterRegistration
#     except ImportError:
#         from accounts.models import SemesterRegistration

from openpyxl import Workbook
from ug.models import ExamRegistration, SemesterRegistration
from pg.models import PGExamRegistration


def generate_excel(data, file_name):
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"

    # Header
    headers = ['College', 'Status', 'Semester', 'Department', 'Count']
    ws.append(headers)

    # Data
    for row in data:
        ws.append([
            row.get('student__college__name', ''),
            row.get('status', ''),
            row.get('sem', ''),
            row.get('student__department__name', ''),
            row.get('count', 0)
        ])

    wb.save(file_name)
    print(f"✅ Saved: {file_name}")


def export_all():
    print("🚀 Export started...")

    # 1. Semester
    sem_data = SemesterRegistration.objects.values(
        'student__college__name',
        'status',
        'sem',
        'student__department__name'
    ).annotate(count=Count('id')).order_by('student__college__name').iterator()

    generate_excel(sem_data, 'semester_registration.xlsx')

    # 2. Exam
    exam_data = ExamRegistration.objects.values(
        'student__college__name',
        'status',
        'sem',
        'student__department__name'
    ).annotate(count=Count('id')).order_by('student__college__name').iterator()

    generate_excel(exam_data, 'exam_registration.xlsx')

    # 3. PG Exam
    pg_exam_data = PGExamRegistration.objects.values(
        'student__college__name',
        'status',
        'sem',
        'student__department__name'
    ).annotate(count=Count('id')).order_by('student__college__name').iterator()

    generate_excel(pg_exam_data, 'pg_exam_registration.xlsx')

    print("🎉 All files exported successfully!")


if __name__ == "__main__":
    export_all()