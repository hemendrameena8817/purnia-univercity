#!/usr/bin/env python
"""
Create CIA Back Paper Entries for PENDING Results with CIA Fail

This script identifies students who have:
1. semester_result = 'PENDING'
2. cia_pass = False

For these students, it creates CIA Back Entries (PGStudentCourseAssessment) for ALL papers.
It does NOT create Exam Registrations.

Usage:
    python pg/scripts/create_cia_back_for_pending_fail.py --semester 1ST --source-session 2023-24 --target-session 2024-25 --batch 2023-25 --dry-run
    python pg/scripts/create_cia_back_for_pending_fail.py --semester 1ST --source-session 2023-24 --target-session 2024-25 --batch 2023-25 --execute
"""

import os
import sys
import django
import argparse

# Setup Django
sys.path.append('/home/gaurav/Desktop/purniya/pup-umis-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from pg.models import PGStudentCourseAssessment, PGExamResult

def create_cia_back_for_pending(semester, source_session, target_session, batch=None, dry_run=True):
    print("=" * 100)
    print("CREATE CIA BACK ENTRIES FOR PENDING + CIA FAIL")
    print("=" * 100)
    print(f"Batch: {batch if batch else 'ALL'}")
    print(f"Semester: {semester}")
    print(f"Source Session (Failure): {source_session}")
    print(f"Target Session (Back Attempt): {target_session}")
    print(f"Mode: {'DRY RUN (Preview)' if dry_run else 'EXECUTE (Save to DB)'}")
    print("=" * 100)

    # Helper to convert "1ST" -> 1
    sem_map = {
        '1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4
    }
    
    # 1. Find Students based on Result Status
    print(f"\nScanning PGExamResult for PENDING + CIA FAIL...")
    
    from django.db.models import Q
    
    # Base Query
    results_qs = PGExamResult.objects.filter(
        semester=semester,
        session=source_session
    )
    
    if batch:
        results_qs = results_qs.filter(student__batch=batch)
        
    # Filter: Status is PENDING AND cia_pass is False
    pending_failed_results = results_qs.filter(
        semester_result='PENDING',
        cia_pass=False
    ).select_related('student')
    
    count_failures = pending_failed_results.count()
    print(f"Found {count_failures} students matching criteria.")
    
    if count_failures == 0:
        print("No matching students found. Exiting.")
        return

    total_cia_created = 0
    students_processed = 0
    
    for result in pending_failed_results:
        student = result.student
        reg_no = student.registration_no
        status = result.semester_result
        cia_failed = (result.cia_pass is False)
        
        print(f"\nProcessing {reg_no} (Status: {status}, CIA Fail: {cia_failed})...")
        students_processed += 1
        
        # ---------------------------------------------------------------------
        # STEP A: Create CIA Back Entries
        # Logic: Always true for this script's filter
        # ---------------------------------------------------------------------
        print(f"   - [Check] Generating CIA Back entries...")
        
        # Get ALL CIA papers for this student in the source session
        original_cia_assessments = PGStudentCourseAssessment.objects.filter(
            student=student,
            semester=semester,
            session=source_session,
            label__icontains='CIA'
        )
        
        if not original_cia_assessments.exists():
            print(f"     ⚠️  No original CIA assessments found to copy.")
        else:
            for assessment in original_cia_assessments:
                # Check for duplicates in target session
                exists = PGStudentCourseAssessment.objects.filter(
                    student=student,
                    semester=semester,
                    session=target_session,
                    paper_code=assessment.paper_code,
                    label=assessment.label,
                    exam_type='Back'
                ).exists()
                
                if exists:
                    print(f"     - [Skip] {assessment.paper_code}: Back Entry already exists.")
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
                            session=target_session,  # NEW SESSION
                            batch=assessment.batch,
                            college_code=assessment.college_code,
                            exam_type='Back',        # BACK TYPE
                            
                            ind_max_marks=assessment.ind_max_marks,
                            ind_pass_marks=assessment.ind_pass_marks,
                            
                            # Reset results
                            ind_marks_obtained=None,
                            ind_is_absent=False,
                            ind_is_pass=None,
                            is_cia_fill=False,
                            is_ese_fill=False
                        )
                    print(f"     - [Created] {assessment.paper_code} Back")
                    total_cia_created += 1
                else:
                    print(f"     - [Would Create] {assessment.paper_code} Back")
                    total_cia_created += 1

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Students Processed: {students_processed}")
    print(f"CIA Back Entries {'Created' if not dry_run else 'Proposed'}: {total_cia_created}")
    
    if dry_run:
        print("\n🔍 DRY RUN COMPLETE. Use --execute to save changes.")
    else:
        print("\n✅ EXECUTION COMPLETE.")

def main():
    parser = argparse.ArgumentParser(description='Create CIA Back Entries for PENDING + CIA Fail')
    parser.add_argument('--semester', type=str, required=True, help='Semester (e.g. 1ST)')
    parser.add_argument('--source-session', type=str, required=True, help='Source Session (e.g. 2023-24)')
    parser.add_argument('--target-session', type=str, required=True, help='Target Session (e.g. 2024-25)')
    parser.add_argument('--batch', type=str, required=False, help='Batch (Optional)')
    parser.add_argument('--execute', action='store_true', help='Execute changes')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    
    args = parser.parse_args()
    dry_run = not args.execute or args.dry_run
    
    if not dry_run:
         confirm = input("\n⚠️  WARNING: This will populate the database. Continue? (yes/no): ")
         if confirm.lower() != 'yes':
             print("Aborted.")
             return
             
    create_cia_back_for_pending(
        semester=args.semester,
        source_session=args.source_session,
        target_session=args.target_session,
        batch=args.batch,
        dry_run=dry_run
    )

if __name__ == '__main__':
    main()
