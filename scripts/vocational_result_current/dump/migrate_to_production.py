import os
import sys
import django
from decimal import Decimal

# Set up Django environment
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from django.db.models import Sum
from staging.models import VocationalResultCurrent
from colleges.models import College
from accounts.models import UserAccount

# App-specific imports
import bba_year.models as bba_models
import bca_hons_year.models as bca_models

# Configuration
COURSE_CODES = ['BBA', 'BCA_HONS', 'BCA_SC', 'BCA_ART', 'BCA_COMM']

# Mappings
YEAR_MAPPING = {
    '1ST': '1',
    '2ND': '2',
    '3RD': '3',
}

LABEL_MAPPING = {
    'END2_TERM': 'ESE 2',
    'END_TERM': 'ESE',
    'LAB': 'CIA',
    'MID_TERM': 'CIA',
}

def migrate_to_production():
    print("Starting prioritized migration from staging to production models...")
    
    # Filter staging data
    staging_records = VocationalResultCurrent.objects.filter(course_code__in=COURSE_CODES).order_by('id')
    total_count = staging_records.count()
    print(f"Total records to process: {total_count}")

    college_cache = {c.college_code: c for c in College.objects.all() if c.college_code}
    
    processed = 0
    errors = 0
    error_list = []

    for record in staging_records:
        try:
            course_code = record.course_code
            if course_code == 'BBA':
                app = bba_models
                profile_type = 'bba_year'
            elif course_code in ['BCA_HONS', 'BCA_SC', 'BCA_ART', 'BCA_COMM', 'BCA']:
                app = bca_models
                profile_type = 'bca_hons_year'
            else:
                continue

            # 1. Master Data (Sessions, Courses, Batches)
            session_name = record.session_code or "Unknown"
            batch_name = record.batch_code or "Default Batch"
            college_obj = college_cache.get(record.institute_code)
            
            with transaction.atomic():
                # Get the appropriate Session/Course/Batch models
                if hasattr(app, 'BBASession'):
                    session_obj, _ = app.BBASession.objects.get_or_create(name=session_name)
                    course_obj, _ = app.BBACourse.objects.get_or_create(
                        course_code=course_code, 
                        defaults={'name': 'Bachelor of Business Administration'}
                    )
                    batch_obj, _ = app.BBABatch.objects.get_or_create(name=batch_name)
                else:
                    session_obj, _ = app.BCAHonsSession.objects.get_or_create(name=session_name)
                    course_obj, _ = app.BCAHonsCourse.objects.get_or_create(
                        course_code=course_code, 
                        defaults={'name': 'Bachelor of Computer Applications'}
                    )
                    batch_obj, _ = app.BCAHonsBatch.objects.get_or_create(name=batch_name)

                # 2. Priority Identifier Handling
                reg_no = record.college_reg_no
                roll_no = record.college_roll_no
                
                # Priority: Registration Number > Roll Number
                identifier = reg_no if reg_no and reg_no.strip() else roll_no
                
                if not identifier or not identifier.strip():
                    raise ValueError(f"Record {record.id} missing both registration and roll number")
                
                identifier = identifier.strip()

                # 3. User Account Handling
                user_obj, created = UserAccount.objects.get_or_create(
                    username=identifier,
                    defaults={
                        'first_name': record.student_name.split(' ')[0] if record.student_name else "Student",
                        'last_name': ' '.join(record.student_name.split(' ')[1:]) if record.student_name and ' ' in record.student_name else "",
                        'user_type': 'student',
                        'current_profile': profile_type,
                        'is_active': True,
                    }
                )
                if created:
                    user_obj.set_password(identifier)
                    user_obj.save()

                # 4. Student Profile Handling
                year_val = YEAR_MAPPING.get(record.semester_code, record.semester_code)
                
                profile_defaults = {
                    'user': user_obj,
                    'roll_no': roll_no,
                    'first_name': record.student_name,
                    'father_name': record.fathers_name,
                    'mother_name': record.mothers_name,
                    'current_year': int(year_val) if str(year_val).isdigit() else 1,
                    'session_str': session_name,
                    'college': college_obj,
                    'course': course_obj,
                    'batch': batch_obj,
                }

                if hasattr(app, 'BBAStudentProfile'):
                    student_obj, _ = app.BBAStudentProfile.objects.update_or_create(
                        registration_no=identifier,
                        defaults=profile_defaults
                    )
                else:
                    student_obj, _ = app.BCAHonsStudentProfile.objects.update_or_create(
                        registration_no=identifier,
                        defaults=profile_defaults
                    )

                # 5. Course Structure Logic
                paper_code = record.paper_code or "P-UNKNOWN"
                subject_name = record.subject_name or "Unknown Subject"
                raw_status = record.status # e.g. MID_TERM, END_TERM
                label = LABEL_MAPPING.get(raw_status, 'ESE') # Fallback to ESE
                
                # Paper Type Logic: _SUB suffix means SUBSIDIARY
                subj_code = record.subject_code or ""
                paper_type_val = 'SUBSIDIARY' if subj_code.endswith('_SUB') else 'HONOURS'
                
                max_marks_val = float(record.maximum_mark) if record.maximum_mark and str(record.maximum_mark).replace('.','').isdigit() else 100.0
                
                CourseStructureModel = app.BBACourseStructure if hasattr(app, 'BBACourseStructure') else app.BCAHonsCourseStructure
                CommonCourseStructureModel = app.BBACommonCourseStructure if hasattr(app, 'BBACommonCourseStructure') else app.BCAHonsCommonCourseStructure
                ExamModel = app.BBAExam if hasattr(app, 'BBAExam') else app.BCAHonsExam
                AssessmentModel = app.BBAStudentCourseAssessment if hasattr(app, 'BBAStudentCourseAssessment') else app.BCAHonsStudentCourseAssessment

                # Check if CourseStructure entry exists, if not create it
                struct_obj, struct_created = CourseStructureModel.objects.update_or_create(
                    course=course_obj,
                    course_code=paper_code,
                    year=year_val,
                    label=label,
                    defaults={
                        'course_name': subject_name,
                        'max_marks': max_marks_val,
                        'course_type': 'Theory'
                    }
                )

                # Update CommonCourseStructure total marks
                total_marks = CourseStructureModel.objects.filter(
                    course=course_obj,
                    course_code=paper_code,
                    year=year_val
                ).aggregate(total=Sum('max_marks'))['total'] or max_marks_val

                CommonCourseStructureModel.objects.update_or_create(
                    code=paper_code,
                    year=year_val,
                    course=course_obj,
                    defaults={
                        'course_name': subject_name,
                        'course_type': 'Theory',
                        'marks': int(total_marks),
                        'paper_type': paper_type_val
                    }
                )

                # 6. Exam Event Handling
                exam_name = f"{course_code} {year_val} Year Exam - {session_name}"
                exam_obj, _ = ExamModel.objects.get_or_create(
                    name=exam_name,
                    defaults={'session': session_name, 'year': int(year_val) if str(year_val).isdigit() else 1}
                )

                # 7. Result Mapping (StudentCourseAssessment)
                marks_obtained = Decimal(record.mark_secured) if record.mark_secured and str(record.mark_secured).replace('.','').isdigit() else Decimal('0.00')
                pass_marks = Decimal(record.pass_mark) if record.pass_mark and str(record.pass_mark).replace('.','').isdigit() else Decimal('33.00')
                
                # Absent indicators from various fields
                is_absent = (record.record_status == 'ABS' or 
                             record.grade == 'Ab' or 
                             record.mark_secured == 'ABS' or
                             record.status == 'ABSENT')

                assessment_defaults = {
                    'course_name': subject_name,
                    'batch': batch_obj,
                    'ind_max_marks': int(max_marks_val),
                    'ind_pass_marks': pass_marks,
                    'ind_marks_obtained': marks_obtained,
                    'ind_is_absent': is_absent,
                }
                
                if hasattr(app, 'BBAExam'):
                    assessment_defaults['bba_exam'] = exam_obj
                else:
                    assessment_defaults['bca_hons_exam'] = exam_obj

                AssessmentModel.objects.update_or_create(
                    student=student_obj,
                    paper_code=paper_code,
                    year=year_val,
                    label=label,
                    session=session_obj,
                    exam_type=record.exam_type or 'REGULAR',
                    defaults=assessment_defaults
                )

            processed += 1
            if processed % 100 == 0:
                print(f"Processed {processed}/{total_count} records...")

        except Exception as e:
            errors += 1
            err_msg = f"Record ID: {record.id} | Course: {record.course_code} | Error: {str(e)}"
            print(err_msg)
            error_list.append(err_msg)

    print("\n" + "="*50)
    print("MIGRATION SUMMARY")
    print("="*50)
    print(f"Total Successfully Processed: {processed}")
    print(f"Errors Encountered: {errors}")
    
    if error_list:
        print("\n" + "="*50)
        print("ERROR DETAILS")
        print("="*50)
        for err in error_list:
            print(f"- {err}")

if __name__ == "__main__":
    migrate_to_production()
