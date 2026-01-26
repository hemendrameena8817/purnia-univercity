import os
import sys
import django
import csv
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from django.db import transaction
from staging.models import UGSemResultCurrent, DisciplineMaster
from ug.models import (
    UGStudentProfile, StudentCourseAssessment,
    UGDepartment, UGBatch
)

BATCH_SIZE = 5000  # Optimized batch size

common_course_structure_data = [
    # Semester-I
    {"semester": "Semester-I", "course_name": "Major Course 1", "course_type": "MJC-1", "ltp": "6-1-0", "credit": 6, "marks": 100, "code":"1001"},
    {"semester": "Semester-I", "course_name": "Minor Course 1", "course_type": "MIC-1", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"1002"},
    {"semester": "Semester-I", "course_name": "Multidisciplinary Course 1", "course_type": "MDC-1", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"1003"},
    {"semester": "Semester-I", "course_name": "MIL", "course_type": "AEC-1", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"1004"},
    {"semester": "Semester-I", "course_name": "Skill Enhancement Course", "course_type": "SEC-1", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"1005"},
    {"semester": "Semester-I", "course_name": "Value Added Course", "course_type": "VAC-1", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"1006"},
    
    # Semester-II
    {"semester": "Semester-II", "course_name": "Major Course 2", "course_type": "MJC-2", "ltp": "6-1-0", "credit": 6, "marks": 100, "code":"2001"},
    {"semester": "Semester-II", "course_name": "Minor Course 2", "course_type": "MIC-2", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"2002"},
    {"semester": "Semester-II", "course_name": "Multidisciplinary Course 2", "course_type": "MDC-2", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"2003"},
    {"semester": "Semester-II", "course_name": "Environmental Science", "course_type": "AEC-2", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"2004"},
    {"semester": "Semester-II", "course_name": "Skill Enhancement Course", "course_type": "SEC-2", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"2005"},
    {"semester": "Semester-II", "course_name": "Value Added Course", "course_type": "VAC-2", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"2006"},

    # Semester-III
    {"semester": "Semester-III", "course_name": "Major Course 3", "course_type": "MJC-3", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"3001"},
    {"semester": "Semester-III", "course_name": "Major Course 4", "course_type": "MJC-4", "ltp": "3-1-0", "credit": 4, "marks": 100, "code":"3002"},
    {"semester": "Semester-III", "course_name": "Minor Course 3", "course_type": "MIC-3", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"3003"},
    {"semester": "Semester-III", "course_name": "Multidisciplinary Course 3", "course_type": "MDC-3", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"3004"},
    {"semester": "Semester-III", "course_name": "Ability Enhancing course (Course on Disaster Risk Management)", "course_type": "AEC-3", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"3005"},
    {"semester": "Semester-III", "course_name": "Skill Enhancement Course", "course_type": "SEC-3", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"3006"},

    # Semester-IV
    {"semester": "Semester-IV", "course_name": "Major Course 5", "course_type": "MJC-5", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"4001"},
    {"semester": "Semester-IV", "course_name": "Major Course 6", "course_type": "MJC-6", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"4002"},
    {"semester": "Semester-IV", "course_name": "Major Course 7", "course_type": "MJC-7", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"4003"},
    {"semester": "Semester-IV", "course_name": "Minor Course 4", "course_type": "MIC-4", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"4004"},
    {"semester": "Semester-IV", "course_name": "Ability enhancing course (Course on NCC/ NSS/ NGO's /Social Service/ Scout & Guide / Sports)", "course_type": "AEC-4", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"4005"},

    # Semester-V
    {"semester": "Semester-V", "course_name": "Major Course 8", "course_type": "MJC-8", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"5001"},
    {"semester": "Semester-V", "course_name": "Major Course 9", "course_type": "MJC-9", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"5002"},
    {"semester": "Semester-V", "course_name": "Minor Course 5", "course_type": "MIC-5", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"5003"},
    {"semester": "Semester-V", "course_name": "Minor Course 6", "course_type": "MIC-6", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"5004"},
    {"semester": "Semester-V", "course_name": "Internship", "course_type": "INT-1", "ltp": "-", "credit": 4, "marks": 100, "code":"5005"},

    # Semester-VI
    {"semester": "Semester-VI", "course_name": "Major Course 10", "course_type": "MJC-10", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"6001"},
    {"semester": "Semester-VI", "course_name": "Major Course 11", "course_type": "MJC-11", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"6002"},
    {"semester": "Semester-VI", "course_name": "Major Course 12", "course_type": "MJC-12", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"6003"},
    {"semester": "Semester-VI", "course_name": "Minor Course 7", "course_type": "MIC-7", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"6004"},
    {"semester": "Semester-VI", "course_name": "Minor Course 8", "course_type": "MIC-8", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"6005"},

    # Semester-VII
    {"semester": "Semester-VII", "course_name": "Major Course 13", "course_type": "MJC-13", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"7001"},
    {"semester": "Semester-VII", "course_name": "Major Course 14", "course_type": "MJC-14", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"7002"},
    {"semester": "Semester-VII", "course_name": "Major Course 15", "course_type": "MJC-15", "ltp": "6-1-0", "credit": 6, "marks": 100, "code":"7003"},
    {"semester": "Semester-VII", "course_name": "Minor Course 9", "course_type": "MIC-9", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"7004"},

    # Semester-VIII
    {"semester": "Semester-VIII", "course_name": "Major Course 16", "course_type": "MJC-16", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"8001"},
    {"semester": "Semester-VIII", "course_name": "Minor Course 10", "course_type": "MIC-10", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"8002"},
    {"semester": "Semester-VIII", "course_name": "Research Project/Dissertation", "course_type": "RP-1", "ltp": "-", "credit": 12, "marks": 100, "code":"8003"},
]

def safe_int(value, default=None):
    if value is None or value == '':
        return default
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default

def build_caches():
    print("📦 Building caches...")
    
    # Cache students by registration number (map to ID only)
    students_cache = {}
    for data in UGStudentProfile.objects.all().values('id', 'registration_no'):
        students_cache[data['registration_no']] = data['id']
    print(f"   Cached {len(students_cache):,} students")
    
    # Cache departments by discipline_code
    departments_cache = {}
    disciplines = DisciplineMaster.objects.all().values('discipline_code', 'discipline_name')
    dept_map = {d.name.lower().strip(): d.id for d in UGDepartment.objects.all()}
    for disc in disciplines:
        if disc['discipline_code'] and disc['discipline_name']:
            key = disc['discipline_name'].strip().lower()
            if key in dept_map:
                departments_cache[disc['discipline_code']] = dept_map[key]
    print(f"   Cached {len(departments_cache):,} departments")
    
    # Cache batches
    batches_cache = {b.name: b.id for b in UGBatch.objects.all()}
    print(f"   Cached {len(batches_cache):,} batches")
    
    # Cache existing assessment composite keys
    print("   Caching existing records for deduplication...")
    existing_keys = set()
    assessments = StudentCourseAssessment.objects.all().values_list(
        'student_id', 'paper_code', 'semester', 'label', 'exam_type', 'session'
    ).iterator(chunk_size=10000)
    for key in assessments:
        existing_keys.add(key)
    print(f"   Cached {len(existing_keys):,} existing records")
    
    common_lookup = {item['code']: item for item in common_course_structure_data}
    
    return students_cache, departments_cache, batches_cache, common_lookup, existing_keys

def migrate_data(limit=None, clear_existing=False):
    print(f"\n{'='*80}")
    print(f"🚀 SUPERFAST MIGRATION: UG Semester Results")
    print(f"{'='*80}\n")
    
    if clear_existing:
        print("🗑️  Clearing target table...")
        StudentCourseAssessment.objects.all().delete()
    
    students_cache, departments_cache, batches_cache, common_lookup, existing_keys = build_caches()
    
    queryset = UGSemResultCurrent.objects.filter(is_migrated=False)
    if limit:
        queryset = queryset[:limit]
    
    total = limit if limit else queryset.count()
    print(f"📊 Processing {total:,} records...\n")
    
    stats = {'processed': 0, 'created': 0, 'duplicates': 0, 'skipped': 0}
    batch_assessments = []
    staging_ids_to_mark = []
    profile_updates = {} # student_id -> {field: value}
    
    start_time = datetime.now()
    
    for staging in queryset.iterator(chunk_size=BATCH_SIZE):
        stats['processed'] += 1
        
        try:
            student_id = students_cache.get(staging.college_reg_no)
            if not student_id:
                stats['skipped'] += 1
                continue
            
            label = staging.status or 'UNKNOWN'
            pc = str(staging.paper_code or '').strip()
            last_4 = pc[-4:] if len(pc) >= 4 else None
            
            matched = common_lookup.get(last_4)
            if matched:
                c_code = matched['course_type']
                c_type = c_code.split('-')[0]
            else:
                c_type = 'GEN'
                c_code = staging.course_code or 'UNKNOWN'
            
            # Deduplication key
            key = (student_id, staging.paper_code, staging.semester_code, label, staging.exam_type, staging.session_code)
            
            if key in existing_keys:
                stats['duplicates'] += 1
                staging_ids_to_mark.append(staging.id)
                if len(staging_ids_to_mark) >= BATCH_SIZE:
                    UGSemResultCurrent.objects.filter(id__in=staging_ids_to_mark).update(is_migrated=True)
                    staging_ids_to_mark = []
                continue
            
            # Determine if absent
            marks = staging.mark_secured
            is_absent = True if (marks is None or marks == '' or str(marks).strip().lower() in ['abs', 'absent']) else False
            
            grace_mark = safe_int(staging.grace_given, 0)
            is_grace = True if grace_mark > 0 else False

            # Create object
            batch_assessments.append(StudentCourseAssessment(
                student_id=student_id,
                name=staging.subject_name,
                short_name=staging.subject_code,
                course_type=c_type,
                course_code=c_code,
                paper_code=staging.paper_code,
                semester=staging.semester_code,
                max_marks=safe_int(staging.maximum_mark),
                min_mark=safe_int(staging.pass_mark),
                marks_obtained=safe_int(staging.mark_secured),
                credit_obtained=safe_int(staging.subject_ce),
                grade=staging.let_grad_sub,
                numeric_grade=safe_int(staging.numrical_let_grad),
                exam_type=staging.exam_type,
                exam_result=staging.subject_result,
                final_result=staging.final_result,
                grace_mark=grace_mark,
                is_grace=is_grace,
                is_absent=is_absent,
                session=staging.session_code,
                batch_id=batches_cache.get(str(staging.batch_code).strip()) if staging.batch_code else None,
                department_id=departments_cache.get(staging.discipline_code),
                college_code=staging.institute_code,
                degree=staging.course_code,
                label=label,
                json_data={
                    k: (v.isoformat() if isinstance(v, datetime) else v)
                    for k, v in staging.__dict__.items() 
                    if not k.startswith('_') and k != 'uid' and k != 'id'
                }
            ))
            
            existing_keys.add(key)
            staging_ids_to_mark.append(staging.id)
            
            # Track profile updates
            if c_type in ['MJC', 'MIC', 'MDC']:
                field = {'MJC': 'major_course', 'MIC': 'minor_course', 'MDC': 'mdc_course'}[c_type]
                if student_id not in profile_updates: profile_updates[student_id] = {}
                profile_updates[student_id][field] = staging.subject_name

            if len(batch_assessments) >= BATCH_SIZE:
                with transaction.atomic():
                    StudentCourseAssessment.objects.bulk_create(batch_assessments, ignore_conflicts=True)
                    UGSemResultCurrent.objects.filter(id__in=staging_ids_to_mark).update(is_migrated=True)
                
                stats['created'] += len(batch_assessments)
                batch_assessments = []
                staging_ids_to_mark = []
                
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = stats['processed'] / elapsed if elapsed > 0 else 0
                print(f"   📥 Batch Committed | Processed {stats['processed']:,} | Created: {stats['created']:,} | Rate: {rate:.0f}/s")

        except Exception as e:
            print(f"❌ Error at ID {staging.id}: {e}")
            stats['skipped'] += 1

    # Remaining
    if batch_assessments:
        with transaction.atomic():
            StudentCourseAssessment.objects.bulk_create(batch_assessments, ignore_conflicts=True)
            UGSemResultCurrent.objects.filter(id__in=staging_ids_to_mark).update(is_migrated=True)
        stats['created'] += len(batch_assessments)

    # Bulk profile updates
    if profile_updates:
        print(f"\n🆙 Bulk updating {len(profile_updates):,} student profiles...")
        p_ids = list(profile_updates.keys())
        p_chunk = 5000 # Increased chunk size
        for i in range(0, len(p_ids), p_chunk):
            chunk = p_ids[i:i+p_chunk]
            profiles = list(UGStudentProfile.objects.filter(id__in=chunk))
            for p in profiles:
                for f, v in profile_updates[p.id].items(): 
                    setattr(p, f, v)
            UGStudentProfile.objects.bulk_update(profiles, ['major_course', 'minor_course', 'mdc_course'])
            print(f"   Updated profiles: {min(i+p_chunk, len(p_ids)):,} / {len(p_ids):,}")

    duration = (datetime.now() - start_time).total_seconds()
    print(f"\n🏁 Done in {duration:.1f}s | Avg Rate: {stats['processed']/duration:.0f}/s")
    print(f"✅ Total Created: {stats['created']:,} | Duplicates: {stats['duplicates']:,} | Skipped: {stats['skipped']:,}")

if __name__ == '__main__':
    migrate_data()
