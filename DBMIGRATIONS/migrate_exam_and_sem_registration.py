
import os
import sys
import django
import argparse
import time
from django.db import connections
from django.db.utils import OperationalError
from django.core.management import call_command
# python DBMIGRATIONS/migrate_exam_and_sem_registration.py --session "2024-25" --semester "1ST"
# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.conf import settings
from pg.models import (
    PGStudentProfile,
    PGSemesterRegistration,
    PGExamRegistration,
    PGExamResult
)

def get_live_student_map():
    """
    Fetch student mapping data from LIVE database.
    Returns:
        student_map: {registration_no: id}
    """
    print("  → Fetching Student mapping from LIVE database...")
    
    students = PGStudentProfile.objects.using('live').values('id', 'registration_no')
    student_map = {s['registration_no']: s['id'] for s in students if s['registration_no']}
    print(f"    - Loaded {len(student_map)} students.")
    
    return student_map

def get_semester_int(sem_str):
    """Convert '1ST', '2ND' etc. to integer 1, 2."""
    if not sem_str: return None
    normalized = str(sem_str).upper().strip()
    if '1' in normalized: return 1
    if '2' in normalized: return 2
    if '3' in normalized: return 3
    if '4' in normalized: return 4
    return None


def migrate_semester_registrations(session, sem_int, batch, student_map, dry_run=False):
    print("=" * 80)
    print("MIGRATION: PGSemesterRegistration (Local) → (Live)")
    print("=" * 80)
    
    if not sem_int:
        print("  ⚠ Valid Integer Semester required for PGSemesterRegistration. Skipping.")
        return

    qs = PGSemesterRegistration.objects.filter(session=session, sem=sem_int)
    if batch:
        # PGStudentProfile.batch is a CharField
        qs = qs.filter(student__batch=batch)
        
    total_count = qs.count()
    print(f"  Found {total_count} records for Session='{session}', Sem={sem_int}, Batch='{batch or 'ALL'}'")

    if total_count == 0:
        return

    to_create = []
    skipped = 0
    
    for record in qs.iterator():
        if not record.student or not record.student.registration_no:
            skipped += 1
            continue
            
        live_student_id = student_map.get(record.student.registration_no)
        if not live_student_id:
            # print(f"    Skipping {record.student.registration_no} (Not in LIVE)") # Verbose
            skipped += 1
            continue

        obj = PGSemesterRegistration(
            student_id=live_student_id,
            start_date=record.start_date,
            end_date=record.end_date,
            is_open=record.is_open,
            sem=record.sem,
            status=record.status,
            exam_eligible=record.exam_eligible,
            remarks=record.remarks,
            session=record.session,
            json_data=record.json_data
        )
        to_create.append(obj)

    print(f"  Prepared {len(to_create)} records. Skipped {skipped} (Student mismatch).")
    
    if not dry_run and to_create:
        print("  Writing to LIVE database...")
        PGSemesterRegistration.objects.using('live').bulk_create(to_create)
        print("  ✓ Done.")
    elif dry_run:
        print("  [DRY RUN] Would write records.")

def migrate_exam_registrations(session, sem_int, batch, student_map, dry_run=False):
    print("=" * 80)
    print("MIGRATION: PGExamRegistration (Local) → (Live)")
    print("=" * 80)
    
    if not sem_int:
        print("  ⚠ Valid Integer Semester required for PGExamRegistration. Skipping.")
        return

    qs = PGExamRegistration.objects.filter(session=session, sem=sem_int)
    if batch:
        qs = qs.filter(student__batch=batch)

    total_count = qs.count()
    print(f"  Found {total_count} records for Session='{session}', Sem={sem_int}, Batch='{batch or 'ALL'}'")

    if total_count == 0:
        return

    to_create = []
    skipped = 0
    
    for record in qs.iterator():
        if not record.student or not record.student.registration_no:
            skipped += 1
            continue
            
        live_student_id = student_map.get(record.student.registration_no)
        if not live_student_id:
            skipped += 1
            continue

        obj = PGExamRegistration(
            student_id=live_student_id,
            start_date=record.start_date,
            end_date=record.end_date,
            is_open=record.is_open,
            fees=record.fees,
            sem=record.sem,
            status=record.status,
            session=record.session,
            json_data=record.json_data
        )
        to_create.append(obj)

    print(f"  Prepared {len(to_create)} records. Skipped {skipped}.")
    
    if not dry_run and to_create:
        print("  Writing to LIVE database...")
        PGExamRegistration.objects.using('live').bulk_create(to_create)
        print("  ✓ Done.")
    elif dry_run:
        print("  [DRY RUN] Would write records.")

def migrate_exam_results(session, sem_str, batch, student_map, dry_run=False):
    print("=" * 80)
    print("MIGRATION: PGExamResult (Local) → (Live)")
    print("=" * 80)
    
    qs = PGExamResult.objects.filter(session=session, semester=sem_str)
    if batch:
        qs = qs.filter(student__batch=batch)
        
    total_count = qs.count()
    print(f"  Found {total_count} records for Session='{session}', Semester='{sem_str}', Batch='{batch or 'ALL'}'")

    if total_count == 0:
        return

    to_create = []
    skipped = 0
    
    for record in qs.iterator():
        if not record.student or not record.student.registration_no:
            skipped += 1
            continue
            
        live_student_id = student_map.get(record.student.registration_no)
        if not live_student_id:
            skipped += 1
            continue

        obj = PGExamResult(
            student_id=live_student_id,
            semester=record.semester,
            session=record.session,
            cia_pass=record.cia_pass,
            ese_pass=record.ese_pass,
            semester_result=record.semester_result,
            semester_max_credit=record.semester_max_credit,
            semester_credit_earned=record.semester_credit_earned,
            sgpa=record.sgpa,
            next_semester=record.next_semester,
            next_sem_status=record.next_sem_status,
            is_legacy=record.is_legacy,
            published_at=record.published_at 
        )
        to_create.append(obj)

    print(f"  Prepared {len(to_create)} records. Skipped {skipped}.")
    
    if not dry_run and to_create:
        print("  Writing to LIVE database...")
        PGExamResult.objects.using('live').bulk_create(to_create, ignore_conflicts=True)
        print("  ✓ Done.")
    elif dry_run:
        print("  [DRY RUN] Would write records.")

def main():
    parser = argparse.ArgumentParser(description='Migrate PG Exam/Sem Registration & Results Local -> Live')
    parser.add_argument('--session', type=str, required=True, help='Session (e.g. "2024-25")')
    parser.add_argument('--semester', type=str, required=True, help='Semester (e.g. "1ST", "2ND")')
    parser.add_argument('--batch', type=str, help='Batch Name (e.g. "2024-26")')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    
    args = parser.parse_args()
    
    if not args.dry_run:
        print("\n⚠ WARNING: You are about to write to the LIVE database.")
        if input("Continue? (yes/no): ").lower() not in ['yes', 'y']:
            print("Cancelled.")
            return

    # Check Connection
    if 'live' not in settings.DATABASES:
        print("❌ 'live' database not configured.")
        return
    
    try:
        with connections['live'].cursor():
            pass
        print(f"✓ Connected to LIVE database: {settings.DATABASES['live']['HOST']}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    # Constants
    session = args.session
    sem_str = args.semester
    sem_int = get_semester_int(sem_str)
    batch = args.batch

    # 1. Get Map
    student_map = get_live_student_map()
    if not student_map:
        print("❌ No students found in LIVE database. Aborting.")
        return

    # 2. Runs
    migrate_semester_registrations(session, sem_int, batch, student_map, args.dry_run)
    migrate_exam_registrations(session, sem_int, batch, student_map, args.dry_run)
    migrate_exam_results(session, sem_str, batch, student_map, args.dry_run)

    print("\nAll Migrations Completed.")


if __name__ == '__main__':
    main()
