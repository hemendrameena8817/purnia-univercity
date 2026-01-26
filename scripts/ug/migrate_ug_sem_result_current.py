"""
Migrate UG Semester Result data from staging.UGSemResultCurrent to ug.StudentCourseAssessment.

This script:
1. Looks up course_type (MJC/MIC/MDC) from existing CourseStructure by subject_name
2. Preserves faculty field as-is from staging data
3. Creates StudentCourseAssessment records with proper field mappings
4. Updates UG student profiles with major/minor/MDC courses
5. Stores complete staging record in json_data
6. Generates CSV report of failed records

Usage:
    poetry run python scripts/ug/migrate_ug_sem_result_current.py
    
    # Or with limit for testing:
    poetry run python manage.py shell -c "exec(open('scripts/ug/migrate_ug_sem_result_current.py').read()); migrate_data(limit=100)"
"""
import os
import sys
import django
import csv
from datetime import datetime
from collections import defaultdict

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pupumis.settings')
django.setup()

from django.db import transaction
from staging.models import UGSemResultCurrent, DisciplineMaster
from ug.models import (
    UGStudentProfile, StudentCourseAssessment, CourseStructure,
    UGDepartment, UGBatch
)

BATCH_SIZE = 2000  # Increased for better performance


def safe_int(value, default=None):
    """Safely convert value to int."""
    if value is None or value == '':
        return default
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default


def get_course_type_from_structure(subject_name, semester, department, courses_cache):
    """
    Look up course_type from existing CourseStructure.
    The CourseStructure already has course_type properly set (MJC, MIC, MDC, etc.)
    from the master data import.
    """
    if not subject_name:
        return 'GEN'
    
    # Try to find in cache
    key = (
        subject_name.lower().strip(),
        str(semester) if semester else '',
        department.id if department else None
    )
    
    course = courses_cache.get(key)
    if course and course.course_type:
        return course.course_type
    
    # Try without department
    key_no_dept = (
        subject_name.lower().strip(),
        str(semester) if semester else '',
        None
    )
    course = courses_cache.get(key_no_dept)
    if course and course.course_type:
        return course.course_type
    
    return 'GEN'  # Default if not found


def build_caches():
    """Pre-load data into memory for fast lookups."""
    print("📦 Building caches...")
    
    # Cache students by registration number
    students_cache = {}
    for student in UGStudentProfile.objects.all().iterator(chunk_size=5000):
        students_cache[student.registration_no] = student
    print(f"   Cached {len(students_cache):,} students")
    
    # Cache departments by discipline_code
    departments_cache = {}
    for discipline in DisciplineMaster.objects.all().iterator(chunk_size=1000):
        if discipline.discipline_code and discipline.discipline_name:
            # Find matching department
            dept = UGDepartment.objects.filter(name__iexact=discipline.discipline_name.strip()).first()
            if dept:
                departments_cache[discipline.discipline_code] = dept
    print(f"   Cached {len(departments_cache):,} department mappings")
    
    # Cache batches
    batches_cache = {}
    for batch in UGBatch.objects.all():
        batches_cache[batch.name] = batch
    print(f"   Cached {len(batches_cache):,} batches")
    
    # Cache course structures by (name, semester, department)
    courses_cache = {}
    for course in CourseStructure.objects.select_related('department').all().iterator(chunk_size=5000):
        key = (
            course.name.lower() if course.name else '',
            str(course.semester) if course.semester else '',
            course.department_id if course.department_id else None
        )
        courses_cache[key] = course
    print(f"   Cached {len(courses_cache):,} course structures\n")
    
    return students_cache, departments_cache, batches_cache, courses_cache


def migrate_data(limit=None, clear_existing=False, dry_run=False):
    """
    Migrate data from UGSemResultCurrent to StudentCourseAssessment.
    
    Args:
        limit: Optional limit on number of records to process (for testing)
        clear_existing: If True, delete all existing StudentCourseAssessment records
        dry_run: If True, don't actually save data (for testing)
    """
    print(f"\n{'='*80}")
    print(f"Migrating UG Semester Results to StudentCourseAssessment")
    if dry_run:
        print(f"🔍 DRY RUN MODE - No data will be saved")
    print(f"{'='*80}\n")
    
    if clear_existing and not dry_run:
        print("🗑️  Clearing existing StudentCourseAssessment records...")
        deleted_count = StudentCourseAssessment.objects.all().delete()[0]
        print(f"   Deleted {deleted_count} existing records\n")
    
    # Build caches for fast lookups
    students_cache, departments_cache, batches_cache, courses_cache = build_caches()
    
    # Get staging records
    queryset = UGSemResultCurrent.objects.filter(is_migrated=False).select_related()
    if limit:
        queryset = queryset[:limit]
        print(f"📊 Processing {limit} records (test mode)\n")
    else:
        total_count = queryset.count()
        print(f"📊 Total records to migrate: {total_count:,}\n")
    
    # Tracking
    stats = {
        'processed': 0,
        'created': 0,
        'skipped_no_student': 0,
        'skipped_no_dept': 0,
        'skipped_errors': 0,
        'batches_created': 0,
        'profiles_updated': 0,
    }
    
    # Track student course updates
    student_course_tracking = defaultdict(lambda: {'MJC': False, 'MIC': False, 'MDC': False})
    students_to_update = {}
    
    batch = []
    updated_staging_ids = []
    error_records = []  # For CSV export
    
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    error_file = f"migration_errors_{timestamp}.csv"
    
    print("🚀 Starting migration...\n")
    
    for staging_record in queryset.iterator(chunk_size=BATCH_SIZE):
        stats['processed'] += 1
        
        try:
            # 1. Find student from cache
            reg_no = staging_record.college_reg_no
            if not reg_no:
                stats['skipped_no_student'] += 1
                error_records.append({
                    'source_id': staging_record.source_id,
                    'reg_no': reg_no or 'MISSING',
                    'student_name': staging_record.student_name,
                    'subject': staging_record.subject_name,
                    'error': 'Missing registration number'
                })
                continue
            
            student = students_cache.get(reg_no)
            if not student:
                stats['skipped_no_student'] += 1
                error_records.append({
                    'source_id': staging_record.source_id,
                    'reg_no': reg_no,
                    'student_name': staging_record.student_name,
                    'subject': staging_record.subject_name,
                    'error': 'Student not found in database'
                })
                continue
            
            # 2. Get department from cache
            department = departments_cache.get(staging_record.discipline_code)
            # Note: Department can be None - we'll continue processing
            
            # 3. Get or create batch from cache
            batch_obj = None
            if staging_record.batch_code:
                batch_name = str(staging_record.batch_code).strip()
                if batch_name in batches_cache:
                    batch_obj = batches_cache[batch_name]
                else:
                    # Create new batch
                    batch_obj = UGBatch.objects.create(name=batch_name)
                    batches_cache[batch_name] = batch_obj
                    stats['batches_created'] += 1
            
            # 4. Get course type from CourseStructure
            course_type = get_course_type_from_structure(
                staging_record.subject_name,
                staging_record.semester_code,
                department,
                courses_cache
            )
            
            # 5. Prepare StudentCourseAssessment data
            assessment_data = {
                'student': student,
                'name': staging_record.subject_name,
                'course_type': course_type,
                'code': staging_record.subject_code,
                'paper_code': staging_record.paper_code,
                'semester': staging_record.semester_code,
                'max_marks': safe_int(staging_record.maximum_mark),
                'min_mark': safe_int(staging_record.pass_mark),
                'marks_obtained': safe_int(staging_record.mark_secured),
                'credit_obtained': safe_int(staging_record.subject_ce),
                'grade': staging_record.let_grad_sub,
                'numeric_grade': safe_int(staging_record.numrical_let_grad),
                'exam_type': staging_record.exam_type,
                'exam_result': staging_record.subject_result,
                'session': staging_record.session_code,
                'batch': batch_obj,
                'department': department,
                'degree': staging_record.course_code,
                'label': staging_record.status or 'UNKNOWN',
                'json_data': {
                    'source_id': staging_record.source_id,
                    'user_id': staging_record.user_id,
                    'college_roll_no': staging_record.college_roll_no,
                    'college_reg_no': staging_record.college_reg_no,
                    'student_name': staging_record.student_name,
                    'fathers_name': staging_record.fathers_name,
                    'mothers_name': staging_record.mothers_name,
                    'subject_total_mark': staging_record.subject_total_mark,
                    'grace_given': staging_record.grace_given,
                    'final_mark': staging_record.final_mark,
                    'subject_ca': staging_record.subject_ca,
                    'subject_ng': staging_record.subject_ng,
                    'subject_gp': staging_record.subject_gp,
                    'total_gp': staging_record.total_gp,
                    'total_ca': staging_record.total_ca,
                    'total_ce': staging_record.total_ce,
                    'final_result': staging_record.final_result,
                    'final_status': staging_record.final_status,
                    'gpa': staging_record.gpa,
                    'cgpa': staging_record.cgpa,
                    'institute_code': staging_record.institute_code,
                    'faculty': staging_record.faculty,
                }
            }
            
            # Create assessment object
            assessment = StudentCourseAssessment(**assessment_data)
            batch.append(assessment)
            
            # 6. Track student profile updates (only once per course type)
            student_key = student.id
            if course_type == 'MJC' and not student_course_tracking[student_key]['MJC']:
                if student_key not in students_to_update:
                    students_to_update[student_key] = student
                student.major_course = staging_record.subject_name
                student_course_tracking[student_key]['MJC'] = True
            elif course_type == 'MIC' and not student_course_tracking[student_key]['MIC']:
                if student_key not in students_to_update:
                    students_to_update[student_key] = student
                student.minor_course = staging_record.subject_name
                student_course_tracking[student_key]['MIC'] = True
            elif course_type == 'MDC' and not student_course_tracking[student_key]['MDC']:
                if student_key not in students_to_update:
                    students_to_update[student_key] = student
                student.mdc_course = staging_record.subject_name
                student_course_tracking[student_key]['MDC'] = True
            
            updated_staging_ids.append(staging_record.id)
            
            # Bulk insert when batch is full
            if len(batch) >= BATCH_SIZE:
                if not dry_run:
                    with transaction.atomic():
                        StudentCourseAssessment.objects.bulk_create(
                            batch, 
                            ignore_conflicts=True
                        )
                        stats['created'] += len(batch)
                        
                        # Update student profiles
                        if students_to_update:
                            UGStudentProfile.objects.bulk_update(
                                list(students_to_update.values()),
                                ['major_course', 'minor_course', 'mdc_course']
                            )
                            stats['profiles_updated'] += len(students_to_update)
                        
                        # Mark staging records as migrated
                        UGSemResultCurrent.objects.filter(id__in=updated_staging_ids).update(
                            is_migrated=True
                        )
                else:
                    stats['created'] += len(batch)
                    stats['profiles_updated'] += len(students_to_update)
                
                batch = []
                updated_staging_ids = []
                students_to_update.clear()
                student_course_tracking.clear()
                
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = stats['processed'] / elapsed if elapsed > 0 else 0
                print(f"   Processed {stats['processed']:,} | Created {stats['created']:,} | Rate: {rate:.0f} rec/sec")
        
        except Exception as e:
            stats['skipped_errors'] += 1
            error_records.append({
                'source_id': staging_record.source_id,
                'reg_no': staging_record.college_reg_no or 'N/A',
                'student_name': staging_record.student_name,
                'subject': staging_record.subject_name,
                'error': str(e)
            })
    
    # Insert remaining batch
    if batch and not dry_run:
        with transaction.atomic():
            StudentCourseAssessment.objects.bulk_create(
                batch,
                ignore_conflicts=True
            )
            stats['created'] += len(batch)
            
            # Update student profiles
            if students_to_update:
                UGStudentProfile.objects.bulk_update(
                    list(students_to_update.values()),
                    ['major_course', 'minor_course', 'mdc_course']
                )
                stats['profiles_updated'] += len(students_to_update)
            
            # Mark staging records as migrated
            UGSemResultCurrent.objects.filter(id__in=updated_staging_ids).update(
                is_migrated=True
            )
    elif batch:
        stats['created'] += len(batch)
        stats['profiles_updated'] += len(students_to_update)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Write error records to CSV
    if error_records:
        with open(error_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['source_id', 'reg_no', 'student_name', 'subject', 'error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(error_records)
        print(f"\n📄 Error report saved to: {error_file}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"Migration Complete")
    print(f"{'='*80}")
    print(f"✅ Records processed: {stats['processed']:,}")
    print(f"✅ Assessments created: {stats['created']:,}")
    print(f"✅ Student profiles updated: {stats['profiles_updated']:,}")
    print(f"✅ Batches created: {stats['batches_created']:,}")
    print(f"⚠️  Skipped (no student): {stats['skipped_no_student']:,}")
    print(f"⚠️  Skipped (no dept): {stats['skipped_no_dept']:,}")
    print(f"❌ Errors: {stats['skipped_errors']:,}")
    if error_records:
        print(f"📄 Error records exported to: {error_file}")
    print(f"⏱️  Time: {elapsed:.1f} seconds ({stats['processed']/elapsed:.0f} rec/sec)" if elapsed > 0 else "")
    print(f"\n📊 Current totals:")
    print(f"   StudentCourseAssessment: {StudentCourseAssessment.objects.count():,}")
    print(f"   CourseStructure: {CourseStructure.objects.count():,}")
    print()
    
    return stats


if __name__ == '__main__':
    migrate_data()
