# -*- coding: utf-8 -*-
"""
Migrate data from StagingLLBResultCurrent to LLB app models

This script will:
1. Create users if they don't exist
2. Create/map Course, Session, Batch, Exam, Subject, College
3. Create LLBStudentProfile with llb profile type
4. Create LLBResult and LLBResultDetail records

Run this:
poetry run python scripts/llb/migrate_staging_to_llb.py
"""

import os
import sys
import django
from django.db import transaction
from django.contrib.auth import get_user_model

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import StagingLLBResultCurrent
from llb.models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile,
    LLBCourseStructure, CommonCourseStructure, LLBExam, LLBStudentExamResult, LLBStudentCourseAssessment
)
from colleges.models import College

User = get_user_model()

# Cache dictionaries
courses_cache = {}
sessions_cache = {}
batches_cache = {}
subjects_cache = {}
common_subjects_cache = {}
exams_cache = {}
colleges_cache = {}
users_cache = {}
students_cache = {}

def get_assessment_label(status):
    """Convert staging status to assessment label"""
    if not status:
        return "Unknown"
    
    status = status.upper().strip()
    
    # Map staging status to assessment labels
    if status == "END_TERM":
        return "ESE"  
    elif status == "MID_TERM":
        return "CIA"  
    elif status == "LAB":
        return "CIA"
    else:
        return status

def get_or_create_course(course_code):
    """Get or create LLB course"""
    if course_code in courses_cache:
        return courses_cache[course_code]
    
    course, created = LLBCourse.objects.get_or_create(
        name=course_code or 'LLB',
        defaults={'duration_years': 3}
    )
    courses_cache[course_code] = course
    if created:
        print(f"  Created course: {course.name}")
    return course

def get_or_create_session(session_code):
    """Get or create LLB session"""
    if session_code in sessions_cache:
        return sessions_cache[session_code]
    
    # Parse session like "2019-22" to get years
    try:
        if session_code and '-' in session_code:
            parts = session_code.split('-')
            start_year = int('20' + parts[0]) if len(parts[0]) == 2 else int(parts[0])
            end_year = int('20' + parts[1]) if len(parts[1]) == 2 else int(parts[1])
        else:
            start_year = 2020
            end_year = 2023
    except:
        start_year = 2020
        end_year = 2023
    
    session, created = LLBSession.objects.get_or_create(
        name=session_code or '2020-23',
        defaults={
            'start_year': start_year,
            'end_year': end_year,
            'is_active': True
        }
    )
    sessions_cache[session_code] = session
    if created:
        print(f"  Created session: {session.name}")
    return session

def get_or_create_batch(batch_code):
    """Get or create LLB batch"""
    if batch_code in batches_cache:
        return batches_cache[batch_code]
    
    batch, created = LLBBatch.objects.get_or_create(
        name=batch_code or '2020 Admission',
        defaults={'is_active': True}
    )
    batches_cache[batch_code] = batch
    if created:
        print(f"  Created batch: {batch.name}")
    return batch

def clean_subject_name(name):
    """Clean and normalize subject name (same as migrate_course_structures.py)"""
    if not name:
        return 'Unknown Subject'
    
    # Remove newlines, extra spaces, and normalize
    name = name.replace('\n', ' ').replace('\r', ' ')
    name = ' '.join(name.split())
    name = name.strip()
    
    # Remove -T1, -P1, -PS1 suffixes (staging data inconsistencies)
    import re
    name = re.sub(r'-T\d+$', '', name)
    name = re.sub(r'-P\d+$', '', name)
    name = re.sub(r'-PS\d+$', '', name)
    name = name.strip()
    
    return name or 'Unknown Subject'

def get_course_code(paper_code):
    """Generate course_code based on paper_code (same as migrate_course_structures.py)"""
    if not paper_code or paper_code == 'UNKNOWN':
        return 'UNKNOWN'
    
    try:
        if len(paper_code) >= 6 and paper_code.startswith('LLB'):
            code_part = paper_code[-3:]
            paper_num = int(code_part[1:])
            
            roman_numerals = {
                1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
                6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X',
                11: 'XI', 12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV'
            }
            
            return roman_numerals.get(paper_num, str(paper_num))
        else:
            return 'UNKNOWN'
    except:
        return 'UNKNOWN'

def get_or_create_subject(subject_name, maximum_mark, pass_mark, semester, paper_code=None, status=None):
    """
    Get existing LLB course structure (does NOT create new ones).
    Course structures should be created first using migrate_course_structures.py
    
    Uses paper_code as the primary identifier to avoid spelling variation issues.
    Returns the matching LLBCourseStructure or None if not found.
    """
    semester = semester or ''
    paper_code = paper_code or 'UNKNOWN'
    
    # Determine assessment type from status
    assessment_label = get_assessment_label(status)
    
    # Cache key uses paper_code to match migrate_course_structures.py
    cache_key = f"{paper_code}_{semester}_{assessment_label}"
    if cache_key in subjects_cache:
        return subjects_cache[cache_key]
    
    # Try to get existing LLBCourseStructure using paper_code (do NOT create)
    try:
        subject = LLBCourseStructure.objects.get(
            paper_code=paper_code,  # Use paper_code field
            semester=semester,
            status=assessment_label
        )
        subjects_cache[cache_key] = subject
        return subject
    except LLBCourseStructure.DoesNotExist:
        print(f"  ⚠️  Warning: Course structure not found: {paper_code} ({semester}) [{assessment_label}]")
        return None
    except LLBCourseStructure.MultipleObjectsReturned:
        # If multiple found, get the first one
        subject = LLBCourseStructure.objects.filter(
            paper_code=paper_code,
            semester=semester,
            status=assessment_label
        ).first()
        subjects_cache[cache_key] = subject
        return subject

def get_or_create_exam(session_code, exam_type, batch=None, semester=None):
    """Get or create LLB exam"""
    cache_key = f"{session_code}_{exam_type}"
    if cache_key in exams_cache:
        return exams_cache[cache_key]
    
    exam_name = f"LLB {exam_type} Examination {session_code}"
    
    from datetime import date
    exam, created = LLBExam.objects.get_or_create(
        name=exam_name,
        defaults={
            'session': session_code or '2020-21',
            'batch': batch,
            'semester': semester,
            'exam_month_year': 'June 2024',
            'publication_date': date.today()
        }
    )
    exams_cache[cache_key] = exam
    if created:
        print(f"  Created exam: {exam.name}")
    return exam

def get_or_create_college(institute_code):
    """Get or create college"""
    if institute_code in colleges_cache:
        return colleges_cache[institute_code]
    
    try:
        college = College.objects.get(college_code=institute_code)
        colleges_cache[institute_code] = college
        return college
    except College.DoesNotExist:
        # Create a placeholder college
        college, created = College.objects.get_or_create(
            college_code=institute_code or 'UNKNOWN',
            defaults={
                'name': f'College {institute_code}',
                'short_name': f'COL{institute_code}'
            }
        )
        colleges_cache[institute_code] = college
        if created:
            print(f"  Created college: {college.name}")
        return college

def get_or_create_user(student_name, fathers_name, mothers_name, college_roll_no, college_reg_no):
    """Get or create user account"""
    # Use college_reg_no first, then college_roll_no as username
    # Skip if both are None or 'None'
    if (not college_reg_no or college_reg_no == 'None') and (not college_roll_no or college_roll_no == 'None'):
        return None
    
    username = college_reg_no if college_reg_no and college_reg_no != 'None' else college_roll_no
    cache_key = username
    
    if cache_key in users_cache:
        return users_cache[cache_key]
    
    # Try to find existing user by username
    try:
        user = User.objects.get(username=username)
        users_cache[cache_key] = user
        return user
    except User.DoesNotExist:
        pass
    
    # Parse name
    name_parts = student_name.strip().split() if student_name else ['Student', 'Name']
    first_name = name_parts[0] if len(name_parts) > 0 else 'Student'
    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Name'
    
    # Password is same as username or 'PASSWORD' if no username available
    password = username if username and username != 'llb_unknown' else 'PASSWORD'
    
    # Create new user
    user = User.objects.create_user(
        username=username,
        first_name=first_name[:30],
        last_name=last_name[:150],
        email=f'{username}@llb.edu' if username != 'llb_unknown' else 'noemail@llb.edu',
        password=password,
        profile_type='llb'
    )
    users_cache[cache_key] = user
    print(f"  Created user: {user.username} ({user.get_full_name()}) - password: {password}")
    return user

def get_or_create_student_profile(staging_record, user, college, course, batch):
    """Get or create LLB student profile"""
    # Use registration_no first, fallback to roll_no
    registration_no = staging_record.college_reg_no
    roll_no = staging_record.college_roll_no
    
    # Skip if both are missing
    if (not registration_no or registration_no == 'None') and (not roll_no or roll_no == 'None'):
        print(f"  ⚠️  Skipping student profile: Missing both registration_no and roll_no for record {staging_record.source_id}")
        return None
    
    # Use registration_no as primary identifier, fallback to roll_no
    primary_id = registration_no if registration_no and registration_no != 'None' else roll_no
    cache_key = primary_id
    
    if cache_key in students_cache:
        return students_cache[cache_key]
    
    # Try to find existing student by registration_no first, then roll_no
    try:
        if registration_no and registration_no != 'None':
            student = LLBStudentProfile.objects.get(registration_no=registration_no)
        else:
            student = LLBStudentProfile.objects.get(roll_no=roll_no)
        students_cache[cache_key] = student
        return student
    except LLBStudentProfile.DoesNotExist:
        pass
    
    # Skip if college, course, or batch is None
    if not college or not course or not batch:
        print(f"  ⚠️  Skipping student profile: Missing college/course/batch for {primary_id}")
        return None
    
    # Create student with available identifiers
    student = LLBStudentProfile.objects.create(
        user=user,
        roll_no=roll_no or f'ROLL{staging_record.source_id}',
        registration_no=registration_no if registration_no and registration_no != 'None' else f'REG{staging_record.source_id}',
        father_name=staging_record.fathers_name,
        mother_name=staging_record.mothers_name,
        college=college,
        course=course,
        batch=batch,
        is_active=True
    )
    students_cache[cache_key] = student
    print(f"  Created student: {student.roll_no} - {student.registration_no}")
    return student

def migrate_data():
    """Main migration function"""
    
    print("Starting LLB data migration from staging...")
    
    # Get all staging records
    staging_records = StagingLLBResultCurrent.objects.filter(is_migrated=False).order_by('college_reg_no', 'session_code', 'paper_code')
    total_count = staging_records.count()
    
    print(f"Total staging records to migrate: {total_count}")
    
    if total_count == 0:
        print("No records to migrate!")
        return
    
    migrated_count = 0
    error_count = 0
    skipped_count = 0
    
    # Group by student (college_reg_no + session_code)
    current_student_key = None
    current_result = None
    
    for idx, record in enumerate(staging_records, 1):
        try:
            # Create/get master data (outside transaction to avoid FK issues)
            course = get_or_create_course(record.course_code)
            session = get_or_create_session(record.session_code)
            batch = get_or_create_batch(record.batch_code)
            college = get_or_create_college(record.institute_code)
            exam = get_or_create_exam(record.session_code, record.exam_type, batch, record.semester_code)
            subject = get_or_create_subject(
                record.subject_name,
                record.maximum_mark,
                record.pass_mark,
                record.semester_code,
                record.paper_code,
                record.status  # Pass status to differentiate CIA/ESE
            )
            
            # Skip if course structure not found
            if subject is None:
                skipped_count += 1
                continue
            
            # Create/get user and student profile (outside transaction to avoid FK issues)
            student_key = f"{record.college_reg_no}_{record.session_code}"
            
            if student_key != current_student_key:
                # Create/get user first
                user = get_or_create_user(
                    record.student_name,
                    record.fathers_name,
                    record.mothers_name,
                    record.college_roll_no,
                    record.college_reg_no
                )
                
                # Skip if user creation failed (missing both reg_no and roll_no)
                if user is None:
                    skipped_count += 1
                    continue
                
                student = get_or_create_student_profile(
                    record, user, college, course, batch
                )
                
                # Skip if student profile creation failed
                if student is None:
                    skipped_count += 1
                    continue
                
                # Create result record for this student+exam
                try:
                    total_marks = int(record.grand_total_mark) if record.grand_total_mark else 0
                except:
                    total_marks = 0
                
                current_result = LLBStudentExamResult.objects.create(
                    student=student,
                    exam=exam,
                    total_marks=total_marks,
                    result_status=record.final_result or 'PENDING',
                    grace=int(record.grace_chk) if record.grace_chk and record.grace_chk.isdigit() else None
                )
                
                current_student_key = student_key

            with transaction.atomic():
                # Create result detail for this subject
                try:
                    marks_obtained = int(record.mark_secured) if record.mark_secured else 0
                except:
                    marks_obtained = 0
                
                # Skip simple assessment - using only MCA pattern assessment
                
                # Create detailed course assessment with labels
                assessment_label = get_assessment_label(record.status)
                
                LLBStudentCourseAssessment.objects.create(
                    exam_result=current_result,
                    student=student,
                    course=course,
                    course_structure=subject,
                    exam=exam,
                    semester=record.semester_code,
                    label=assessment_label,
                    session=record.session_code,
                    batch=batch,
                    college_code=record.institute_code,
                    exam_type=record.exam_type,
                    paper_code=record.paper_code,
                    
                    # Individual assessment fields
                    ind_max_marks=int(record.maximum_mark) if record.maximum_mark else None,
                    ind_pass_marks=int(record.pass_mark) if record.pass_mark else None,
                    ind_marks_obtained=marks_obtained,
                    ind_final_marks_obtained=marks_obtained,
                    
                    # Combined fields (same as individual for single assessment)
                    comb_max_marks=int(record.maximum_mark) if record.maximum_mark else None,
                    comb_pass_marks=int(record.pass_mark) if record.pass_mark else None,
                    comb_marks_obtained=marks_obtained,
                    comb_final_marks_obtained=marks_obtained,
                    
                    # Course summary fields
                    course_max_marks=int(record.maximum_mark) if record.maximum_mark else None,
                    course_marks_obtained=marks_obtained,
                    course_final_marks_obtained=marks_obtained,
                    
                    # Result status
                    subject_result=record.subject_result,
                    grade=record.grade,
                )
                
                # Mark as migrated
                record.is_migrated = True
                record.migration_notes = f"Migrated successfully on {django.utils.timezone.now()}"
                record.save()
                
                migrated_count += 1
                
                if idx % 100 == 0:
                    print(f"Progress: {idx}/{total_count} ({(idx/total_count)*100:.1f}%)")
                
        except Exception as e:
            error_count += 1
            print(f"Error migrating record {record.source_id}: {e}")
            record.migration_notes = f"Error: {str(e)}"
            record.save()
            continue
    
    print(f"\nMigration completed!")
    print(f"Successfully migrated: {migrated_count}")
    print(f"Skipped (course structure not found): {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"\nSummary:")
    print(f"  Courses: {len(courses_cache)}")
    print(f"  Sessions: {len(sessions_cache)}")
    print(f"  Batches: {len(batches_cache)}")
    print(f"  Course Structures (retrieved): {len(subjects_cache)}")
    print(f"  Exams: {len(exams_cache)}")
    print(f"  Colleges: {len(colleges_cache)}")
    print(f"  Students: {len(students_cache)}")
    print(f"  Users: {len(users_cache)}")

if __name__ == '__main__':
    migrate_data()
