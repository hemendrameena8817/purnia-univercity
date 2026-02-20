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
# python pg/services/run_generate_ese_entries.py --batch 2024-26 --semester 3RD --session 2024-25 --dry-run/
def generate_ese_entries(batch=None, semester=None, session=None, dry_run=False, include_all_batches=False, registration_no=None, registration_nos=None):
    """
    Generates ESE assessment entries for students who have passed CIA.
    
    Args:
        batch (str): Batch code (e.g. '2023-25'). Optional if include_all_batches is True.
        semester (str): Semester code (e.g. '1ST'). Required.
        session (str): Session code (e.g. '2024-25'). Required.
        dry_run (bool): If True, does not commit changes.
        include_all_batches (bool): If True, includes all batches for the session.
        registration_no (str): If set, process only this single student by registration number.
        registration_nos (list): If set, process only these students (list of registration numbers).
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

    # Single student filter
    if registration_no:
        exam_results = exam_results.filter(student__registration_no=registration_no)
        print(f"Single student mode: {registration_no}")
    # Multiple students filter
    elif registration_nos:
        exam_results = exam_results.filter(student__registration_no__in=registration_nos)
        print(f"Multiple students mode: {len(registration_nos)} students")
    elif batch and not include_all_batches:
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
                # Fetch from PGCourseStructure as per user request
                from pg.models import PGCourseStructure
                
                # Default values
                # ese_max_marks = 70
                # ese_pass_marks = 31.5
                
                # Try to find structure
                # We match by course_code/paper_code and department/batch
                # PGCourseStructure is specific to Department and Batch usually.
                
                structure = PGCourseStructure.objects.filter(
                    code=cia_entry.course_code, # 'code' field in PGCourseStructure usually holds the course code like CC-1
                    # Also try to match department or batch if possible to be precise
                    department=student.department
                ).first()
                
                if not structure:
                    # Try by paper_code
                     structure = PGCourseStructure.objects.filter(
                        paper_code=cia_entry.paper_code,
                        department=student.department
                    ).first()

                if structure:
                    if structure.max_marks:
                        ese_max_marks = structure.max_marks
                    
                    if structure.min_marks:
                        ese_pass_marks = structure.min_marks
                    else:
                        # Fallback calculation if min_marks not set
                         ese_pass_marks = float(ese_max_marks) * 0.45
                        
                    # print(f"  Found PGCourseStructure for {paper_code}: Max {ese_max_marks}, Pass {ese_pass_marks}")
                else:
                    # print(f"  WARNING: PGCourseStructure not found for {paper_code} in {student.department}. Using defaults.")
                    pass

                # Explicitly fetch exam type from 2025-26 3RD sem CIA entry
                # This ensures we get the correct status (Regular/Back) even if running for a different context or if multiple exist
                target_cia_for_type = PGStudentCourseAssessment.objects.filter(
                    student=student,
                    paper_code=paper_code,
                    semester='3RD',
                    session='2025-26',
                    label__icontains='CIA'
                ).first()
                
                final_exam_type = cia_entry.exam_type
                if target_cia_for_type:
                    final_exam_type = target_cia_for_type.exam_type
                
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
                            exam_type=final_exam_type, # Carry forward Regular/Back status from 2025-26 3RD sem lookup
                            
                            # ESE Specifics
                            ind_max_marks=ese_max_marks,
                            ind_pass_marks=ese_pass_marks,
                            ind_marks_obtained=None, # To be filled later
                            ind_is_absent=False,
                            ind_is_pass=None,
                            
                            course_max_marks=None, # Using ESE max as course max for this entry
                            course_pass_marks=None,
                            
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
