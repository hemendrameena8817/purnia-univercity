#!/usr/bin/env python
"""
Script to Map Department by Subject Name for UG Students - OPTIMIZED FOR BULK DATA

This script:
1. Processes StudentCourseAssessment records in batches
2. Matches paper_code last 4 digits with MIC (1002) or MDC (1005)
3. Matches course name to find department
4. Uses bulk_update for efficient database operations

Optimizations:
- Batch processing (10,000 assessments at a time)
- Bulk updates (1,000 profiles at a time)
- Cached department lookups
- Minimal database queries

Usage:
    python scripts/ug/map_depratment_by_subject_name.py
"""

import os
import sys
import django
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db.models import Q
from ug.models import UGStudentProfile, StudentCourseAssessment, UGDepartment

# MDC Departments and Courses (paper_code ends with 1005)
mdc_departments_and_courses = [
    {"department":"MUSIC","department_code":"MUS", "course":"Fundamentals of Indian Music"},
    {"department":"ENGLISH","department_code":"ENG", "course":"Indian Classical Literaure"}, 
    {"department":"PHILOSOPHY","department_code":"PHI", "course":"Deductive Logic"}, 
    {"department":"MAITHILI","department_code":"ML", "course":"Maithili Sahityik Aadikaal Evan Madhyakaal"}, 
    {"department":"HINDI","department_code":"HIN", "course":"हिंदी साहित्य का इतिहास"}, 
    {"department":"PSYCHOLOGY","department_code":"PSY", "course":"Introduction to General Psychology"}, 
    {"department":"HISTORY","department_code":"HIST", "course":"The Idea of Bharat"}, 
    {"department":"HOME SCIENCE","department_code":"HSC", "course":"NGO Management"},
    {"department":"POLITICAL SCIENCE","department_code":"POL", "course":"Understanding Political Theory"}, 
    {"department":"GEOGRAPHY","department_code":"GEOG", "course":"Geomorphology"}, 
    {"department":"ECONOMICS","department_code":"ECO", "course":"Introductory Microeconomics"}, 
    {"department":"SOCIOLOGY","department_code":"SOC", "course":"Introduction to Sociology - I"}, 
    {"department":"COMMERCE(Marketing)","department_code":"Marketing", "course":"Principles & Functions of Marketing"}, 
    {"department":"COMMERCE(HRM)","department_code":"HRM", "course":"Fundamentals of HRM"}, 
    {"department":"PERSIAN","department_code":"PER", "course":"Introduction Elementary Persian Language"}, 
    {"department":"CHEMISTRY","department_code":"CHEM", "course":"Inorganic and Organic Chemistry"}, 
    {"department":"ZOOLOGY","department_code":"ZOO", "course":"Diversity of Non-Chordates"}, 
    {"department":"BOTANY","department_code":"BOT", "course":"Phycology and Microbiology"}, 
    {"department":"PHYSICS","department_code":"PHY", "course":"Physics around us"}, 
    {"department":"MATH","department_code":"MATH", "course":"Algebra"}, 
    {"department":"BENGALI","department_code":"BEN", "course":"Bangla Sahityer ltihas-Prachin-o-Madhya Jug"}, 
    {"department":"HINDI","department_code":"HIN", "course":"History of Hindi Literature"}, 
    {"department":"ENGLISH","department_code":"ENG", "course":"Indian Classical Literature"}, 
    {"department":"URDU","department_code":"URD", "course":"Study of Urdu Fiction"}, 
    {"department":"SANSKRIT","department_code":"SNK", "course":"Sanskrit Vyakaran"}, 
    {"department":"Urdu","department_code":"URD", "course":"MIL - Urdu"},
    {"department":"COMMERCE(HRM)", "department_code":"HRM", "course":"Fandamentals of HRM"},
]

# MIC Departments and Courses (paper_code ends with 1002)
mic_departments_and_courses = [
    {"department":"HOME SCIENCE", "department_code":"HSC", "course":"Food and Nutrition"},
    {"department":"GEOGRAPHY", "department_code":"GEOG", "course":"Geomorphology"},
    {"department":"HISTORY", "department_code":"HIST", "course":"The Idea of Bharat"},
    {"department":"POLITICAL SCIENCE", "department_code":"POL", "course":"Understanding Political Theory"},
    {"department":"PSYCHOLOGY","department_code":"PSY", "course":"Introduction to General Psychology"},
    {"department":"ECONOMICS", "department_code":"ECO", "course":"Introductory Microeconomics"},
    {"department":"SOCIOLOGY", "department_code":"SOC", "course":"Introduction to Sociology - I"},
    {"department":"HINDI", "department_code":"HIN", "course":"History of Hindi Literature: From Aadikaal to Reetikaal"},
    {"department":"ENGLISH", "department_code":"ENG", "course":"Indian Classical Literature"},
    {"department":"PHILOSOPHY", "department_code":"PHI", "course":"Deductive Logic"},
    {"department":"MAITHILI", "department_code":"ML", "course":"Maithili Sahityik Aadikaal  Evan Madhyakaal"},
    {"department":"URDU", "department_code":"URD", "course":"Study of Urdu Fiction"},
    {"department":"MUSIC", "department_code":"MUS", "course":"Fundamentals of Indian Music"},
    {"department":"ANCIENT INDIAN HISTORY","department_code":"AIH", "course":"Political History of India (From Indus Valley Civilization to 319 A.D)"},
    {"department":"MATH", "department_code":"MATH", "course":"Algebra"},
    {"department":"SANSKRIT", "department_code":"SNK", "course":"Sanskrit Vyakaran"},
    {"department":"LABOUR AND SOCIAL WELFARE", "department_code":"LSW", "course":"Industrial Relations"},
    {"department":"PERSIAN", "department_code":"PER", "course":"Applied Persian Grammar & Translation"},
    {"department":"BENGLA", "department_code":"BEN", "course":"BUILDING SCIENCE"},
    {"department":"GANDHIAN THOUGHT", "department_code":"GTV", "course":"Gandhi`s Life Journey (From Birth to 1914)"},
    {"department":"ANTHROPOLOGY","department_code":"ANTH", "course":"An Introduction to Genral Anthropology"},
    {"department":"RURAL ECONOMICS", "department_code":"RECO", "course":"Foundation of Agriculture Farm"},
    {"department":"ANCIENT INDIAN HISTORY", "department_code":"AIH", "course":"Political History of India (From Indus Valley Civilization to 319 A.D 1206 A.D.)"},
    {"department":"ZOOLOGY", "department_code":"ZOO", "course":"Diversity of Non-Chordates"},
    {"department":"CHEMISTRY", "department_code":"CHEM", "course":"Inorganic and Organic Chemistry"},
    {"department":"PHYSICS", "department_code":"PHY", "course":"Introduction to Mathematical Physics & Classical Mechaincs"},
    {"department":"BOTANY","department_code":"BOT", "course":"Phycology and Microbiology"},
    {"department":"STATITICS", "department_code":"STAT", "course":"Descriptive Statistics"},
    {"department":"COMMERCE(Marketing)", "department_code":"Marketing", "course":"Principles & Functions of Marketing"},
    {"department":"COMMERCE(HRM)", "department_code":"HRM", "course":"Fandamentals of HRM"},
    {"department":"HINDI", "department_code":"HIN", "course":"History of Hindi Literature"},
    {"department":"PERSIAN", "department_code":"PER", "course":"Applied Persian Grammar & Translation"},
    {"department":"PERSIAN", "department_code":"PER", "course":"Introduction Elementary Persian Language"}
]


def create_course_to_dept_map(courses_list):
    """Create a mapping of course name -> department_code"""
    mapping = {}
    for item in courses_list:
        mapping[item['course'].strip()] = item['department_code'].strip()
    return mapping


def get_department_cache():
    """
    Load all published departments into memory for fast lookup
    Returns: {dept_code: UGDepartment instance}
    """
    print("  → Loading departments into cache...")
    departments = UGDepartment.objects.filter(is_publish=True)
    cache = {}
    for dept in departments:
        cache[dept.code.upper()] = dept
    print(f"  ✓ Loaded {len(cache)} published departments")
    return cache


def process_assessments_optimized(batch="2024-28", semester="1ST", batch_size=10000, update_batch_size=1000):
    """
    Process assessments in batches and bulk update profiles
    """
    print("=" * 80)
    print("OPTIMIZED DEPARTMENT MAPPING SCRIPT")
    print("=" * 80)
    print(f"Batch:              {batch}")
    print(f"Semester:           {semester}")
    print(f"Assessment Batch:   {batch_size}")
    print(f"Update Batch:       {update_batch_size}")
    print("-" * 80)
    
    # Create mappings
    mic_map = create_course_to_dept_map(mic_departments_and_courses)
    mdc_map = create_course_to_dept_map(mdc_departments_and_courses)
    
    print(f"MDC Courses: {len(mdc_map)}")
    print(f"MIC Courses: {len(mic_map)}")
    
    # Load department cache
    dept_cache = get_department_cache()
    
    print("-" * 80)
    
    # Count total assessments
    total_count = StudentCourseAssessment.objects.filter(
        Q(paper_code__endswith="1002") | Q(paper_code__endswith="1005"),
        batch__name=batch,
        semester=semester
    ).count()
    
    print(f"\nTotal assessments: {total_count:,}")
    print(f"Processing in batches of {batch_size:,}...\n")
    
    # Statistics
    stats = {
        'assessments_processed': 0,
        'mic_matched': 0,
        'mdc_matched': 0,
        'profiles_updated_mic': 0,
        'profiles_updated_mdc': 0,
        'dept_not_found': 0,
        'course_not_matched': 0,
    }
    
    # Track which student profiles need updating
    # Structure: {student_id: {'mic': dept_obj, 'mdc': dept_obj}}
    profile_updates = defaultdict(dict)
    
    # Track unmatched items
    unmatched_courses = set()
    missing_departments = set()
    
    # Process in batches
    offset = 0
    while offset < total_count:
        print(f"Processing assessments {offset:,} to {min(offset + batch_size, total_count):,}...")
        
        # Get batch of assessments
        assessments = StudentCourseAssessment.objects.filter(
            batch__name=batch,
            semester=semester
        ).select_related('student')[offset:offset + batch_size]
        
        for assessment in assessments:
            stats['assessments_processed'] += 1
            
            if not assessment.paper_code or not assessment.course_name or not assessment.student:
                continue
            
            paper_suffix = assessment.paper_code[-4:]
            course_name = assessment.course_name.strip()
            
            dept_code = None
            course_type = None
            
            # Check MIC (1002)
            if paper_suffix == "1002":
                if course_name in mic_map:
                    dept_code = mic_map[course_name]
                    course_type = 'mic'
                    stats['mic_matched'] += 1
                else:
                    unmatched_courses.add(f"{course_name} (MIC 1002)")
                    stats['course_not_matched'] += 1
                    continue
            
            # Check MDC (1005)
            elif paper_suffix == "1005":
                if course_name in mdc_map:
                    dept_code = mdc_map[course_name]
                    course_type = 'mdc'
                    stats['mdc_matched'] += 1
                else:
                    unmatched_courses.add(f"{course_name} (MDC 1005)")
                    stats['course_not_matched'] += 1
                    continue
            
            else:
                # Not a relevant paper code
                continue
            
            # Lookup department in cache
            if dept_code:
                ug_dept = dept_cache.get(dept_code.upper())
                
                if ug_dept:
                    # Store for bulk update later
                    student_id = assessment.student.id
                    profile_updates[student_id][course_type] = ug_dept
                else:
                    missing_departments.add(dept_code)
                    stats['dept_not_found'] += 1
        
        offset += batch_size
        
        # Perform bulk update every update_batch_size profiles
        if len(profile_updates) >= update_batch_size:
            _bulk_update_profiles(profile_updates, stats)
            profile_updates.clear()
    
    # Update remaining profiles
    if profile_updates:
        _bulk_update_profiles(profile_updates, stats)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Assessments processed:    {stats['assessments_processed']:,}")
    print(f"MIC courses matched:      {stats['mic_matched']:,}")
    print(f"MDC courses matched:      {stats['mdc_matched']:,}")
    print(f"MIC profiles updated:     {stats['profiles_updated_mic']:,}")
    print(f"MDC profiles updated:     {stats['profiles_updated_mdc']:,}")
    print(f"Dept not found:           {stats['dept_not_found']:,}")
    print(f"Course not matched:       {stats['course_not_matched']:,}")
    
    if missing_departments:
        print("\n" + "-" * 80)
        print(f"MISSING DEPARTMENTS ({len(missing_departments)}):")
        print("-" * 80)
        for dept in sorted(missing_departments):
            print(f"- {dept}")

    if unmatched_courses:
        print("\n" + "-" * 80)
        print(f"UNMATCHED COURSES ({len(unmatched_courses)}):")
        print("-" * 80)
        for course in sorted(unmatched_courses):
            print(f"- {course}")
            
    print("-" * 80)
    print("\n✓ Processing completed successfully!")


def _bulk_update_profiles(profile_updates, stats):
    """
    Bulk update student profiles
    """
    if not profile_updates:
        return
    
    print(f"  → Bulk updating {len(profile_updates):,} profiles...")
    
    # Fetch all profiles
    student_ids = list(profile_updates.keys())
    profiles = UGStudentProfile.objects.filter(id__in=student_ids)
    
    # Prepare updates
    minor_course = []
    mdc_course = []
    
    for profile in profiles:
        updates = profile_updates.get(profile.id, {})
        
        if 'mic' in updates and profile.minor_course != updates['mic']:
            profile.minor_course = updates['mic']
            minor_course.append(profile)
            stats['profiles_updated_mic'] += 1
        
        if 'mdc' in updates and profile.mdc_course != updates['mdc']:
            profile.mdc_course = updates['mdc']
            mdc_course.append(profile)
            stats['profiles_updated_mdc'] += 1
    
    # Bulk update
    if minor_course:
        UGStudentProfile.objects.bulk_update(minor_course, ['minor_course'], batch_size=500)
        print(f"    ✓ Updated {len(minor_course):,} MIC courses")
    
    if mdc_course:
        UGStudentProfile.objects.bulk_update(mdc_course, ['mdc_course'], batch_size=500)
        print(f"    ✓ Updated {len(mdc_course):,} MDC courses")


def main():
    """
    Run the department mapping script
    """
    print("\n" + "=" * 80)
    print("Starting Optimized Department Mapping Script")
    print("Batch: 2024-28, Semester: 1ST")
    print("=" * 80 + "\n")
    
    # Configuration
    batch = "2024-28"
    semester = "1ST"
    assessment_batch_size = 10000   # Process assessments in chunks of 10k
    update_batch_size = 1000         # Bulk update profiles every 1k
    
    process_assessments_optimized(
        batch=batch,
        semester=semester,
        batch_size=assessment_batch_size,
        update_batch_size=update_batch_size
    )


if __name__ == '__main__':
    main()