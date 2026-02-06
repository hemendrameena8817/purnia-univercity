#!/usr/bin/env python
"""
Report students where MJC/MIC/MDC departments differ between 
UGStudentProfile (from sem 1) and Semester 2 assessments
"""

import os
import sys
import django
from collections import defaultdict

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import StudentCourseAssessment, UGStudentProfile


def generate_course_mismatch_report():
    print("\n" + "="*90)
    print("COURSE DEPARTMENT MISMATCH REPORT (Semester 1 vs Semester 2)")
    print("="*90)
    
    # Get semester 2 assessments with departments for 2024-28 batch
    sem2_assessments = StudentCourseAssessment.objects.filter(
        semester='2ND',
        json_data__batch_code='2024-28',
        department__isnull=False
    ).select_related('student', 'department').only(
        'student_id', 'course_type', 'department_id'
    )
    
    print(f"Semester 2 assessments with departments: {sem2_assessments.count():,}")
    
    # Get unique student IDs from semester 2 assessments
    student_ids_with_sem2 = set()
    
    # Build semester 2 course mapping for each student
    sem2_courses = defaultdict(lambda: {'MJC': None, 'MIC': None, 'MDC': None})
    
    print("\nAnalyzing semester 2 courses...")
    for assessment in sem2_assessments.iterator(chunk_size=1000):
        if not assessment.course_type or not assessment.student_id:
            continue
        
        student_ids_with_sem2.add(assessment.student_id)
        course_type = assessment.course_type.upper()
        
        if course_type.startswith('MJC'):
            if not sem2_courses[assessment.student_id]['MJC']:
                sem2_courses[assessment.student_id]['MJC'] = assessment.department
        elif course_type.startswith('MIC'):
            if not sem2_courses[assessment.student_id]['MIC']:
                sem2_courses[assessment.student_id]['MIC'] = assessment.department
        elif course_type.startswith('MDC'):
            if not sem2_courses[assessment.student_id]['MDC']:
                sem2_courses[assessment.student_id]['MDC'] = assessment.department
    
    # Get students who have semester 2 data
    students = UGStudentProfile.objects.filter(
        id__in=student_ids_with_sem2
    ).select_related('major_course', 'minor_course', 'mdc_course')
    
    total_students = students.count()
    print(f"\nTotal students with semester 2 data: {total_students:,}")
    
    # Compare and find mismatches
    mismatches = []
    
    print("\nComparing semester 1 (profile) vs semester 2 (assessments)...")
    for student in students.iterator(chunk_size=1000):
        sem2 = sem2_courses.get(student.id)
        if not sem2:
            continue  # Student has no sem 2 data
        
        student_mismatches = []
        
        # Check MJC (Major Course)
        if student.major_course and sem2['MJC']:
            if student.major_course.id != sem2['MJC'].id:
                student_mismatches.append({
                    'course_type': 'MJC (Major)',
                    'sem1_dept': student.major_course.name,
                    'sem1_code': student.major_course.code,
                    'sem2_dept': sem2['MJC'].name,
                    'sem2_code': sem2['MJC'].code
                })
        
        # Check MIC (Minor Course)
        if student.minor_course and sem2['MIC']:
            if student.minor_course.id != sem2['MIC'].id:
                student_mismatches.append({
                    'course_type': 'MIC (Minor)',
                    'sem1_dept': student.minor_course.name,
                    'sem1_code': student.minor_course.code,
                    'sem2_dept': sem2['MIC'].name,
                    'sem2_code': sem2['MIC'].code
                })
        
        # Check MDC
        if student.mdc_course and sem2['MDC']:
            if student.mdc_course.id != sem2['MDC'].id:
                student_mismatches.append({
                    'course_type': 'MDC',
                    'sem1_dept': student.mdc_course.name,
                    'sem1_code': student.mdc_course.code,
                    'sem2_dept': sem2['MDC'].name,
                    'sem2_code': sem2['MDC'].code
                })
        
        if student_mismatches:
            mismatches.append({
                'username': student.registration_no,
                'student_name': student.name,
                'mismatches': student_mismatches
            })
    
    # Print report
    print(f"\n" + "="*90)
    print("MISMATCH REPORT")
    print("="*90)
    print(f"\nTotal students with mismatches: {len(mismatches):,}\n")
    
    if mismatches:
        for idx, student_data in enumerate(mismatches, 1):
            print(f"\n{idx}. Username: {student_data['username']}")
            print(f"   Name: {student_data['student_name']}")
            print(f"   Mismatches:")
            for mismatch in student_data['mismatches']:
                print(f"      • {mismatch['course_type']}:")
                print(f"        Sem 1: {mismatch['sem1_dept']} ({mismatch['sem1_code']})")
                print(f"        Sem 2: {mismatch['sem2_dept']} ({mismatch['sem2_code']})")
    else:
        print("✅ No mismatches found! All students have consistent departments.")
    
    print(f"\n" + "="*90)
    
    # Save to file
    report_file = '/Users/anuprash/Desktop/projects/pup-umis-backend/course_mismatch_report.txt'
    with open(report_file, 'w') as f:
        f.write("="*90 + "\n")
        f.write("COURSE DEPARTMENT MISMATCH REPORT (Semester 1 vs Semester 2)\n")
        f.write("="*90 + "\n\n")
        f.write(f"Total students with mismatches: {len(mismatches)}\n\n")
        
        if mismatches:
            for idx, student_data in enumerate(mismatches, 1):
                f.write(f"\n{idx}. Username: {student_data['username']}\n")
                f.write(f"   Name: {student_data['student_name']}\n")
                f.write(f"   Mismatches:\n")
                for mismatch in student_data['mismatches']:
                    f.write(f"      • {mismatch['course_type']}:\n")
                    f.write(f"        Sem 1: {mismatch['sem1_dept']} ({mismatch['sem1_code']})\n")
                    f.write(f"        Sem 2: {mismatch['sem2_dept']} ({mismatch['sem2_code']})\n")
        else:
            f.write("✅ No mismatches found! All students have consistent departments.\n")
    
    print(f"\n📄 Report saved to: {report_file}")
    print("="*90 + "\n")


if __name__ == '__main__':
    generate_course_mismatch_report()
