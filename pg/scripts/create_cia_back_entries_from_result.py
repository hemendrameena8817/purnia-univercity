#!/usr/bin/env python
"""
Create CIA Back Paper Entries based on PGExamResult

This script creates specific entries based on student semester result:
1. FAIL: Creates CIA Back Entries (PGStudentCourseAssessment) for ALL papers.
2. PROMOTED / DISQUALIFIED / PARTIALDISQUALIFIED: Creates Exam Registration (PGExamRegistration).

Filtering options:
  --semester          : Semester (e.g. 1ST, 2ND)
  --source-session    : Session of the failed result (e.g. 2023-24)
  --target-session    : Session for new back entries (e.g. 2024-25)
  --batch             : (Optional) Filter by batch name
  --registration-no   : (Optional) Process a single student by enrollment/registration no

Usage:
    # All students dry run
    python pg/scripts/create_cia_back_entries_from_result.py --semester 1ST --source-session 2023-24 --target-session 2024-25 --dry-run

    # Single student dry run
    python pg/scripts/create_cia_back_entries_from_result.py --semester 1ST --source-session 2023-24 --target-session 2024-25 --registration-no PU2024001 --dry-run

    # Execute (production)
    python pg/scripts/create_cia_back_entries_from_result.py --semester 1ST --source-session 2023-24 --target-session 2024-25 --execute
"""

import os
import sys
import django
import argparse
from pathlib import Path

# Setup Django — works on ANY machine (local, AWS, etc.)
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # pg/scripts/ → pg/ → project root
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from django.db.models import Q
from pg.models import PGStudentCourseAssessment, PGExamResult, PGExamRegistration


def create_cia_back_entries(semester, source_session, target_session, batch=None, registration_no=None, dry_run=True):
    print("=" * 100)
    print("CREATE CIA BACK PAPER ENTRIES & EXAM REGISTRATION")
    print("=" * 100)
    print(f"Registration No : {registration_no if registration_no else 'ALL'}")
    print(f"Batch           : {batch if batch else 'ALL'}")
    print(f"Semester        : {semester}")
    print(f"Source Session  : {source_session}")
    print(f"Target Session  : {target_session}")
    print(f"Mode            : {'DRY RUN (Preview)' if dry_run else 'EXECUTE (Save to DB)'}")
    print("=" * 100)

    sem_map = {'1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4}
    sem_int = sem_map.get(semester.upper(), 0)

    # ── Build base query ──────────────────────────────────────────────────────
    print(f"\nScanning PGExamResult for FAIL, PROMOTED, DISQUALIFIED, PARTIALDISQUALIFIED...")

    results_qs = PGExamResult.objects.filter(
        semester=semester,
        session=source_session,
    ).select_related('student')

    if registration_no:
        results_qs = results_qs.filter(student__registration_no=registration_no)
        print(f"🔍 Single student mode: {registration_no}")

    if batch:
        results_qs = results_qs.filter(student__batch=batch)

    target_statuses = ['FAIL', 'PROMOTED', 'DISQUALIFIED', 'PARTIALDISQUALIFIED']
    failed_results = results_qs.filter(
        Q(semester_result__in=target_statuses) | Q(cia_pass=False)
    )

    count_failures = failed_results.count()
    print(f"Found {count_failures} students matching criteria.")

    if count_failures == 0:
        print("No matching students found. Exiting.")
        return

    total_cia_created = 0
    total_reg_created = 0
    students_processed = 0

    for result in failed_results.iterator(chunk_size=200):
        student = result.student
        reg_no  = student.registration_no
        status  = result.semester_result
        cia_failed = (result.cia_pass is False)

        print(f"\nProcessing {reg_no} | Status: {status} | CIA Fail: {cia_failed}")
        students_processed += 1

        # ── STEP A: CIA Back entries (only for FAIL) ──────────────────────────
        if status == 'FAIL' or cia_failed:
            reason = "FAIL" if status == 'FAIL' else "CIA fail flag"
            print(f"   → Creating CIA Back entries  (reason: {reason})")

            original_cia = PGStudentCourseAssessment.objects.filter(
                student=student,
                semester=semester,
                session=source_session,
                label__icontains='CIA'
            )

            if not original_cia.exists():
                print(f"     ⚠️  No original CIA assessments found.")
            else:
                for assessment in original_cia:
                    exists = PGStudentCourseAssessment.objects.filter(
                        student=student,
                        semester=semester,
                        session=target_session,
                        paper_code=assessment.paper_code,
                        label=assessment.label,
                        exam_type='Back'
                    ).exists()

                    if exists:
                        print(f"     [Skip]   {assessment.paper_code} back entry already exists")
                        continue

                    if not dry_run:
                        with transaction.atomic():
                            PGStudentCourseAssessment.objects.create(
                                student=student,
                                course_name=assessment.course_name,
                                course_short_name=assessment.course_short_name,
                                course_type=assessment.course_type,
                                course_code=assessment.course_code,
                                paper_code=assessment.paper_code,
                                semester=semester,
                                label=assessment.label,
                                department=assessment.department,
                                degree=assessment.degree,
                                session=target_session,
                                batch=assessment.batch,
                                college_code=assessment.college_code,
                                exam_type='Back',
                                ind_max_marks=assessment.ind_max_marks,
                                ind_pass_marks=assessment.ind_pass_marks,
                                ind_marks_obtained=None,
                                ind_is_absent=False,
                                ind_is_pass=None,
                                is_cia_fill=False,
                                is_ese_fill=False,
                            )
                        print(f"     [Created] {assessment.paper_code} Back entry")
                    else:
                        print(f"     [Would Create] {assessment.paper_code} Back entry")
                    total_cia_created += 1
        else:
            print(f"   [Skip] CIA Back (status '{status}' not FAIL)")

        # ── STEP B: Exam Registration (PROMOTED / DISQUALIFIED) ───────────────
        if status in ['PROMOTED', 'DISQUALIFIED', 'PARTIALDISQUALIFIED']:
            reg_exists = PGExamRegistration.objects.filter(
                student=student,
                sem=sem_int,
                session=target_session,
                exam_type='BACK'
            ).exists()

            if reg_exists:
                print(f"   [Skip] PGExamRegistration (Back) already exists")
            else:
                if not dry_run:
                    PGExamRegistration.objects.create(
                        student=student,
                        sem=sem_int,
                        session=target_session,
                        exam_type='BACK',
                        status='open'
                    )
                    print(f"   [Created] PGExamRegistration (Back)")
                else:
                    print(f"   [Would Create] PGExamRegistration (Back)")
                total_reg_created += 1
        else:
            print(f"   [Skip] PGExamRegistration (status '{status}' excluded)")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Students Processed        : {students_processed}")
    print(f"CIA Back Entries {'Created' if not dry_run else 'Proposed'} : {total_cia_created}")
    print(f"Exam Registrations {'Created' if not dry_run else 'Proposed'}: {total_reg_created}")

    if dry_run:
        print("\n🔍 DRY RUN COMPLETE. Use --execute to save changes.")
    else:
        print("\n✅ EXECUTION COMPLETE.")


def main():
    parser = argparse.ArgumentParser(
        description='Create CIA Back Entries & Exam Registration from PGExamResult',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--semester',        type=str, required=True,  help='Semester (e.g. 1ST, 2ND)')
    parser.add_argument('--source-session',  type=str, required=True,  help='Source session of failed result (e.g. 2023-24)')
    parser.add_argument('--target-session',  type=str, required=True,  help='Target session for back entries (e.g. 2024-25)')
    parser.add_argument('--batch',           type=str, required=False, help='Filter by batch (optional)')
    parser.add_argument('--registration-no', type=str, required=False, help='Process single student by enrollment/registration no')
    parser.add_argument('--execute',         action='store_true',      help='Save changes to database')
    parser.add_argument('--dry-run',         action='store_true',      help='Preview without saving (default)')

    args = parser.parse_args()
    dry_run = not args.execute or args.dry_run

    if not dry_run:
        confirm = input("\n⚠️  WARNING: This will write to the database. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return

    create_cia_back_entries(
        semester=args.semester,
        source_session=args.source_session,
        target_session=args.target_session,
        batch=args.batch,
        registration_no=args.registration_no,
        dry_run=dry_run,
    )


if __name__ == '__main__':
    main()
