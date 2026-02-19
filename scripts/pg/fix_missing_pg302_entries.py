import os
import sys
import django
from decimal import Decimal

# Setup path to project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.models import PGStudentProfile, PGStudentCourseAssessment, PGCourseStructure

# Target Student IDs (Registration No. or Roll No.)
TARGET_IDS = [
    '2332M010008',
    '2312M010008',
    '1804-28015',
    '1912B030015',
    '1933B030005',
    '2109B350067'
]

def run():
    print("Starting manual insertion for PG-302 entries...")
    
    for student_id in set(TARGET_IDS):
        print(f"\nProcessing ID: {student_id}")
        
        # 1. Find Student
        # Try finding by registration_no first
        student = PGStudentProfile.objects.filter(registration_no=student_id).first()
        if not student:
            # Fallback to finding by roll_no if registration lookup fails
            student = PGStudentProfile.objects.filter(roll_no=student_id).first()
            
        if not student:
            print(f"ERROR: Student not found for ID: {student_id}")
            continue
            
        print(f"Found Student: {student.first_name} {student.last_name or ''} (Reg: {student.registration_no}, Roll: {student.roll_no})")
        
        # 1.5 Clean up incorrect '302' entries from previous run
        incorrect_entries = PGStudentCourseAssessment.objects.filter(
            student=student, 
            paper_code='302'
        )
        if incorrect_entries.exists():
            print(f"Deleting {incorrect_entries.count()} incorrect '302' entries...")
            incorrect_entries.delete()

        # 1.6 Determine Exam Type from existing entries
        # User requested to check the examtype of particular user and create it same
        # We look for any other assessment for this student, ideally in the same semester (3RD)
        exam_type_to_use = 'REGULAR' # Default
        
        # Try finding an entry for 3rd semester first
        reference_entry = PGStudentCourseAssessment.objects.filter(
            student=student,
            semester='3RD'
        ).exclude(paper_code__in=['302', 'PG302']).first()
        
        if not reference_entry:
             # Fallback to any entry
             reference_entry = PGStudentCourseAssessment.objects.filter(student=student).first()
             
        if reference_entry:
            exam_type_to_use = reference_entry.exam_type
            print(f"Detected exam_type '{exam_type_to_use}' from reference entry (ID: {reference_entry.id})")
        else:
            print(f"Could not detect exam_type, defaulting to '{exam_type_to_use}'")

        # 2. Check for existing 'PG302' entry for this student
        existing = PGStudentCourseAssessment.objects.filter(
            student=student, 
            paper_code='PG302'
        ).first()

        if existing:
            print(f"Entry already exists for paper_code='PG302' (ID: {existing.id}). Updating to CIA/3RD/ExamType if needed.")
            needs_save = False
            if existing.course_name != "Economics of Growth & Development-II":
                 existing.course_name = "Economics of Growth & Development-II"
                 existing.course_code = "CC-XI"
                 needs_save = True
            
            if existing.label != 'CIA':
                existing.label = 'CIA'
                needs_save = True
                
            if existing.semester != '3RD':
                existing.semester = '3RD'
                needs_save = True

            if existing.exam_type != exam_type_to_use:
                existing.exam_type = exam_type_to_use
                needs_save = True
                
            # Update marks defaults for CIA if we are converting
            if existing.course_max_marks != 30:
                existing.course_max_marks = 30
                existing.ind_max_marks = 30
                existing.course_pass_marks = 13.5
                existing.ind_pass_marks = 13.5
                needs_save = True

            if needs_save:
                 existing.save()
                 print(f"Updated entry to CIA, 3RD Sem, marks structure, and exam_type='{exam_type_to_use}'.")
            continue

        # 3. Hardcoded Course Details for Economics
        course_name = "Economics of Growth & Development-II"
        course_code = "CC-XI"
        paper_code = "PG302"
        max_marks = 30  # CIA Max Marks
        pass_marks = 13.5 # CIA Pass Marks
        credits = 5 
        course_type = "CC"
        
        # 3.5 Try to resolve Batch ID
        from pg.models import PGBatch
        batch_obj = None
        
        # 3.5.1 Try from student profile
        if student.batch:
            batch_obj = PGBatch.objects.filter(name=student.batch).first()
            
        # 3.5.2 Fallback: Try from other assessments if not found
        if not batch_obj:
            ref_assessment = PGStudentCourseAssessment.objects.filter(student=student, batch__isnull=False).first()
            if ref_assessment:
                batch_obj = ref_assessment.batch
                print(f"Inferred batch '{batch_obj.name}' from other assessment (ID: {ref_assessment.id})")
        
        if batch_obj:
            print(f"Using Batch: {batch_obj.name}")
        else:
            print("WARNING: Could not determine Batch for student. Entry will have batch=None.")

        # 4. Create Entry
        try:
            assessment = PGStudentCourseAssessment.objects.create(
                student=student,
                
                # Use student's department. If null, try to infer? 
                # Student profile should have department.
                department=student.department,
                
                batch=batch_obj, 
                
                course_name=course_name,
                course_code=course_code,
                paper_code=paper_code, 
                
                semester='3RD', # Force 3RD as requested
                label='CIA',    # Force CIA as requested
                
                session=student.session,
                college_code=student.college.college_code if student.college else None,
                
                exam_type=exam_type_to_use,
                
                # Initial placeholder values for CIA
                ind_max_marks=30, 
                ind_pass_marks=13.5,
                ind_marks_obtained=None,
                ind_is_absent=False,
                ind_is_pass=None,
                
                comb_max_credits=credits,
                course_type=course_type,
                
                # Using course_max_marks field
                course_max_marks=30,
                course_pass_marks=13.5
            )
            print(f"SUCCESS: Created CIA assessment entry (ID: {assessment.id}) with exam_type '{exam_type_to_use}' and batch '{batch_obj.name if batch_obj else 'None'}' for student {student.registration_no}")
            
        except Exception as e:
            print(f"ERROR creating entry for {student_id}: {e}")
                


if __name__ == "__main__":
    run()
