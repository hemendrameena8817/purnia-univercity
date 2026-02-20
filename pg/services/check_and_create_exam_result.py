"""
Service: check_and_create_exam_result.py

Check if all CIA entries are passed for a student and create PGExamResult if not already present.
If PGExamResult already exists → SKIP (no update).

Logic:
1. Get target students (by batch, session, or single registration_no)
2. For each student, check CIA assessments for the semester
3. If ALL CIA papers are passed → create PGExamResult (cia_pass=True)
4. If ANY CIA paper is failed → create PGExamResult (cia_pass=False)
5. If PGExamResult already exists for student+semester+session → SKIP

Usage:
    # Batch - Dry run
    python pg/services/run_check_and_create_exam_result.py --batch 2024-26 --semester 3RD --session 2024-25 --dry-run

    # Batch - Production
    python pg/services/run_check_and_create_exam_result.py --batch 2024-26 --semester 3RD --session 2024-25

    # Single student - Dry run
    python pg/services/run_check_and_create_exam_result.py --semester 3RD --session 2024-25 --registration-no PU2024001 --dry-run

    # Single student - Production
    python pg/services/run_check_and_create_exam_result.py --semester 3RD --session 2024-25 --registration-no PU2024001

    # All batches in session
    python pg/services/run_check_and_create_exam_result.py --semester 3RD --session 2024-25 --include-all-batches --dry-run
    # Single student - Dry run (pehle yahi karein)
python pg/services/run_check_and_create_exam_result.py \
    --semester 3RD --session 2024-25 \
    --registration-no PU2024001 --dry-run

# Single student - Production
python pg/services/run_check_and_create_exam_result.py \
    --semester 3RD --session 2024-25 \
    --registration-no PU2024001

# Full batch - Dry run
python pg/services/run_check_and_create_exam_result.py \
    --batch 2024-26 --semester 3RD --session 2024-25 --dry-run

# All batches - Dry run
python pg/services/run_check_and_create_exam_result.py \
    --semester 3RD --session 2024-25 --include-all-batches --dry-run
"""

from decimal import Decimal
from django.db import transaction

from pg.models import (
    PGStudentProfile,
    PGStudentCourseAssessment,
    PGExamResult,
)


SEM_MAP = {
    '1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4,
    '1': 1, '2': 2, '3': 3, '4': 4,
}


def _all_cia_passed(student, semester, session):
    """
    Returns True if the student has passed ALL CIA papers for the
    given semester+session. Returns False if any paper is failed/absent.
    Returns None if there are no CIA entries at all.
    """
    cia_entries = PGStudentCourseAssessment.objects.filter(
        student=student,
        semester=semester,
        session=session,
        label__icontains='CIA',
    )

    if not cia_entries.exists():
        return None  # No CIA data found

    # Group by paper_code — need at least one pass per paper
    papers = {}
    for entry in cia_entries:
        key = entry.paper_code or entry.course_code or ''
        if key not in papers:
            papers[key] = []
        papers[key].append(entry)

    for code, entries in papers.items():
        paper_ok = False
        for entry in entries:
            if entry.ind_is_absent:
                is_pass = False
            elif entry.ind_marks_obtained is not None and entry.ind_pass_marks is not None:
                is_pass = entry.ind_marks_obtained >= entry.ind_pass_marks
            else:
                is_pass = False

            if is_pass:
                paper_ok = True
                break

        if not paper_ok:
            return False  # At least one paper not cleared

    return True  # All papers cleared


def check_and_create_exam_results(
    batch=None,
    semester=None,
    session=None,
    registration_no=None,
    include_all_batches=False,
    dry_run=False,
):
    """
    Main entry point.
    """
    stats = {
        'total': 0,
        'no_cia_data': 0,
        'cia_pass': 0,
        'cia_fail': 0,
        'created': 0,
        'skipped_exists': 0,
    }

    print("\n" + "=" * 80)
    print("📋 CHECK & CREATE PGExamResult (Skip if exists)")
    print("=" * 80)
    print(f"  Semester : {semester}")
    print(f"  Session  : {session}")
    if registration_no:
        print(f"  Student  : {registration_no} (single)")
    elif batch and not include_all_batches:
        print(f"  Batch    : {batch}")
    else:
        print(f"  Scope    : ALL batches in session")
    print(f"  Dry Run  : {dry_run}")
    print("=" * 80)

    # ── Get target students ────────────────────────────────────────────────────
    if registration_no:
        students = PGStudentProfile.objects.filter(registration_no=registration_no)
    elif batch and not include_all_batches:
        students = PGStudentProfile.objects.filter(
            batch=batch,
            course_assessments__semester=semester,
            course_assessments__session=session,
        ).distinct()
    else:
        students = PGStudentProfile.objects.filter(
            course_assessments__semester=semester,
            course_assessments__session=session,
        ).distinct()

    total = students.count()
    stats['total'] = total
    print(f"\n  Found {total:,} students to process\n")

    def _process(student, dry_run):
        cia_result = _all_cia_passed(student, semester, session)

        if cia_result is None:
            stats['no_cia_data'] += 1
            print(f"  ⚠️  {student.registration_no} — No CIA data, skipping")
            return

        if cia_result:
            stats['cia_pass'] += 1
        else:
            stats['cia_fail'] += 1

        # Check if PGExamResult already exists
        exists = PGExamResult.objects.filter(
            student=student,
            semester=semester,
            session=session,
        ).exists()

        if exists:
            stats['skipped_exists'] += 1
            print(f"  ⏭️  {student.registration_no} — PGExamResult EXISTS, skipping")
            return

        # Create
        status_icon = "✅" if cia_result else "❌"
        print(f"  {status_icon} {student.registration_no} — CIA {'PASS' if cia_result else 'FAIL'} → Creating PGExamResult")

        if not dry_run:
            PGExamResult.objects.create(
                student=student,
                semester=semester,
                session=session,
                cia_pass=cia_result,
                semester_result='PENDING',
                semester_max_credit=0,
                semester_credit_earned=0,
                sgpa=Decimal('0.00'),
                is_legacy=False,
            )
        stats['created'] += 1

    # ── Process ────────────────────────────────────────────────────────────────
    if dry_run:
        print("🔍 DRY RUN — no DB changes\n")
        for student in students.iterator():
            _process(student, dry_run=True)
    else:
        with transaction.atomic():
            for student in students.iterator():
                _process(student, dry_run=False)

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"  Total students      : {stats['total']:,}")
    print(f"  No CIA data         : {stats['no_cia_data']:,}")
    print(f"  CIA PASS            : {stats['cia_pass']:,}")
    print(f"  CIA FAIL            : {stats['cia_fail']:,}")
    print(f"  Skipped (exists)    : {stats['skipped_exists']:,}")
    print(f"  PGExamResult created: {stats['created']:,}")
    if dry_run:
        print("\n  *** DRY RUN — no changes committed ***")
    print("=" * 80)

    return stats
