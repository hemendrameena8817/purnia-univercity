import os
import sys
import django
import uuid
from typing import Dict, List
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from django.db import transaction
from ug.models import UGExamResult, StudentCourseAssessment, ExamRegistration

def copy_assessment(a: StudentCourseAssessment, session: str) -> StudentCourseAssessment:
    return StudentCourseAssessment(
        uid=uuid.uuid4(),
        student=a.student,
        course_name=a.course_name,
        course_short_name=a.course_short_name,
        course_type=a.course_type,
        course_code=a.course_code,
        paper_code=a.paper_code,
        semester=a.semester,
        label=a.label,
        department=a.department,
        degree=a.degree,
        batch=a.batch,
        college_code=a.college_code,
        
        exam_type='BACK',
        session=session,
        
        # Max/Pass marks to retain
        ind_max_marks=a.ind_max_marks,
        ind_pass_marks=a.ind_pass_marks,
        comb_max_marks=a.comb_max_marks,
        comb_max_credits=a.comb_max_credits,
        comb_pass_marks=a.comb_pass_marks,
        course_max_marks=a.course_max_marks,
        course_max_credits=a.course_max_credits,
        course_pass_marks=a.course_pass_marks,
        sem_max_credit=a.sem_max_credit,
        
        # Values to reset
        attendance=None,
        ind_is_absent=False,
        ind_marks_obtained=None,
        ind_grace_obtained=0,
        ind_final_marks_obtained=None,
        ind_is_pass=None,
        comb_marks_obtained=None,
        comb_grace_obtained=0,
        comb_final_marks_obtained=None,
        comb_credit_obtained=None,
        comb_numeric_grade=None,
        comb_letter_grade=None,
        comb_grade_point=None,
        course_marks_obtained=None,
        course_grace_obtained=0,
        course_final_marks_obtained=None,
        course_credit_obtained=None,
        course_grade_point=None,
        sem_credit_obtained=None,
        sgpa=None,
        sem_result=None,
        next_sem_status=None,
        sem_grace_obtained=0,
        temp_total_gp=None,
        
        is_cia_filled=False,
        cia_filled_on=None,
    )

def main():
    target_sem = '1ST'
    target_session = '2025-26'
    
    # Optional single registration number from CLI
    target_reg_no = sys.argv[1] if len(sys.argv) > 1 else None
    
    if target_reg_no:
        print(f"Preparing back exam entries for SPECIFIC student: {target_reg_no}")
    else:
        print(f"Preparing back exam entries for ALL eligible students in semester '{target_sem}', session '{target_session}'...")

    # Fetch students who failed, were promoted, partly qualified, or disqualified
    query = UGExamResult.objects.filter(
        semester=target_sem,
        semester_result__in=['FAIL', 'PROMOTED', 'PARTLY_QUALIFIED', 'DISQUALIFIED']
    ).select_related('student')
    
    if target_reg_no:
        query = query.filter(student__registration_no=target_reg_no)
        
    results = query
    
    # Exclude 2024-28 batch? Optionally wait, the user didn't explicitly ask for batch exclusion this time
    # but let's follow normal bulk processing.
    
    total_students = results.count()
    print(f"Total students to process: {total_students}")
    
    exam_registrations_to_create = []
    assessments_to_create = []
    
    count = 0
    # Group assessments for bulk operations to manage memory
    BATCH_SIZE = 1000
    
    for res in results.iterator(chunk_size=BATCH_SIZE):
        count += 1
        student = res.student
        
        # 1. Create Exam Registration (only if not already created for BACK)
        # We'll create it directly in bulk later or ignore if it exists
        exam_reg = ExamRegistration(
            uid=uuid.uuid4(),
            student=student,
            is_open=True,
            sem=1,  # 1st Sem = 1
            session=target_session,
            status='PENDING'
        )
        exam_registrations_to_create.append(exam_reg)
        
        # 2. Get the latest assessments for the student in 1st semester
        student_assessments = StudentCourseAssessment.objects.filter(
            student=student,
            semester=target_sem
        ).order_by('-created_at')
        
        # We must uniquely identify by (paper_code, label) to only look at their latest attempt
        latest_assessments = {}
        for a in student_assessments:
            key = f"{a.paper_code}_{a.label}"
            if key not in latest_assessments:
                latest_assessments[key] = a
                
        # 3. Apply the logic to duplicate assessments
        for key, a in latest_assessments.items():
            if res.semester_result == 'FAIL':
                # Create all CIA and ESE for 'FAIL' student
                new_a = copy_assessment(a, target_session)
                assessments_to_create.append(new_a)
            else:
                # 'PROMOTED', 'PARTLY_QUALIFIED', 'DISQUALIFIED'
                # As per user update: only create entry with back type in which paper student was ind_is_pass=False
                if a.ind_is_pass is False:
                    new_a = copy_assessment(a, target_session)
                    assessments_to_create.append(new_a)
                    
        # Batch inserting to database
        if len(assessments_to_create) >= 5000:
            with transaction.atomic():
                # Ignore conflicts if exam registration already exists
                ExamRegistration.objects.bulk_create(exam_registrations_to_create, ignore_conflicts=True)
                StudentCourseAssessment.objects.bulk_create(assessments_to_create, ignore_conflicts=True)
            print(f"[{count}/{total_students}] Flushed batch of {len(assessments_to_create)} assessments.")
            exam_registrations_to_create.clear()
            assessments_to_create.clear()

    # Flush remaining
    if assessments_to_create or exam_registrations_to_create:
        with transaction.atomic():
            ExamRegistration.objects.bulk_create(exam_registrations_to_create, ignore_conflicts=True)
            StudentCourseAssessment.objects.bulk_create(assessments_to_create, ignore_conflicts=True)
        print(f"[{count}/{total_students}] Flushed final batch of {len(assessments_to_create)} assessments.")
        
    print("\n✅ Successfully created exam registration forms and back exam assessments.")

if __name__ == '__main__':
    main()
