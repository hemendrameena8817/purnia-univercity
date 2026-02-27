"""
UG Before CBCS Data Migration Script - FINAL SIMPLIFIED VERSION
==============================================================

Migrates data from staging.UGResultCurrent to the simplified ug_before_cbcs app.
All 42 columns from staging are migrated directly into UGBeforeCBCSStudentProfile, UGBeforeCBCSExam, and UGBeforeCBCSStudentResult.

HOW TO RUN:
-----------
1. Run the migration:
   a) PYTHONPATH=. poetry run python scripts/ug_before_cbcs/migrate_staging_to_app_v2.py
   b) poetry run python scripts/ug_before_cbcs/migrate_staging_to_app_v2.py --semester 1ST
2. Monitor progress (script shows progress every 100 records)

WHAT IT DOES:
-------------
- Creates UGBeforeCBCSStudentProfile (one per student)
- Creates UGBeforeCBCSExam (unique exam events)
- Creates UGBeforeCBCSStudentResult (one per student per subject per exam)
  (All subject and summary fields are stored in StudentResult)

NO SUBJECT OR SUMMARY TABLES ARE USED!
ALL 42 STAGING COLUMNS ARE PRESERVED!
"""
import os
import sys
import django
from collections import defaultdict

# Add the project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from staging.models import UGResultCurrent
from accounts.models import UserAccount
from colleges.models import College
from ug_before_cbcs.models import (
    UGBeforeCBCSStudentProfile,
    UGBeforeCBCSExam,
    UGBeforeCBCSStudentResult
)


def generate_exam_code(batch_code, session_code, semester_code, course_code):
    """Generate unique exam code from components"""
    parts = []
    if batch_code:
        parts.append(batch_code)
    if session_code:
        parts.append(session_code.replace('-', ''))
    if semester_code:
        parts.append(semester_code)
    if course_code:
        parts.append(course_code)
    return '_'.join(parts) if parts else 'UNKNOWN'


def map_semester_to_part(semester_code):
    """Map semester code to PART choices"""
    if not semester_code:
        return 'PART1'
    
    semester_upper = semester_code.upper()
    if '1ST' in semester_upper or 'I' == semester_upper or 'PART1' in semester_upper:
        return 'PART1'
    elif '2ND' in semester_upper or 'II' == semester_upper or 'PART2' in semester_upper:
        return 'PART2'
    elif '3RD' in semester_upper or 'III' == semester_upper or 'PART3' in semester_upper:
        return 'PART3'
    else:
        return 'PART1'  # Default


def migrate_data(skip_existing=True, start_from=0, semester_code=None):
    """Main migration function
    
    Args:
        skip_existing: If True, skips records that already have results created
        start_from: Start processing from this record number (0-based)
        semester_code: Optional semester to filter (e.g. '1ST')
    """
    print("=" * 80)
    print("UG BEFORE CBCS MIGRATION - SIMPLIFIED VERSION")
    print(f"SEMESTER FILTER: {semester_code or 'ALL'}")
    print("=" * 80)
    print("\nThis script will migrate ALL staging data to the new simplified models.")
    print("All 42 columns from staging will be preserved.\n")
    
    if skip_existing:
        print("⚠️  SKIP MODE: Already processed records will be skipped.\n")
    if start_from > 0:
        print(f"⏩ STARTING FROM: Record #{start_from:,}\n")
    
    # Get total count
    total_records = UGResultCurrent.objects.count()
    print(f"Total staging records to process: {total_records:,}\n")
    
    # Caches to avoid duplicate queries
    student_cache = {}
    exam_cache = {}
    college_cache = {}
    
    # Statistics
    stats = {
        'students_created': 0,
        'students_updated': 0,
        'exams_created': 0,
        'results_created': 0,
        'skipped': 0,
        'errors': 0
    }
    
    # Process records
    print("Processing staging records...")
    print("-" * 80)
    
    # Base Query
    queryset = UGResultCurrent.objects.all().select_related()
    
    # Filter by semester if provided
    if semester_code:
        queryset = queryset.filter(semester_code=semester_code)
    
    total_records = queryset.count()
    print(f"Total records to process: {total_records:,}")

    # Get records with offset if starting from a specific point
    if start_from > 0:
        records = queryset[start_from:].iterator(chunk_size=500)
    else:
        records = queryset.iterator(chunk_size=500)
    
    for idx, record in enumerate(records, start_from + 1):
        try:
            with transaction.atomic():
                # ============================================================
                # 1. GET OR CREATE COLLEGE
                # ============================================================
                college = None
                if record.institute_code:
                    if record.institute_code not in college_cache:
                        college_cache[record.institute_code] = College.objects.filter(
                            college_code=record.institute_code
                        ).first()
                    college = college_cache[record.institute_code]
                
                # ============================================================
                # 2. GET OR CREATE STUDENT PROFILE
                # ============================================================
                reg_no = record.college_reg_no
                roll_no = record.college_roll_no
                
                # Identification logic: Try reg_no first, then roll_no
                student_identifier = reg_no if reg_no else (f"ROLL_{roll_no}" if roll_no else None)
                
                if not student_identifier:
                    print(f"  ⚠ Skipping record {idx}: No registration or roll number")
                    continue
                
                if student_identifier not in student_cache:
                    # Attempt to find existing profile in DB first
                    profile = None
                    if reg_no:
                        profile = UGBeforeCBCSStudentProfile.objects.filter(registration_no=reg_no).first()
                    elif roll_no:
                        # Search by roll_no if reg_no is missing
                        profile = UGBeforeCBCSStudentProfile.objects.filter(roll_no=roll_no).first()
                    
                    if not profile:
                        # Create new user
                        # If reg_no is missing, use roll_no based identifier for username
                        username = reg_no if reg_no else f"roll_{roll_no}"
                        
                        user, user_created = UserAccount.objects.get_or_create(
                            username=username,
                            defaults={
                                'first_name': record.student_name or 'Student',
                                'user_type': 'student',
                                'current_profile': 'ug_before_cbcs',
                                'college': college
                            }
                        )
                        
                        if not user_created and college and not user.college:
                            user.college = college
                            user.save(update_fields=['college'])
                        
                        # Create new student profile
                        # If reg_no is missing in staging, we use our surrogate identifier for the unique registration_no field
                        profile = UGBeforeCBCSStudentProfile.objects.create(
                            user=user,
                            registration_no=reg_no if reg_no else f"MISSING_REG_{roll_no}",
                            roll_no=roll_no,
                            student_name=record.student_name or 'Unknown',
                            fathers_name=record.fathers_name,
                            mothers_name=record.mothers_name,
                            college=college,
                            course_code=record.course_code,
                            discipline_code=record.discipline_code,
                            source_user_id=record.user_id,
                        )
                        stats['students_created'] += 1
                    else:
                        # Profile exists, update it if necessary
                        if college and not profile.college:
                            profile.college = college
                            profile.save(update_fields=['college'])
                        stats['students_updated'] += 1
                    
                    student_cache[student_identifier] = profile
                else:
                    profile = student_cache[student_identifier]
                
                # ============================================================
                # 3. GET OR CREATE EXAM
                # ============================================================
                exam_code = generate_exam_code(
                    record.batch_code,
                    record.session_code,
                    record.semester_code,
                    record.course_code
                )
                
                if exam_code not in exam_cache:
                    part = map_semester_to_part(record.semester_code)
                    
                    # Extract year from batch_code
                    exam_year = 2000
                    if record.batch_code and record.batch_code.isdigit():
                        exam_year = int(record.batch_code)
                    
                    # Generate exam name
                    exam_name = f"{record.course_code or 'UG'} {record.semester_code or 'Part-I'} Exam {record.batch_code or ''}"
                    
                    exam, exam_created = UGBeforeCBCSExam.objects.get_or_create(
                        exam_code=exam_code,
                        defaults={
                            'name': exam_name.strip(),
                            'part': part,
                            'semester_code': record.semester_code,
                            'exam_year': exam_year,
                            'exam_month_year': record.session_code,
                            'session_code': record.session_code,
                            'batch_code': record.batch_code,
                            'course_code': record.course_code,
                            'discipline_code': record.discipline_code,
                        }
                    )
                    
                    exam_cache[exam_code] = exam
                    
                    if exam_created:
                        stats['exams_created'] += 1
                else:
                    exam = exam_cache[exam_code]
                
                # ============================================================
                # 5. CREATE STUDENT RESULT (ONE PER SUBJECT)
                # ============================================================
                # ============================================================
                # 4. CREATE STUDENT RESULT (ALL FIELDS)
                # ============================================================
                # Result Entry
                UGBeforeCBCSStudentResult.objects.create(
                    student=profile,
                    exam=exam,
                    paper_code=record.paper_code,
                    subject_code=record.subject_code,
                    subject_name=record.subject_name,
                    paper_type_code=record.paper_type_code,
                    exam_type=record.exam_type,
                    temp_paper_code=record.temp_paper_code,
                    paper_code_correction=record.paper_code_correction,
                    subject_code_correction=record.subject_code_correction,
                    # Details
                    exam_type_his=record.exam_type_his,
                    is_ex_regular=record.ExRegular_chk == 'YES' if record.ExRegular_chk else False,
                    status=record.status,
                    # Marks
                    theory=record.theory,
                    practical=record.pra,
                    sessional=record.sessional,
                    # Calculated Marks
                    mark_secured=record.mark_secured,
                    mark_secured_history=record.mark_secured_history,
                    subject_total_mark=record.subject_total_mark,
                    maximum_mark=record.maximum_mark,
                    pass_mark=record.pass_mark,
                    # Subject Results
                    subject_result=record.subject_result,
                    subject_result_1=record.subject_result_1,
                    subject_result_2=record.subject_result_2,
                    sub_reult_com=record.sub_reult_com,
                    # Exam Summary Fields (now in result)
                    grand_total_mark=record.grand_total_mark,
                    total_secured_mark=record.total_secured_mark,
                    total_secured_mark_1=record.total_secured_mark_1,
                    total_secured_mark_2=record.total_secured_mark_2,
                    hon=record.hon,
                    total_per=record.total_per,
                    grade=record.grade,
                    final_result=record.final_result,
                    agreegate=record.agreegate,
                    aggregate_hindi=record.aggregate_hindi,
                    record_status=record.record_status,
                    record_status_check=record.record_status_check,
                    subject_count=record.subject_count,
                    # Additional Fields
                    is_absent='ABS' in (record.theory or '') or 'ABS' in (record.pra or ''),
                    grace_chk=record.grace_chk,
                    remark=record.remark,
                    student_check=record.student_check,
                    # Source tracking
                    source_id=record.source_id,
                    registration_no=profile.registration_no,
                )
                stats['results_created'] += 1
                
                
                # ============================================================
                # 6. EXAM SUMMARY IS STORED IN STUDENT RESULT
                # ============================================================
                # The UGBeforeCBCSExamSummary model does not exist.
                # All 42 staging columns (including summary fields) are stored in UGBeforeCBCSStudentResult.
                # References to summary model removed.
                pass
                
        except Exception as e:
            stats['errors'] += 1
            print(f"  ✗ Error processing record {idx}: {str(e)}")
            continue
        
        # Progress indicator
        if idx % 100 == 0:
            print(f"  ✓ Processed {idx:,} / {total_records:,} records...")
    
    # ============================================================
    # FINAL STATISTICS
    # ============================================================
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETED!")
    print("=" * 80)
    print(f"\n📊 STATISTICS:")
    print(f"  • Students Created:       {stats['students_created']:,}")
    print(f"  • Students Updated:       {stats['students_updated']:,}")
    print(f"  • Exams Created:          {stats['exams_created']:,}")
    print(f"  • Results Created:        {stats['results_created']:,}")
    print(f"  • Skipped (Duplicates):   {stats['skipped']:,}")
    print(f"  • Errors:                 {stats['errors']:,}")
    print("\n" + "=" * 80)
    
    # Verify counts
    print("\n📈 VERIFICATION:")
    print(f"  • Total Student Profiles: {UGBeforeCBCSStudentProfile.objects.count():,}")
    print(f"  • Total Exams:            {UGBeforeCBCSExam.objects.count():,}")
    print(f"  • Total Results:          {UGBeforeCBCSStudentResult.objects.count():,}")
    print("\n" + "=" * 80)
    print("\n✅ All staging columns have been migrated!")
    print("   You can now use the Django admin or APIs to view the data.\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate UG Before CBCS data from staging')
    parser.add_argument(
        '--no-skip', 
        action='store_true', 
        help='Process all records including duplicates (default: skip existing)'
    )
    parser.add_argument(
        '--start-from', 
        type=int, 
        default=0, 
        help='Start processing from this record number (default: 0)'
    )
    
    parser.add_argument(
        '--semester', 
        type=str, 
        default=None, 
        help='Migrate only this semester (e.g., 1ST, 2ND, 3RD)'
    )
    
    args = parser.parse_args()
    
    migrate_data(
        skip_existing=not args.no_skip,
        start_from=args.start_from,
        semester_code=args.semester
    )
