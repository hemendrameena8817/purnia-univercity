"""
Bulk update StudentCourseAssessment records with correct course_type and code
by matching with CourseStructure based on course name.

This script:
1. Loads all CourseStructure records into memory for fast lookup
2. Matches StudentCourseAssessment by course name
3. Bulk updates in batches for speed
4. Reports progress and statistics
"""

import os
import sys
import django
import time
from datetime import datetime

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pupumis.settings')
django.setup()

from django.db import transaction
from ug.models import CourseStructure, StudentCourseAssessment


def normalize_name(name):
    """
    Normalize course name for better matching.
    Removes common suffixes like (T), (P), (Theory), (Practical), etc.
    """
    if not name:
        return ''
    
    # Convert to lowercase and strip whitespace
    normalized = str(name).lower().strip()
    
    # Remove common suffixes in parentheses
    # e.g., "Economics (T)" -> "economics"
    import re
    # Match patterns like (T), (P), (Theory), (Practical), etc.
    normalized = re.sub(r'\s*\([^)]*\)\s*$', '', normalized)
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized


def build_course_lookup():
    """Build a dictionary mapping (normalized_name) -> CourseStructure"""
    print('📦 Building course structure lookup...')
    
    course_lookup = {}
    
    for course in CourseStructure.objects.all():
        key = normalize_name(course.name)
        if key:
            # Store the course with its code and type
            if key not in course_lookup:
                course_lookup[key] = []
            course_lookup[key].append({
                'code': course.code,
                'course_type': course.course_type,
                'id': course.id
            })
    
    print(f'   Loaded {len(course_lookup):,} unique course names')
    print(f'   Total CourseStructure records: {CourseStructure.objects.count():,}')
    return course_lookup


def update_assessments(batch_size=5000, limit=None):
    """Update StudentCourseAssessment records with correct course_type and code"""
    
    start_time = time.time()
    
    print('\n' + '='*80)
    print('Bulk Updating StudentCourseAssessment Course Types and Codes')
    print('='*80 + '\n')
    
    # Build lookup table
    course_lookup = build_course_lookup()
    
    # Get total count
    queryset = StudentCourseAssessment.objects.all()
    if limit:
        queryset = queryset[:limit]
        total_count = limit
    else:
        total_count = StudentCourseAssessment.objects.count()
    
    print(f'\n📊 Total assessments to process: {total_count:,}')
    print(f'📦 Batch size: {batch_size:,}\n')
    print('🚀 Starting update...\n')
    
    # Statistics
    stats = {
        'processed': 0,
        'matched': 0,
        'updated': 0,
        'not_matched': 0,
        'multiple_matches': 0
    }
    
    # Process in batches
    offset = 0
    
    while offset < total_count:
        # Fetch batch
        batch = list(queryset[offset:offset + batch_size])
        
        if not batch:
            break
        
        updates = []
        
        # Match each record
        for assessment in batch:
            stats['processed'] += 1
            
            # Look up by normalized name
            key = normalize_name(assessment.name)
            matches = course_lookup.get(key, [])
            
            if not matches:
                stats['not_matched'] += 1
                continue
            
            stats['matched'] += 1
            
            if len(matches) > 1:
                stats['multiple_matches'] += 1
            
            # Use the first match
            match = matches[0]
            
            # Update if different
            if assessment.course_type != match['course_type'] or assessment.code != match['code']:
                assessment.course_type = match['course_type']
                assessment.code = match['code']
                updates.append(assessment)
                stats['updated'] += 1
        
        # Bulk update this batch
        if updates:
            with transaction.atomic():
                StudentCourseAssessment.objects.bulk_update(updates, ['course_type', 'code'], batch_size=batch_size)
        
        # Progress update
        if stats['processed'] % 10000 == 0 and stats['processed'] > 0:
            elapsed = time.time() - start_time
            rate = stats['processed'] / elapsed if elapsed > 0 else 0
            print(f'   Processed {stats["processed"]:,} | Matched: {stats["matched"]:,} | Updated: {stats["updated"]:,} | Rate: {rate:.0f} rec/sec')
        
        offset += batch_size
    
    # Final stats
    elapsed_time = time.time() - start_time
    
    print('\n' + '='*80)
    print('Update Complete')
    print('='*80)
    print(f'✅ Records processed: {stats["processed"]:,}')
    print(f'✅ Records matched: {stats["matched"]:,} ({stats["matched"]/stats["processed"]*100:.1f}%)')
    print(f'✅ Records updated: {stats["updated"]:,}')
    print(f'⚠️  Not matched: {stats["not_matched"]:,}')
    print(f'⚠️  Multiple matches: {stats["multiple_matches"]:,}')
    print(f'⏱️  Time: {elapsed_time:.1f} seconds ({stats["processed"]/elapsed_time:.0f} rec/sec)')
    print()
    
    # Show course_type distribution after update
    print('📊 Course type distribution after update:')
    from django.db.models import Count
    types = StudentCourseAssessment.objects.values('course_type').annotate(count=Count('id')).order_by('-count')
    for t in types[:10]:
        print(f'   {t["course_type"] or "None":10s}: {t["count"]:,}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Update StudentCourseAssessment with course types and codes from CourseStructure')
    parser.add_argument('--limit', type=int, help='Limit number of records to process (for testing)')
    parser.add_argument('--batch-size', type=int, default=5000, help='Batch size for bulk updates')
    
    args = parser.parse_args()
    
    update_assessments(batch_size=args.batch_size, limit=args.limit)
