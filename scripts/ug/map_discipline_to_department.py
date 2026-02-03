#!/usr/bin/env python
"""
Map discipline codes from StudentCourseAssessment json_data to UGDepartment
and update StudentCourseAssessment.department field for 2024-28 batch, 1st semester
"""

import os
import sys
import django
from django.db import transaction

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import StudentCourseAssessment, UGDepartment


def map_discipline_to_department():
    print("\n" + "="*90)
    print("MAPPING DISCIPLINE CODES TO STUDENTCOURSEASSESSMENT.DEPARTMENT")
    print("="*90)
    
    # Get assessments for 2024-28 batch, 1st semester
    # Filter by batch_code in json_data directly in the query for better performance
    assessments = StudentCourseAssessment.objects.filter(
        semester='2ND',
        json_data__batch_code='2024-28'
    ).only('id', 'json_data', 'department')
    
    total_assessments = assessments.count()
    print(f"\nTotal assessments for 2024-28 batch, 2nd sem: {total_assessments:,}")
    print(f"Note: Using iterator for memory-efficient processing...")
    
    # Get all departments for mapping
    departments = UGDepartment.objects.all()
    dept_map = {dept.code: dept for dept in departments if dept.code}
    
    # Add special mapping for CORP -> AC
    if 'AC' in dept_map:
        dept_map['CORP'] = dept_map['AC']
        print(f"\n✅ Added special mapping: CORP → AC (Accountancy)")
    
    # Remove M18 from mapping (should be skipped)
    if 'M18' in dept_map:
        del dept_map['M18']
        print(f"🚫 Excluded M18 from mapping (will be skipped)")
    
    print(f"\nDepartments available for mapping: {len(dept_map)}")
    print("\nSample department codes:")
    for code in list(dept_map.keys())[:10]:
        print(f"  - {code}: {dept_map[code].name}")
    
    # Track statistics
    assessments_updated = 0
    assessments_no_discipline = 0
    assessments_no_match = 0
    assessments_m18_skipped = 0
    discipline_codes_found = set()
    unmatched_codes = set()
    
    print(f"\n" + "="*90)
    print("Processing assessments for 2024-28 batch...")
    print("="*90)
    
    # Use iterator() for memory-efficient processing and bulk update
    batch_updates = []
    BATCH_SIZE = 500
    
    with transaction.atomic():
        for idx, assessment in enumerate(assessments.iterator(chunk_size=1000), 1):
            if idx % 10000 == 0:
                print(f"  Processed {idx:,}/{total_assessments:,}...")
            
            # Get discipline_code from json_data
            if not assessment.json_data:
                assessments_no_discipline += 1
                continue
            
            discipline_code = assessment.json_data.get('discipline_code')
            if not discipline_code:
                assessments_no_discipline += 1
                continue
            
            # Skip M18
            if discipline_code == 'M18':
                assessments_m18_skipped += 1
                continue
            
            discipline_codes_found.add(discipline_code)
            
            # Map to department
            department = dept_map.get(discipline_code)
            if not department:
                assessments_no_match += 1
                unmatched_codes.add(discipline_code)
                continue
            
            # Update assessment's department field
            if assessment.department != department:
                assessment.department = department
                batch_updates.append(assessment)
                assessments_updated += 1
                
                # Bulk save every BATCH_SIZE records
                if len(batch_updates) >= BATCH_SIZE:
                    StudentCourseAssessment.objects.bulk_update(batch_updates, ['department'])
                    batch_updates = []
        
        # Save remaining updates
        if batch_updates:
            StudentCourseAssessment.objects.bulk_update(batch_updates, ['department'])
    
    # Print results
    print(f"\n" + "="*90)
    print("MAPPING COMPLETE")
    print("="*90)
    print(f"\nTotal assessments for 2024-28 batch, 1st sem: {total_assessments:,}")
    print(f"✅ Assessments updated with department: {assessments_updated:,}")
    print(f"🚫 M18 assessments (skipped): {assessments_m18_skipped:,}")
    print(f"⚠️  Assessments with no discipline_code in json_data: {assessments_no_discipline:,}")
    print(f"⚠️  Assessments with unmatched discipline_code: {assessments_no_match:,}")
    
    print(f"\n\nDiscipline codes found ({len(discipline_codes_found)}):")
    for code in sorted(discipline_codes_found):
        status = "✅ Mapped" if code in dept_map else "❌ Not mapped"
        dept_name = dept_map[code].name if code in dept_map else "N/A"
        print(f"  {code:10s} → {dept_name:50s} {status}")
    
    if unmatched_codes:
        print(f"\n\nUnmatched discipline codes (need departments created):")
        for code in sorted(unmatched_codes):
            print(f"  - {code}")
    
    print(f"\n" + "="*90)


if __name__ == '__main__':
    map_discipline_to_department()
