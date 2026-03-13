import os
import sys
from pathlib import Path
from datetime import datetime

import django

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.utils import timezone
from ug.models import UGStudentProfile, ExamRegistration


DEFAULT_START_DATE = timezone.make_aware(datetime(2026, 3, 12, 0, 0, 0))
DEFAULT_END_DATE = timezone.make_aware(datetime(2026, 3, 15, 0, 0, 0))


def read_registration_numbers(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"TXT file not found: {file_path}")

    with file_path.open('r', encoding='utf-8') as file:
        reg_nos = [line.strip() for line in file if line.strip()]

    unique_reg_nos = list(dict.fromkeys(reg_nos))
    return unique_reg_nos


def open_exam_registrations(txt_file):
    reg_nos = read_registration_numbers(txt_file)
    print(f"Found {len(reg_nos)} registration numbers in file.")
    updated = 0
    missing_students = []
    missing_registrations = []
    already_processed_registrations = []

    for reg_no in reg_nos:
        student = UGStudentProfile.objects.select_related('user').filter(
            user__username=reg_no
        ).first()

        if not student:
            missing_students.append(reg_no)
            print(f"MISSING STUDENT: {reg_no}")
            continue

        all_registrations = ExamRegistration.objects.filter(
            student=student,
            session='2025-26',
            sem=1,
        ).order_by('-created_at')

        registration = all_registrations.filter(
            status='PENDING',
        ).first()

        if not registration:
            existing_registration = all_registrations.first()
            if existing_registration:
                if existing_registration.status in ['OPEN', 'REGISTERED']:
                    already_processed_registrations.append(reg_no)
            else:
                missing_registrations.append(reg_no)
                print(f"NO REGISTRATION: {reg_no}")
            continue

        registration.status = 'OPEN'
        registration.is_open = True
        registration.start_date = DEFAULT_START_DATE
        registration.end_date = DEFAULT_END_DATE
        registration.save(update_fields=['status', 'is_open', 'start_date', 'end_date', 'updated_at'])
        updated += 1

    print(f"Successfully opened {updated} exam registrations.")

    if already_processed_registrations:
        print(f"Skipped {len(already_processed_registrations)} students because exam registration is already OPEN or REGISTERED.")
        for reg_no in already_processed_registrations[:20]:
            print(f"  ALREADY OPEN/REGISTERED: {reg_no}")
        if len(already_processed_registrations) > 20:
            print(f"  ... and {len(already_processed_registrations) - 20} more")

    if missing_students:
        print(f"Could not find {len(missing_students)} students by username.")

    if missing_registrations:
        print(f"No exam registration found for {len(missing_registrations)} students with session=2025-26 and sem=1.")


def main():
    if len(sys.argv) < 2:
        raise ValueError('Provide TXT file path as first argument.')

    txt_file = sys.argv[1]
    open_exam_registrations(txt_file=txt_file)


if __name__ == '__main__':
    main()
