import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')

import django
django.setup()

from ug.models import StudentCourseAssessment

def run():
    print("Updating missing college_code in StudentCourseAssessment (LOCAL/DEFAULT DB)...")
    
    # Target only local db & records where college_code is currently null
    assessments_def = StudentCourseAssessment.objects.filter(
        college_code__isnull=True
    ).select_related('student__college')
    
    total_def = assessments_def.count()
    print(f"Total local assessments missing college_code: {total_def}")
    
    if total_def == 0:
        print("Nothing to update!")
        return
        
    to_update_def = []
    count_def = 0
    updated_def = 0
    
    for a in assessments_def.iterator(chunk_size=2000):
        count_def += 1
        if count_def % 10000 == 0:
            print(f"Processed {count_def} / {total_def} (Local)")
            
        # Get college directly from student.college as requested
        student_college = a.student.college if a.student else None
        
        if student_college:
            correct_code = student_college.college_code
            if correct_code:  # check again just to be perfectly safe
                a.college_code = correct_code
                to_update_def.append(a)
                
        if len(to_update_def) >= 2000:
            StudentCourseAssessment.objects.bulk_update(to_update_def, ['college_code'], batch_size=1000)
            updated_def += len(to_update_def)
            to_update_def.clear()
            
    if to_update_def:
        StudentCourseAssessment.objects.bulk_update(to_update_def, ['college_code'], batch_size=1000)
        updated_def += len(to_update_def)
        
    print(f"✅ Successfully updated {updated_def} missing college_codes on LOCAL DB using student college.")

if __name__ == '__main__':
    run()
