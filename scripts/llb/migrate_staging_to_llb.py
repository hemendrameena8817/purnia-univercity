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
    LLBCourseStructure, LLBExam, LLBStudentExamResult, LLBStudentAssessment, LLBStudentCourseAssessment
)
from colleges.models import College

User = get_user_model()

# Cache dictionaries
courses_cache = {}
sessions_cache = {}
batches_cache = {}
subjects_cache = {}
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

def get_or_create_subject(subject_name, maximum_mark, pass_mark):
    """Get or create LLB course structure (common subject)"""
    if subject_name in subjects_cache:
        return subjects_cache[subject_name]
    
    try:
        full_marks = int(maximum_mark) if maximum_mark else 100
        pass_marks = int(pass_mark) if pass_mark else 33
    except:
        full_marks = 100
        pass_marks = 33
    
    subject, created = LLBCourseStructure.objects.get_or_create(
        name=subject_name or 'Unknown Subject',
        defaults={
            'full_marks': full_marks,
            'pass_marks': pass_marks
        }
    )
    subjects_cache[subject_name] = subject
    if created:
        print(f"  Created subject: {subject.name}")
    return subject

def get_or_create_exam(session_code, exam_type, batch=None):
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
            'semester': None,
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

def get_or_create_user(student_name, fathers_name, mothers_name, college_roll_no):
    """Get or create user account"""
    cache_key = college_roll_no
    if cache_key in users_cache:
        return users_cache[cache_key]
    
    # Try to find existing user by username (roll_no)
    try:
        user = User.objects.get(username=college_roll_no)
        users_cache[cache_key] = user
        return user
    except User.DoesNotExist:
        pass
    
    # Parse name
    name_parts = student_name.strip().split() if student_name else ['Student', 'Name']
    first_name = name_parts[0] if len(name_parts) > 0 else 'Student'
    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Name'
    
    # Create new user
    user = User.objects.create_user(
        username=college_roll_no or f'llb_{college_roll_no}',
        first_name=first_name[:30],
        last_name=last_name[:150],
        email=f'{college_roll_no}@llb.edu' if college_roll_no else 'noemail@llb.edu',
        profile_type='llb'
    )
    users_cache[cache_key] = user
    print(f"  Created user: {user.username} ({user.get_full_name()})")
    return user

def get_or_create_student_profile(staging_record, user, college, course, batch):
    """Get or create LLB student profile"""
    cache_key = staging_record.college_reg_no
    if cache_key in students_cache:
        return students_cache[cache_key]
    
    try:
        student = LLBStudentProfile.objects.get(registration_no=staging_record.college_reg_no)
        students_cache[cache_key] = student
        return student
    except LLBStudentProfile.DoesNotExist:
        pass
    
    student = LLBStudentProfile.objects.create(
        user=user,
        roll_no=staging_record.college_roll_no or f'ROLL{staging_record.source_id}',
        registration_no=staging_record.college_reg_no or f'REG{staging_record.source_id}',
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
            exam = get_or_create_exam(record.session_code, record.exam_type, batch)
            subject = get_or_create_subject(
                record.subject_name,
                record.maximum_mark,
                record.pass_mark
            )
            
            # Create/get user and student profile (outside transaction to avoid FK issues)
            student_key = f"{record.college_reg_no}_{record.session_code}"
            
            if student_key != current_student_key:
                # Create/get user first
                user = get_or_create_user(
                    record.student_name,
                    record.fathers_name,
                    record.mothers_name,
                    record.college_roll_no
                )
                
                student = get_or_create_student_profile(
                    record, user, college, course, batch
                )
                
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
                
                # Create simple assessment for backward compatibility
                LLBStudentAssessment.objects.create(
                    exam_result=current_result,
                    subject=subject,
                    paper_code=record.paper_code,
                    marks_obtained=marks_obtained,
                    total_secured_mark=int(record.total_secured_mark) if record.total_secured_mark else None,
                    total_percentage=float(record.total_per) if record.total_per else None,
                    grade=record.grade,
                    subject_result=record.subject_result,
                    status=record.status
                )
                
                # Create detailed course assessment with labels
                assessment_label = get_assessment_label(record.status)
                
                LLBStudentCourseAssessment.objects.create(
                    exam_result=current_result,
                    student=student,
                    course_name=subject.name,
                    course_code=subject.name[:100],  # Truncate to fit in field
                    paper_code=record.paper_code,
                    semester=str(exam.semester) if exam.semester else None,
                    label=assessment_label,
                    session=record.session_code,
                    batch=batch,
                    college_code=record.institute_code,
                    exam_type=record.exam_type,
                    
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
    print(f"Errors: {error_count}")
    print(f"\nSummary:")
    print(f"  Courses: {len(courses_cache)}")
    print(f"  Sessions: {len(sessions_cache)}")
    print(f"  Batches: {len(batches_cache)}")
    print(f"  Subjects: {len(subjects_cache)}")
    print(f"  Exams: {len(exams_cache)}")
    print(f"  Colleges: {len(colleges_cache)}")
    print(f"  Students: {len(students_cache)}")
    print(f"  Users: {len(users_cache)}")

if __name__ == '__main__':
    migrate_data()
