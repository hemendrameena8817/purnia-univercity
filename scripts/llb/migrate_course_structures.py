# -*- coding: utf-8 -*-
"""
Migrate ONLY Course Structures from StagingLLBResultCurrent to LLB app models

This script will:
1. Create LLBCourseStructure (individual CIA/ESE entries)
2. Create CommonCourseStructure (combined subject entries)

Run this:
poetry run python scripts/llb/migrate_course_structures.py
"""

import os
import sys
import django

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import StagingLLBResultCurrent
from llb.models import LLBCourseStructure, CommonCourseStructure

def get_assessment_label(status):
    """Convert staging status to assessment label"""
    if not status:
        return "Unknown"
    
    status = status.upper().strip()
    
    # Map staging status to assessment labels
    if status == "END_TERM":
        return "ESE"  
    elif status == "MID_TERM":
        return "CIA"  
    elif status == "LAB":
        return "CIA"
    else:
        return status

def get_course_code(paper_code):
    """Generate course_code based on paper_code"""
    if not paper_code or paper_code == 'UNKNOWN':
        return 'UNKNOWN'
    
    # Extract semester and paper number from paper_code
    # LLB101 -> 1st semester, 1st paper -> course_code "I"
    # LLB102 -> 1st semester, 2nd paper -> course_code "II"
    # LLB201 -> 2nd semester, 1st paper -> course_code "I"
    # LLB202 -> 2nd semester, 2nd paper -> course_code "II"
    
    try:
        if len(paper_code) >= 6 and paper_code.startswith('LLB'):
            # Get the last 3 digits (e.g., "101", "102", "201", "202")
            code_part = paper_code[-3:]
            semester_num = int(code_part[0])  # First digit = semester
            paper_num = int(code_part[1:])     # Last two digits = paper number
            
            # Map paper number to Roman numerals
            roman_numerals = {
                1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
                6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X',
                11: 'XI', 12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV'
            }
            
            return roman_numerals.get(paper_num, str(paper_num))
        else:
            return 'UNKNOWN'
    except:
        return 'UNKNOWN'

def clean_subject_name(name):
    """Clean and normalize subject name"""
    if not name:
        return 'Unknown Subject'
    
    # Remove newlines, extra spaces, and normalize
    name = name.replace('\n', ' ').replace('\r', ' ')
    name = ' '.join(name.split())  # Remove extra whitespace
    name = name.strip()
    
    # Remove -T1, -P1, -PS1 suffixes (staging data inconsistencies)
    import re
    name = re.sub(r'-T\d+$', '', name)  # Remove -T1, -T2, etc.
    name = re.sub(r'-P\d+$', '', name)  # Remove -P1, -P2, etc.
    name = re.sub(r'-PS\d+$', '', name)  # Remove -PS1, -PS2, etc.
    name = name.strip()
    
    return name or 'Unknown Subject'

def migrate_course_structures():
    """Migrate course structures from staging data"""
    
    print("Starting Course Structure migration from staging...")
    
    # Get unique subjects from staging
    staging_records = StagingLLBResultCurrent.objects.all().values(
        'subject_name', 
        'semester_code', 
        'paper_code', 
        'status',
        'maximum_mark',
        'pass_mark'
    ).distinct()
    
    total_records = staging_records.count()
    print(f"Total unique subject combinations: {total_records}")
    
    llb_created = 0
    llb_existing = 0
    common_created = 0
    common_existing = 0
    
    # Track created structures to avoid duplicates
    llb_cache = set()
    common_cache = set()
    
    for idx, record in enumerate(staging_records, 1):
        # Clean subject name to remove newlines and extra spaces
        subject_name = clean_subject_name(record['subject_name'])
        semester = record['semester_code'] or ''
        paper_code = record['paper_code'] or 'UNKNOWN'
        status = record['status']
        
        try:
            full_marks = int(record['maximum_mark']) if record['maximum_mark'] else 100
            pass_marks = int(record['pass_mark']) if record['pass_mark'] else 33
        except:
            full_marks = 100
            pass_marks = 33
        
        # Get assessment label (CIA or ESE)
        assessment_label = get_assessment_label(status)
        
        # Generate course_code from paper_code
        course_code = get_course_code(paper_code)
        
        # Use paper_code + semester + status as unique identifier
        llb_key = f"{paper_code}_{semester}_{assessment_label}"
        if llb_key not in llb_cache:
            # Create or get LLBCourseStructure with proper fields
            llb_subject, llb_created_flag = LLBCourseStructure.objects.get_or_create(
                name=subject_name,  # Use actual subject name
                paper_code=paper_code,  # Store paper_code
                course_code=course_code,  # Store generated course_code
                semester=semester,
                status=assessment_label,
                defaults={
                    'full_marks': full_marks,
                    'pass_marks': pass_marks
                }
            )
            
            llb_cache.add(llb_key)
            
            if llb_created_flag:
                llb_created += 1
                print(f"  [{idx}/{total_records}] Created LLBCourseStructure: {subject_name} ({paper_code}) [{course_code}] ({semester}) [{assessment_label}] - {full_marks}/{pass_marks}")
            else:
                llb_existing += 1
        
        # Create or get CommonCourseStructure (only once per paper_code+semester)
        common_key = f"{paper_code}_{semester}"
        if common_key not in common_cache:
            # Calculate CIA and ESE marks (30% CIA, 70% ESE)
            cia_marks = int(full_marks * 0.3)
            ese_marks = int(full_marks * 0.7)
            
            common_subject, common_created_flag = CommonCourseStructure.objects.get_or_create(
                name=subject_name,  # Keep actual subject name
                paper_code=paper_code,  # Store paper_code
                course_code=course_code,  # Store generated course_code
                semester=semester,
                defaults={
                    'full_marks': full_marks,
                    'pass_marks': pass_marks,
                    'cia_max_marks': cia_marks,
                    'ese_max_marks': ese_marks
                }
            )
            
            common_cache.add(common_key)
            
            if common_created_flag:
                common_created += 1
                print(f"  [{idx}/{total_records}] Created CommonCourseStructure: {subject_name} ({paper_code}) [{course_code}] ({semester})")
            else:
                common_existing += 1
        
        # Progress indicator every 10 records
        if idx % 10 == 0:
            print(f"Progress: {idx}/{total_records} processed...")
    
    print("\n" + "="*60)
    print("Course Structure Migration Summary:")
    print("="*60)
    print(f"LLBCourseStructure:")
    print(f"  - Created: {llb_created}")
    print(f"  - Already existed: {llb_existing}")
    print(f"  - Total: {llb_created + llb_existing}")
    print(f"\nCommonCourseStructure:")
    print(f"  - Created: {common_created}")
    print(f"  - Already existed: {common_existing}")
    print(f"  - Total: {common_created + common_existing}")
    print("="*60)

if __name__ == '__main__':
    try:
        migrate_course_structures()
        print("\n✅ Course structure migration completed successfully!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
