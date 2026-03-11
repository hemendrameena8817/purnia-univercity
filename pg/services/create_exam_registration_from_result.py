"""
Service to create PGExamRegistration entries from PGExamResult.

For every PGExamResult found (filtered by semester/session/batch),
a corresponding PGExamRegistration entry is created IF one does not
already exist for that (student, sem, session, exam_type) combination.
"""
from django.db import transaction
from django.utils import timezone
from datetime import datetime
import pytz
from pg.models import PGExamResult, PGExamRegistration

# Registration window
IST = pytz.timezone('Asia/Kolkata')
REGISTRATION_START = IST.localize(datetime(2026, 3, 7, 0, 0, 0))    # 07-Mar-2026 12:00 AM IST
REGISTRATION_END   = IST.localize(datetime(2026, 3, 11, 0, 0, 0))   # 11-Mar-2026 12:00 AM IST

# Mapping: semester string (e.g. '3RD') → integer sem number stored in PGExamRegistration.sem
SEMESTER_STR_TO_INT = {
    '1ST': 1,
    '2ND': 2,
    '3RD': 3,
    '4TH': 4
}


def create_exam_registration_from_result(
    semester,
    session,
    batch=None,
    registration_no=None,
    registration_nos=None,
    include_all_batches=False,
    exam_type='REGULAR',
    dry_run=False,
):
    """
    Creates PGExamRegistration entries from PGExamResult.

    Args:
        semester (str): Semester code e.g. '3RD'
        session (str): Session e.g. '2024-25'
        batch (str): Optional batch filter e.g. '2024-26'
        registration_no (str): Single student registration number
        registration_nos (list): Multiple student registration numbers
        include_all_batches (bool): If True, ignore batch filter
        exam_type (str): REGULAR / BACK / IMPROVEMENT
        dry_run (bool): If True, do NOT commit any DB changes
    """

    stats = {
        'total_results': 0,
        'registrations_created': 0,
        'registrations_existed': 0,
        'errors': 0,
    }

    sem_int = SEMESTER_STR_TO_INT.get(semester.upper())
    if sem_int is None:
        print(f"⚠️  Unknown semester string '{semester}'. sem will be stored as None.")

    print(f"\n--- Starting Exam Registration Creation ---")
    print(f"Semester : {semester}  (sem={sem_int})")
    print(f"Session  : {session}")
    print(f"Batch    : {batch if batch else 'ALL'}")
    print(f"Exam Type: {exam_type}")
    print(f"Dry Run  : {dry_run}")

    # ── Base queryset ──────────────────────────────────────────────
    results = PGExamResult.objects.filter(
        semester=semester,
        session=session,
        cia_pass=True,          # Only students who passed CIA
    ).select_related('student')

    # ── Scope filters ──────────────────────────────────────────────
    if registration_no:
        results = results.filter(student__registration_no=registration_no)
        print(f"Single student mode: {registration_no}")
    elif registration_nos:
        results = results.filter(student__registration_no__in=registration_nos)
        print(f"Multiple students mode: {len(registration_nos)} students")
    elif batch and not include_all_batches:
        results = results.filter(student__batch=batch)

    total = results.count()
    stats['total_results'] = total
    print(f"Found {total} PGExamResult records to process.\n")

    # ── Processing ─────────────────────────────────────────────────
    with transaction.atomic():
        for idx, result in enumerate(results, start=1):
            student = result.student

            if idx % 100 == 0 or idx == 1:
                print(f"[{idx}/{total}] Processing: {student.registration_no}")

            try:
                already_exists = PGExamRegistration.objects.filter(
                    student=student,
                    sem=sem_int,
                    session=session,
                    exam_type=exam_type,
                ).exists()

                if already_exists:
                    stats['registrations_existed'] += 1
                    continue

                if not dry_run:
                    PGExamRegistration.objects.create(
                        student=student,
                        sem=sem_int,
                        session=session,
                        exam_type=exam_type,
                        status='OPEN',
                        is_open=True,
                        start_date=REGISTRATION_START,
                        end_date=REGISTRATION_END,
                    )

                stats['registrations_created'] += 1

            except Exception as e:
                print(f"  ❌ Error for {student.registration_no}: {e}")
                stats['errors'] += 1

        if dry_run:
            # Roll back any accidental writes (there should be none, but safety first)
            transaction.set_rollback(True)

    # ── Summary ────────────────────────────────────────────────────
    print("\n--- Summary ---")
    print(f"Total PGExamResult records   : {stats['total_results']}")
    print(f"Registrations Created        : {stats['registrations_created']}")
    print(f"Registrations Already Existed: {stats['registrations_existed']}")
    print(f"Errors                       : {stats['errors']}")

    if dry_run:
        print("\n*** DRY RUN — No changes committed ***")
