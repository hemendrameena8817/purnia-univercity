#!/usr/bin/env python
"""
Map MJC, MIC, MDC course types from StudentCourseAssessment to UGStudentProfile
for 2024-28 batch, 1st semester students
"""

import os
import sys
import django
from django.db import transaction
from collections import defaultdict

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import StudentCourseAssessment, UGStudentProfile


def map_courses_to_student_profiles():
    print("\n" + "="*90)
    print("MAPPING MJC/MIC/MDC COURSES TO STUDENT PROFILES")
    print("="*90)
    
    # Get assessments for 2024-28 batch, 1st semester with department assigned
    assessments = StudentCourseAssessment.objects.filter(
        semester='1ST',
        json_data__batch_code='2024-28',
        department__isnull=False  # Only process assessments with department assigned
    ).select_related('student', 'department').only(
        'student_id', 'course_type', 'department_id'
    )
    
    total_assessments = assessments.count()
    print(f"\nTotal assessments with departments: {total_assessments:,}")
    
    # Group by student and course type to find their MJC/MIC/MDC departments
    student_courses = defaultdict(lambda: {'MJC': None, 'MIC': None, 'MDC': None})
    
    print(f"\n" + "="*90)
    print("Analyzing student course types...")
    print("="*90)
    
    for idx, assessment in enumerate(assessments.iterator(chunk_size=1000), 1):
        if idx % 10000 == 0:
            print(f"  Processed {idx:,}/{total_assessments:,}...")
        
        if not assessment.student or not assessment.course_type:
            continue
        
        course_type = assessment.course_type.upper()
        
        # Map MJC, MIC, MDC to student
        if course_type.startswith('MJC'):
            if not student_courses[assessment.student_id]['MJC']:
                student_courses[assessment.student_id]['MJC'] = assessment.department
        elif course_type.startswith('MIC'):
            if not student_courses[assessment.student_id]['MIC']:
                student_courses[assessment.student_id]['MIC'] = assessment.department
        elif course_type.startswith('MDC'):
            if not student_courses[assessment.student_id]['MDC']:
                student_courses[assessment.student_id]['MDC'] = assessment.department
    
    # Update student profiles
    print(f"\n" + "="*90)
    print("Updating student profiles...")
    print("="*90)
    
    students_updated = 0
    mjc_updated = 0
    mic_updated = 0
    mdc_updated = 0
    
    batch_updates = []
    BATCH_SIZE = 500
    
    for student_id, courses in student_courses.items():
        try:
            student = UGStudentProfile.objects.get(id=student_id)
            updated = False
            
            if courses['MJC'] and student.major_course != courses['MJC']:
                student.major_course = courses['MJC']
                mjc_updated += 1
                updated = True
            
            if courses['MIC'] and student.minor_course != courses['MIC']:
                student.minor_course = courses['MIC']
                mic_updated += 1
                updated = True
            
            if courses['MDC'] and student.mdc_course != courses['MDC']:
                student.mdc_course = courses['MDC']
                mdc_updated += 1
                updated = True
            
            if updated:
                batch_updates.append(student)
                students_updated += 1
                
                # Bulk save every BATCH_SIZE records
                if len(batch_updates) >= BATCH_SIZE:
                    UGStudentProfile.objects.bulk_update(
                        batch_updates, 
                        ['major_course', 'minor_course', 'mdc_course']
                    )
                    batch_updates = []
        
        except UGStudentProfile.DoesNotExist:
            continue
    
    # Save remaining updates
    if batch_updates:
        UGStudentProfile.objects.bulk_update(
            batch_updates, 
            ['major_course', 'minor_course', 'mdc_course']
        )
    
    # Print results
    print(f"\n" + "="*90)
    print("MAPPING COMPLETE")
    print("="*90)
    print(f"\nTotal students found: {len(student_courses):,}")
    print(f"✅ Students updated: {students_updated:,}")
    print(f"   - Major course (MJC) updated: {mjc_updated:,}")
    print(f"   - Minor course (MIC) updated: {mic_updated:,}")
    print(f"   - MDC course updated: {mdc_updated:,}")
    print(f"\n" + "="*90)


if __name__ == '__main__':
    map_courses_to_student_profiles()
