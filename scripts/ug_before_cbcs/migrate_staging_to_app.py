"""
UG Before CBCS Data Migration Script
=====================================

This script migrates data from staging.UGResultCurrent to the ug_before_cbcs app.

HOW TO RUN:
-----------
1. First, clear existing data (if needed):
   PYTHONPATH=. poetry run python manage.py shell -c "from ug_before_cbcs.models import *; UGBeforeCBCSExamResult.objects.all().delete(); UGBeforeCBCSStudentAssessment.objects.all().delete(); UGBeforeCBCSExamRegistration.objects.all().delete(); UGBeforeCBCSStudentProfile.objects.all().delete(); UGBeforeCBCSExam.objects.all().delete(); UGBeforeCBCSBatch.objects.all().delete(); UGBeforeCBCSSession.objects.all().delete(); UGBeforeCBCSDiscipline.objects.all().delete(); UGBeforeCBCSCourse.objects.all().delete(); UGBeforeCBCSSubject.objects.all().delete(); UGBeforeCBCSCourseStructure.objects.all().delete(); print('All UG Before CBCS data cleared!')"

2. Run the migration:
   PYTHONPATH=. poetry run python scripts/ug_before_cbcs/migrate_staging_to_app.py

3. Verify migration:
   PYTHONPATH=. poetry run python scripts/ug_before_cbcs/verify_migration.py

NOTES:
------
- This script processes ~152,000 students from staging
- Expected runtime: Several hours (depends on system performance)
- All related data (courses, disciplines, exams, assessments) will be created automatically
"""

import os
import sys
import django
from decimal import Decimal

# Add the project root to sys.path (go up two levels from scripts/ug_before_cbcs/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import UGResultCurrent
from accounts.models import UserAccount
from colleges.models import College
from ug_before_cbcs.models import (
    UGBeforeCBCSStudentProfile, UGBeforeCBCSCourse, UGBeforeCBCSDiscipline,
    UGBeforeCBCSSession, UGBeforeCBCSBatch, UGBeforeCBCSExam,
    UGBeforeCBCSExamRegistration, UGBeforeCBCSStudentAssessment,
    UGBeforeCBCSExamResult, UGBeforeCBCSSubject
)

def get_or_create_course(course_code):
    if not course_code:
        return None
    name_map = {
        'BA': 'Bachelor of Arts (Hons.)',
        'BSC': 'Bachelor of Science (Hons.)',
        'BCOM': 'Bachelor of Commerce (Hons.)',
        'BA_GEN': 'Bachelor of Arts (General)',
        'BSC_GEN': 'Bachelor of Science (General)',
        'BCOM_GEN': 'Bachelor of Commerce (General)',
    }
    course, _ = UGBeforeCBCSCourse.objects.get_or_create(
        course_code=course_code,
        defaults={'name': name_map.get(course_code, course_code)}
    )
    return course

def get_or_create_discipline(name, code, course):
    if not code or not course:
        return None
    discipline, _ = UGBeforeCBCSDiscipline.objects.get_or_create(
        code=code,
        course=course,
        defaults={'name': name or code}
    )
    return discipline

def migrate_data():
    print("Starting migration from staging to UG Old (Non-CBCS)...")
    
    # Process by student to optimize
    unique_students = UGResultCurrent.objects.values('college_reg_no', 'student_name', 'college_roll_no', 'fathers_name', 'mothers_name', 'institute_code').distinct()
    
    for stud_data in unique_students:
        reg_no = stud_data['college_reg_no']
        if not reg_no: continue
        
        # 1. Create/Get User
        # First get college to set on user
        college = None
        if stud_data['institute_code']:
            college = College.objects.filter(college_code=stud_data['institute_code']).first()
        
        user, created = UserAccount.objects.get_or_create(
            username=reg_no,
            defaults={
                'first_name': stud_data['student_name'] or 'Student',
                'user_type': 'student',
                'current_profile': 'ug_before_cbcs',
                'college': college
            }
        )
        if created:
            user.set_password(reg_no)
            user.save()
        elif college and not user.college:
            # Update college if user exists but doesn't have college set
            user.college = college
            user.save()
            
        # 3. Create Student Profile
        profile, _ = UGBeforeCBCSStudentProfile.objects.get_or_create(
            registration_no=reg_no,
            defaults={
                'user': user,
                'student_name': stud_data['student_name'],
                'roll_no': stud_data['college_roll_no'],
                'fathers_name': stud_data['fathers_name'],
                'mothers_name': stud_data['mothers_name'],
                'college': college
            }
        )

        
        # 4. Process all records for this student
        student_records = UGResultCurrent.objects.filter(college_reg_no=reg_no)
        
        for record in student_records:
            # Course & Discipline
            course = get_or_create_course(record.course_code)
            discipline = get_or_create_discipline(record.subject_name if 'HON' in (record.hon or '') else None, record.discipline_code, course)
            
            if not profile.course:
                profile.course = course
                profile.discipline = discipline
                profile.save()
                
            # Session
            session = None
            if record.session_code:
                session, _ = UGBeforeCBCSSession.objects.get_or_create(name=record.session_code)
                if not profile.session:
                    profile.session = session
                    profile.save()
                    
            # Exam
            part_map = {'1ST': 'PART1', '2ND': 'PART2', '3RD': 'PART3'}
            part = part_map.get(record.semester_code, 'PART1')
            
            exam, _ = UGBeforeCBCSExam.objects.get_or_create(
                name=f"{course.name if course else ''} {record.semester_code or ''} Exam {record.batch_code or ''}",
                part=part,
                exam_year=int(record.batch_code) if record.batch_code and record.batch_code.isdigit() else 2000,
                defaults={'exam_month_year': record.session_code}
            )
            
            # Exam Registration
            exam_reg, _ = UGBeforeCBCSExamRegistration.objects.get_or_create(
                student=profile,
                exam=exam,
                defaults={
                    'exam_type': 'REGULAR' if record.exam_type == 'REGULAR' else 'BACK',
                    'is_ex_regular': record.ExRegular_chk == 'YES'
                }
            )
            
            # Subject
            subject, _ = UGBeforeCBCSSubject.objects.get_or_create(
                code=record.paper_code or record.subject_code,
                defaults={
                    'name': record.subject_name or record.paper_code,
                    'paper_number': record.paper_code
                }
            )
            
            # Assessment
            UGBeforeCBCSStudentAssessment.objects.update_or_create(
                registration=exam_reg,
                subject=subject,
                defaults={
                    'theory_marks': record.theory,
                    'practical_marks': record.pra,
                    'sessional_marks': record.sessional,
                    'marks_secured': Decimal(record.mark_secured) if record.mark_secured and record.mark_secured.replace('.','',1).isdigit() else None,
                    'max_marks': int(record.maximum_mark) if record.maximum_mark and record.maximum_mark.isdigit() else None,
                    'pass_marks': int(record.pass_mark) if record.pass_mark and record.pass_mark.isdigit() else None,
                    'subject_total_mark': Decimal(record.subject_total_mark) if record.subject_total_mark and record.subject_total_mark.replace('.','',1).isdigit() else None,
                    'subject_result': record.subject_result
                }
            )
            
            # Result Summary
            UGBeforeCBCSExamResult.objects.update_or_create(
                registration=exam_reg,
                defaults={
                    'grand_total_secured': Decimal(record.total_secured_mark) if record.total_secured_mark and record.total_secured_mark.replace('.','',1).isdigit() else None,
                    'grand_total_max': int(record.grand_total_mark) if record.grand_total_mark and record.grand_total_mark.isdigit() else None,
                    'result_status': 'PASS' if 'PASS' in (record.final_result or '').upper() else 'FAIL',
                    'final_result_text': record.final_result
                }
            )

    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate_data()
