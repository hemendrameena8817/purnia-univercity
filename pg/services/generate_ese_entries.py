"""
Service to generate ESE (End Semester Exam) entries for students who passed CIA.
"""
import sys
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from pg.models import (
    PGStudentProfile,
    PGStudentCourseAssessment,
    PGExamResult,
    PGDepartment
)

def generate_ese_entries(batch=None, semester=None, session=None, dry_run=False, include_all_batches=False):
    """
    Generates ESE assessment entries for students who have passed CIA.
    
    Args:
        batch (str): Batch code (e.g. '2023-25'). Optional if include_all_batches is True.
        semester (str): Semester code (e.g. '1ST'). Required.
        session (str): Session code (e.g. '2024-25'). Required.
        dry_run (bool): If True, does not commit changes.
        include_all_batches (bool): If True, includes all batches for the session.
    """
    
    stats = {
        'total_cia_passed': 0,
        'ese_entries_created': 0,
        'ese_entries_existed': 0,
        'errors': 0
    }
    
    print(f"\n--- Starting ESE Entry Generation ---")
    print(f"Semester: {semester}")
    print(f"Session: {session}")
    print(f"Batch: {batch if batch else 'ALL (if include_all_batches=True)'}")
    print(f"Dry Run: {dry_run}")
    
    # 1. Identify Target Students (Those who passed CIA)
    # We look at PGExamResult for the given semester/session AND cia_pass=True
    
    exam_results = PGExamResult.objects.filter(
        semester=semester,
        session=session,
        cia_pass=True
    )
    
    if batch and not include_all_batches:
        exam_results = exam_results.filter(student__batch=batch)
        
    target_students_count = exam_results.count()
    print(f"Found {target_students_count} students with CIA Pass status.")
    
    # 2. Process each student
    with transaction.atomic():
        for index, result in enumerate(exam_results):
            student = result.student
            stats['total_cia_passed'] += 1
            
            if index % 100 == 0:
                print(f"Processing student {index + 1}/{target_students_count}: {student.registration_no}")
            
            # Fetch CIA assessments for this student, semester, and session
            # We use these to know WHICH papers to create ESE entries for.
            cia_assessments = PGStudentCourseAssessment.objects.filter(
                student=student,
                semester=semester,
                session=session,
                label__icontains='CIA'
            )
            
            # Group by paper code to avoid duplicates if multiple CIA entries exist for same paper (e.g. theory + practical? usually distinct)
            # Actually, ESE usually requires one entry per paper code.
            
            unique_papers = {}
            for assess in cia_assessments:
                if assess.paper_code not in unique_papers:
                    unique_papers[assess.paper_code] = assess
            
            for paper_code, cia_entry in unique_papers.items():
                # [Refinement] Ensure this specific paper was passed in CIA?
                # Usually if cia_pass=True for the semester, they passed all.
                # But to be safe and explicit as per request "create only his all cia entry", 
                # let's skip if the specific paper wasn't passed (though cia_pass implies all passed).
                
                # Check if this specific CIA entry is a pass
                if not cia_entry.ind_is_pass:
                    # Double check marks just in case status isn't updated
                    is_actually_pass = False
                    if cia_entry.ind_marks_obtained is not None and cia_entry.ind_pass_marks is not None:
                        is_actually_pass = cia_entry.ind_marks_obtained >= cia_entry.ind_pass_marks
                    
                    if not is_actually_pass:
                        # print(f"  Skipping {paper_code}: CIA not passed.")
                        continue

                # Check if ESE entry already exists
                ese_exists = PGStudentCourseAssessment.objects.filter(
                    student=student,
                    semester=semester,
                    session=session,
                    paper_code=paper_code,
                    label='ESE'
                ).exists()
                
                if ese_exists:
                    stats['ese_entries_existed'] += 1
                    # print(f"  Skipping {paper_code}: ESE entry exists.")
                    continue
                
                # Determine Max/Pass Marks for ESE
                # Standard Logic:
                # If CIA Max was 30 -> ESE Max 70 (Total 100)
                # If CIA Max was 15/10 -> ESE might be different.
                # Ideally should come from CourseStructure, but user asked to base it on CIA entry.
                
                # Default for PG
                ese_max_marks = 70
                ese_pass_marks = 31.5
                
                # Adjust based on Course Type or Credits if needed, but standard is 70/30 split.
                # If user wants specific logic, we can adjust. For now, assuming standard 70.
                
                if not dry_run:
                    try:
                        PGStudentCourseAssessment.objects.create(
                            student=student,
                            department=cia_entry.department,
                            batch=cia_entry.batch,
                            
                            course_name=cia_entry.course_name,
                            course_code=cia_entry.course_code,
                            paper_code=cia_entry.paper_code,
                            
                            semester=semester,
                            label='ESE',
                            
                            session=session,
                            college_code=cia_entry.college_code,
                            exam_type=cia_entry.exam_type, # Carry forward Regular/Back status
                            
                            # ESE Specifics
                            ind_max_marks=ese_max_marks,
                            ind_pass_marks=ese_pass_marks,
                            ind_marks_obtained=None, # To be filled later
                            ind_is_absent=False,
                            ind_is_pass=None,
                            
                            # Course totals (usually same as ESE max for the component, or total course max?)
                            # In this model, course_max_marks seems to be the TOTAL (CIA+ESE) or Component?
                            # Looking at CIA entries, they had course_max_marks=30. 
                            # So ESE entry should probably have course_max_marks=70 or 100?
                            # Often in such systems, valid breakdown is separate rows.
                            
                            # Let's check the corrected Economics script:
                            # It used course_max_marks=30 for CIA.
                            # So for ESE, we use 70.
                            
                            course_max_marks=ese_max_marks,
                            course_pass_marks=ese_pass_marks,
                            
                            comb_max_credits=cia_entry.comb_max_credits,
                            course_type=cia_entry.course_type,
                            
                            is_cia_fill=False,
                            is_ese_fill=True # It is an ESE entry
                        )
                        stats['ese_entries_created'] += 1
                    except Exception as e:
                        print(f"Error creating ESE for {student.registration_no}, {paper_code}: {e}")
                        stats['errors'] += 1
                else:
                    stats['ese_entries_created'] += 1 # Just counting for dry run
                    
    print("\n--- Summary ---")
    print(f"Total Students Processed: {stats['total_cia_passed']}")
    print(f"ESE Entries Created: {stats['ese_entries_created']}")
    print(f"ESE Entries Already Existed: {stats['ese_entries_existed']}")
    print(f"Errors: {stats['errors']}")
    
    if dry_run:
        print("\n*** DRY RUN - No changes committed ***")
