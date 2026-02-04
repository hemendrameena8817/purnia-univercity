from django.core.management.base import BaseCommand
from pg.models import PGStudentProfile, PGBatch, PGStudentCourseAssessment
from pg.services.result_service import PGResultService
import sys
import argparse

def calculate_results(batch_name=None, semester=None, session=None, registration_no=None, dry_run=True):
    """
    Calculate results filtered by Batch, Semester, Session, or Registration No.
    
    Args:
        batch_name (str): Batch Name (e.g., '2019-21')
        semester (str): Semester (e.g., '1ST')
        session (str): Session (e.g., '2019-20')
        registration_no (str): Student Registration Number (e.g., '190150300006')
        dry_run (bool): If True, DOES NOT SAVE changes to DB. Default is True.
    """
    # python manage.py shell -c "from pg.services.calculate_batch_results import calculate_results; calculate_results(registration_no='190150300006', semester='1ST', session='2019-20', dry_run=True)"
    # python manage.py shell -c "from pg.services.calculate_batch_results import calculate_results; calculate_results(registration_no='2112B050184', semester='1ST', session='2024-25', dry_run=True)"/
    # python manage.py shell -c "from pg.services.calculate_batch_results import calculate_results; calculate_results(batch_name='2019-21', semester='1ST', session='2019-20', dry_run=False)"
    print("=" * 100)
    print(f"STARTING RESULT CALCULATION")
    print(f"Filter Criteria -> Batch: {batch_name} | Semester: {semester} | Session: {session} | RegNo: {registration_no}")
    print(f"Dry Run Mode: {dry_run} {'(NO DB CHANGES)' if dry_run else '(SAVING TO DB)'}")
    print("=" * 100)

    # 1. Filter Students
    students = PGStudentProfile.objects.all()
    
    if registration_no:
        students = students.filter(registration_no=registration_no)
        print(f"✅ Filtered by Registration No '{registration_no}': {students.count()} students found")
    
    if batch_name:
        batch = PGBatch.objects.filter(name=batch_name).first()
        if not batch:
            print(f"❌ Batch '{batch_name}' not found!")
            return
        students = students.filter(batch=batch)
        print(f"✅ Filtered by Batch '{batch_name}': {students.count()} students found")
    elif not registration_no:
        print(f"⚠️ No Batch or Registration No specified. Searching all {students.count()} students.")

    if students.count() == 0:
        print("No students found matching the criteria.")
        return

    # 2. Process Students
    count = 0
    success_count = 0
    error_count = 0
    total_students = students.count()

    print(f"\nProcessing {total_students} students...")
    print("-" * 100)

    for idx, student in enumerate(students, 1):
        # Find relevant assessments for this student matching filters
        student_assessments = PGStudentCourseAssessment.objects.filter(student=student)
        
        if semester:
            student_assessments = student_assessments.filter(semester=semester)
        if session:
            student_assessments = student_assessments.filter(session=session)
            
        # Get unique combinations of (semester, session) to process
        # Using set() to ensure absolute uniqueness and avoid any DB-level distinct issues
        combinations = set(student_assessments.values_list('semester', 'session'))
        
        # If no assessments match, skip student
        if not combinations:
            continue
            
        print(f"[{idx}/{total_students}] Processing: {student.first_name} {student.last_name} ({student.registration_no})")
        
        for sem, sess in combinations:
            if not sess:
                if session is None: 
                    print(f"    ⚠️ Skipping {sem} due to missing session in data")
                    continue
                
            try:
                # Process Result
                result = PGResultService.process_student(
                    student_id=student.id,
                    semester=sem,
                    session=sess,
                    dry_run=dry_run 
                )
                
                # Check for explicit failure in return
                if not result.get('success'):
                    print(f"    ❌ Sem {sem} (Session: {sess}) Failed: {result.get('error')}")
                    error_count += 1
                    continue

                # Extract SGPA and Result for display
                summary = result.get('summary', {})
                sgpa = summary.get('sgpa')
                res_status = summary.get('semester_result')
                eff_credits = summary.get('total_max_credits')
                
                print(f"    ✅ Sem {sem} Result Calculated:")
                print(f"       Status: {res_status} | SGPA: {sgpa} | Total Credits: {eff_credits}")
                
                # PRINT DETAILED COURSE BREAKDOWN
                print(f"       {'Course':<10} {'Marks':<10} {'Grade':<8} {'GP':<5} {'Cr.Earn':<10} {'Points':<8}")
                print(f"       {'-'*10} {'-'*10} {'-'*8} {'-'*5} {'-'*10} {'-'*8}")
                
                for course in summary.get('course_results', []):
                    code = course.get('paper_code', 'N/A')
                    marks = f"{course.get('total_marks', 0)}/{course.get('total_max_marks', 0)}"
                    grade = course.get('final_grade', '-')
                    gp = course.get('grade_point', 0)
                    cr_earned = course.get('credits_earned', 0)
                    points = course.get('course_grade_point', 0)
                    
                    print(f"       {code:<10} {marks:<10} {grade:<8} {gp:<5} {cr_earned:<10} {points:<8}")
                print("\n")
                
                if sgpa is not None:
                     success_count += 1
            except Exception as e:
                print(f"    ❌ Sem {sem} (Session: {sess}) Failed: {str(e)}")
                error_count += 1
        
        count += 1

    print("\n" + "=" * 100)
    print("CALCULATION COMPLETE")
    print("=" * 100)
    print(f"Students Processed: {count}/{total_students}")
    print(f"Successful Calculations: {success_count}")
    print(f"Errors: {error_count}")
    if dry_run:
        print("\nNOTE: This was a DRY RUN. No data was saved to the database.")
        print("To save changes, run with dry_run=False")
    print("=" * 100)

if __name__ == "__main__":
    # Allow running as a script with arguments
    # Usage: python manage.py shell -c "from pg.services.calculate_batch_results import calculate_results; calculate_results(batch_name='2019-21', semester='1ST', session='2019-20', dry_run=True)"
    pass
