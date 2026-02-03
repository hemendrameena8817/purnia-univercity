#!/usr/bin/env python
"""
Bulk Update StudentCourseAssessment Course Type and Code

Matches StudentCourseAssessment.course_code (last 4 digits) with CourseStructure.code
and updates course_type and course_code fields.

Example:
- CourseStructure has code "MDC-1"
- StudentCourseAssessment course_code ends with last 4 digits matching
- Update: course_type = "MDC", course_code = "MDC-1"
"""

import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import StudentCourseAssessment, CommonCourseStructure, UGBatch
from django.db import transaction

def bulk_update_course_type_and_code():
    """
    Bulk update StudentCourseAssessment for batch 2024-28
    """
    print("\n" + "="*90)
    print("BULK UPDATE: StudentCourseAssessment Course Type & Code")
    print("="*90)
    
    # Get batch
    batch = UGBatch.objects.filter(name='2024-28').first()
    if not batch:
        print("❌ Batch 2024-28 not found!")
        return
    
    print(f"\nBatch: {batch.name}")
    
    # Get all StudentCourseAssessment records for the batch
    assessments = StudentCourseAssessment.objects.filter(
        student__batch=batch
    ).select_related('student')
    
    total_assessments = assessments.count()
    print(f"Total assessments to process: {total_assessments:,}")
    
    # Get all CommonCourseStructure records
    course_structures = CommonCourseStructure.objects.all()
    
    # Build mapping: last 4 chars of code -> CommonCourseStructure
    # Example: Code "MDC-1" -> last 4 chars: "DC-1"
    code_mapping = {}
    for cs in course_structures:
        if cs.code and len(cs.code) >= 4:
            last_4 = cs.code[-4:]  # Get last 4 characters
            if last_4 not in code_mapping:
                code_mapping[last_4] = []
            code_mapping[last_4].append({
                'full_code': cs.code,
                'course_type': cs.course_type,
                'course_structure': cs
            })
    
    print(f"\nCommonCourseStructure mappings loaded: {len(code_mapping)} unique patterns")
    print("\nSample mappings (last 4 digits -> course info):")
    for key, values in list(code_mapping.items())[:10]:
        print(f"  ...{key} → {[v['full_code'] for v in values]}")
    
    # Process assessments
    updated_count = 0
    not_matched_count = 0
    not_matched_patterns = set()
    
    print(f"\n" + "="*90)
    print("Processing assessments...")
    print("="*90)
    
    with transaction.atomic():
        for idx, assessment in enumerate(assessments, 1):
            if idx % 1000 == 0:
                print(f"  Processed {idx:,}/{total_assessments:,}...")
            
            # Get last 4 digits of paper_code
            if not assessment.paper_code or len(assessment.paper_code) < 4:
                not_matched_count += 1
                continue
            
            paper_last_4 = assessment.paper_code[-4:]  # Last 4 digits of paper_code
            
            # Match against CommonCourseStructure code (last 4 chars)
            if paper_last_4 in code_mapping:
                # Get first match (if multiple, take first one)
                mapping = code_mapping[paper_last_4][0]
                
                # Update assessment
                assessment.course_type = mapping['course_type']
                assessment.course_code = mapping['full_code']
                assessment.save(update_fields=['course_type', 'course_code'])
                
                updated_count += 1
            else:
                not_matched_count += 1
                not_matched_patterns.add(f"{assessment.paper_code} (last 4: {paper_last_4})")
    
    print(f"\n" + "="*90)
    print("UPDATE COMPLETE")
    print("="*90)
    print(f"\nTotal assessments: {total_assessments:,}")
    print(f"✅ Updated: {updated_count:,}")
    print(f"⚠️  Not matched: {not_matched_count:,}")
    
    if not_matched_patterns:
        print(f"\nNot matched paper_codes (sample):")
        for pattern in list(not_matched_patterns)[:10]:
            print(f"  - {pattern}")
    
    print("\n" + "="*90)

if __name__ == '__main__':
    bulk_update_course_type_and_code()
