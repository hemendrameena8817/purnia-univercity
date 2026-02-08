#!/usr/bin/env python
"""
Standalone script to create PGStudentCourseAssessment entries
for students who have passed or been promoted

Usage:
    python create_next_sem_assessments.py --semester 1ST --session 2024-25 --dry-run
    python create_next_sem_assessments.py --semester 1ST --session 2024-25  # Actually create
"""

import os
import sys
import django
import argparse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.services.create_next_semester_assessments import NextSemesterAssessmentService


def main():
    parser = argparse.ArgumentParser(
        description='Create PGStudentCourseAssessment entries for eligible students'
    )
    parser.add_argument(
        '--semester',
        required=True,
        help='Current semester (e.g., 1ST, 2ND, 3RD, 4TH)'
    )
    parser.add_argument(
        '--session',
        required=True,
        help='Academic session (e.g., 2024-25)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without saving to database'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of students to process'
    )
    parser.add_argument(
        '--student-id',
        type=int,
        default=None,
        help='Process only a specific student ID'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Next Semester Assessment Creation Service")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Semester: {args.semester}")
    print(f"  Session: {args.session}")
    print(f"  Dry Run: {args.dry_run}")
    print(f"  Limit: {args.limit or 'None'}")
    print(f"  Student ID: {args.student_id or 'All eligible students'}")
    print()
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be saved to database")
    else:
        print("⚠️  LIVE MODE - Changes will be saved to database")
        response = input("\nContinue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            return
    
    print("\n" + "-" * 80)
    
    # Process single student or all eligible students
    if args.student_id:
        result = NextSemesterAssessmentService.create_assessments_for_student(
            student_id=args.student_id,
            current_semester=args.semester,
            session=args.session,
            dry_run=args.dry_run
        )
        
        print("\n" + "=" * 80)
        print("RESULT")
        print("=" * 80)
        
        if result['success']:
            print(f"✓ Success!")
            print(f"  Student: {result['student_registration']}")
            print(f"  Current Semester: {result['current_semester']}")
            print(f"  Next Semester: {result['next_semester']}")
            print(f"  Next Session: {result['next_session']}")
            print(f"  Semester Result: {result['semester_result']}")
            print(f"  Assessments Created: {result['assessments_created']}")
        else:
            print(f"✗ Failed!")
            print(f"  Error: {result['error']}")
    else:
        results = NextSemesterAssessmentService.create_assessments_for_eligible_students(
            semester=args.semester,
            session=args.session,
            dry_run=args.dry_run,
            limit=args.limit
        )
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Eligible Students: {results['total_eligible']}")
        print(f"✓ Successful: {results['successful']}")
        print(f"✗ Failed: {results['failed']}")
        
        if results['errors']:
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results['errors'][:20]:
                print(f"  - Student {error['registration_no']}: {error['error']}")
            
            if len(results['errors']) > 20:
                print(f"  ... and {len(results['errors']) - 20} more errors")
    
    print("=" * 80)


if __name__ == '__main__':
    main()
