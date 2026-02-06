from django.core.management.base import BaseCommand
from pg.models import PGStudentProfile, PGBatch, PGStudentCourseAssessment, PGExamResult
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
    # python manage.py shell -c "from pg.services.calculate_batch_results import calculate_results; calculate_results(registration_no='1934B090018', semester='1ST', session='2024-25', dry_run=True)"/
    # python manage.py shell -c "from pg.services.calculate_batch_results import calculate_results; calculate_results(batch_name='2024-26', semester='1ST', session='2024-25', dry_run=False)"
    print("=" * 100)
    print(f"STARTING RESULT CALCULATION")
    print(f"Filter Criteria -> Batch: {batch_name} | Semester: {semester} | Session: {session} | RegNo: {registration_no}")
    print(f"Dry Run Mode: {dry_run} {'(NO DB CHANGES)' if dry_run else '(SAVING TO DB)'}")
    print("=" * 100)

    # =========================================================================
    # STEP 1: FILTER STUDENTS
    # =========================================================================
    students = PGStudentProfile.objects.all()
    
    # Priority 1: Filter by specific Registration Number
    if registration_no:
        students = students.filter(registration_no=registration_no)
        print(f"✅ Filtered by Registration No '{registration_no}': {students.count()} students found")
    
    # Priority 2: Filter by Batch name (if no registration_no)
    if batch_name:
        batch = PGBatch.objects.filter(name=batch_name).first()
        if not batch:
            print(f"❌ Batch '{batch_name}' not found!")
            return
        students = students.filter(batch=batch)
        print(f"✅ Filtered by Batch '{batch_name}': {students.count()} students found")
    elif not registration_no:
        print(f"⚠️ No Batch or Registration No specified. Searching all {students.count()} students.")

    # Halt if no students found
    if students.count() == 0:
        print("No students found matching the criteria.")
        return

    # =========================================================================
    # STEP 2: PROCESS STUDENTS & CALCULATE RESULTS
    # =========================================================================
    count = 0
    success_count = 0
    error_count = 0
    total_students = students.count()

    print(f"\nProcessing {total_students} students...")
    print("-" * 100)

    for idx, student in enumerate(students, 1):
        # We look for all assessment marks (PGStudentCourseAssessment) belonging to this student
        student_assessments = PGStudentCourseAssessment.objects.filter(student=student)
        
        # Apply the user-provided Semester and Session filters to the assessment search
        if semester:
            student_assessments = student_assessments.filter(semester=semester)
        if session:
            student_assessments = student_assessments.filter(session=session)
            
        # Extract unique (semester, session) pairs from the student's marks.
        # This handles cases where a student might have backlogs or multiple registrations.
        combinations = set(student_assessments.values_list('semester', 'session'))
        
        # Skip if no marks are found for the filters provided
        if not combinations:
            continue
            
        print(f"[{idx}/{total_students}] Processing: {student.first_name} {student.last_name} ({student.registration_no})")
        
        # Loop through each semester/session combination found for this student
        for sem, sess in combinations:
            # Session is mandatory for result calculation
            if not sess:
                if session is None: 
                    print(f"    ⚠️ Skipping {sem} due to missing session in data")
                    continue
                
            # Validating CIA Pass status before calling the heavy service
            # This avoids "Errors" in the output for students who simply haven't passed CIA yet.
            exam_result = PGExamResult.objects.filter(
                student=student,
                semester=sem,
                session=sess
            ).first()
            
            if not exam_result:
                print(f"    ⚠️ Skipping {sem}: CIA Result (Step 1) not found. Please run Step 1 CIA Processing first.")
                continue
                
            if not exam_result.cia_pass:
                print(f"    ⚠️ Skipping {sem}: Student has NOT passed all CIA assessments.")
                continue

            try:
                # CALL THE CORE SERVICE: This is where the heavy lifting happens.
                # It calculates marks, grades, SGPA, and creates next-semester registration.
                result = PGResultService.process_student(
                    student_id=student.id,
                    semester=sem,
                    session=sess,
                    dry_run=dry_run 
                )
                
                # If the service returns success=False, something went wrong with the data lookup
                if not result.get('success'):
                    print(f"    ❌ Sem {sem} (Session: {sess}) Failed: {result.get('error')}")
                    error_count += 1
                    continue

                # -------------------------------------------------------------
                # DISPLAY DETAILED RESULTS
                # -------------------------------------------------------------
                summary = result.get('summary', {})
                sgpa = summary.get('sgpa')
                res_status = summary.get('semester_result')
                max_credits = summary.get('total_max_credits')
                earned_credits = summary.get('total_credits_earned')
                
                print(f"    ✅ Sem {sem} Result Calculated:")
                print(f"       Status: {res_status} | SGPA: {sgpa} | Max Credits: {max_credits} | Earned: {earned_credits}")
                
                # COURSE BREAKDOWN HEADERS
                print(f"       {'Course':<10} {'Marks':<10} {'Grade':<8} {'GP':<5} {'Cr.Earn':<10} {'Points':<8}")
                print(f"       {'-'*10} {'-'*10} {'-'*8} {'-'*5} {'-'*10} {'-'*8}")
                
                # Loop through each course result in the summary
                for course in summary.get('course_results', []):
                    code = course.get('paper_code', 'N/A')
                    # total_marks = (CIA + ESE combined)
                    marks = f"{course.get('total_marks', 0)}/{course.get('total_max_marks', 0)}"
                    grade = course.get('final_grade', '-')
                    gp = course.get('grade_point', 0)     # E.g. 7
                    cr_earned = course.get('credits_earned', 0) # E.g. 5
                    points = course.get('course_grade_point', 0) # GP * Cr.Earn
                    
                    print(f"       {code:<10} {marks:<10} {grade:<8} {gp:<5} {cr_earned:<10} {points:<8}")
                print("\n")
                
                if sgpa is not None:
                     success_count += 1
            except Exception as e:
                print(f"    ❌ Sem {sem} (Session: {sess}) Failed: {str(e)}")
                error_count += 1
        
        count += 1

    # =========================================================================
    # STEP 3: FINAL SUMMARY REPORT
    # =========================================================================
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
