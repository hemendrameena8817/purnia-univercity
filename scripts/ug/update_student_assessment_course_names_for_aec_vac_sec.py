#!/usr/bin/env python
import os
import sys
from collections import defaultdict
from pathlib import Path

import django
from django.db import transaction

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug.models import CourseStructure, StudentCourseAssessment

TARGET_SEMESTER = '1ST'
TARGET_SESSION = '2025-26'
TARGET_COURSE_TYPES = {'aec', 'vac', 'sec'}



def normalize_text(value):
    return ' '.join(str(value or '').strip().split()).lower()



def normalize_course_name_key(value):
    return ''.join(ch.lower() for ch in str(value or '').strip() if ch.isalnum())



def choose_canonical_course_structure_name(course_names):
    cleaned_names = [str(course_name).strip() for course_name in course_names if str(course_name).strip()]
    if not cleaned_names:
        return None
    return sorted(cleaned_names, key=lambda name: (-len(name), name.lower()))[0]



def get_course_structure_semester_values(semester):
    semester_text = str(semester or '').strip()
    digits = ''.join(ch for ch in semester_text if ch.isdigit())
    values = {semester_text}
    if digits:
        values.add(digits)
    return [value for value in values if value]



def build_course_structure_mapping():
    mapping_candidates = defaultdict(set)
    semester_values = get_course_structure_semester_values(TARGET_SEMESTER)

    queryset = CourseStructure.objects.filter(
        semester__in=semester_values,
    ).exclude(
        course_name__isnull=True,
    ).exclude(
        course_name='',
    ).only(
        'id',
        'course_name',
        'course_type',
        'semester',
        'label',
    )

    for row in queryset.iterator(chunk_size=500):
        course_type_key = normalize_text(row.course_type)
        course_name_key = normalize_course_name_key(row.course_name)
        if not course_type_key or course_type_key not in TARGET_COURSE_TYPES or not course_name_key:
            continue
        mapping_candidates[(course_type_key, course_name_key)].add(row.course_name.strip())

    resolved_mapping = {}
    ambiguous_mapping = {}
    for key, values in mapping_candidates.items():
        canonical_name = choose_canonical_course_structure_name(values)
        if canonical_name:
            resolved_mapping[key] = canonical_name
        else:
            ambiguous_mapping[key] = sorted(values)

    return resolved_mapping, ambiguous_mapping



def run(dry_run=False):
    print('\n' + '=' * 100)
    print('UPDATE AEC VAC SEC ASSESSMENT COURSE NAMES FROM COURSE STRUCTURE')
    print('=' * 100)
    if dry_run:
        print('MODE: DRY RUN')
    else:
        print('MODE: LIVE UPDATE')
    print(f'Semester                               {TARGET_SEMESTER}')
    print(f'Session                                {TARGET_SESSION}')
    print(f'Course types                           {", ".join(sorted(course_type.upper() for course_type in TARGET_COURSE_TYPES))}')
    print(f'CourseStructure semester values        {", ".join(get_course_structure_semester_values(TARGET_SEMESTER))}')

    resolved_mapping, ambiguous_mapping = build_course_structure_mapping()
    print(f'Unique structure name keys             {len(resolved_mapping):,}')
    print(f'Ambiguous structure name keys          {len(ambiguous_mapping):,}')

    queryset = StudentCourseAssessment.objects.filter(
        semester=TARGET_SEMESTER,
        session=TARGET_SESSION,
        course_type__in=['AEC', 'VAC', 'SEC'],
    ).only(
        'id',
        'course_name',
        'course_type',
        'semester',
        'session',
        'label',
    )

    stats = {
        'total': 0,
        'updated': 0,
        'already_correct': 0,
        'missing_course_name': 0,
        'mapping_not_found': 0,
        'ambiguous_mapping': 0,
    }
    updates = []
    unmatched_rows = []
    ambiguous_rows = []

    for row in queryset.iterator(chunk_size=1000):
        stats['total'] += 1
        course_type_key = normalize_text(row.course_type)
        course_name_key = normalize_course_name_key(row.course_name)

        if not course_name_key:
            stats['missing_course_name'] += 1
            unmatched_rows.append(
                f'id={row.id} | reason=missing_course_name | course_type={row.course_type or "-"} | label={row.label or "-"}'
            )
            continue

        key = (course_type_key, course_name_key)
        if key in ambiguous_mapping:
            stats['ambiguous_mapping'] += 1
            ambiguous_rows.append(
                f'id={row.id} | course_type={row.course_type or "-"} | label={row.label or "-"} | current_course_name={row.course_name or "-"} | candidate_names={", ".join(ambiguous_mapping[key])}'
            )
            continue

        target_course_name = resolved_mapping.get(key)
        if not target_course_name:
            stats['mapping_not_found'] += 1
            unmatched_rows.append(
                f'id={row.id} | reason=mapping_not_found | course_type={row.course_type or "-"} | label={row.label or "-"} | current_course_name={row.course_name or "-"}'
            )
            continue

        if (row.course_name or '').strip() == target_course_name:
            stats['already_correct'] += 1
            continue

        row.course_name = target_course_name
        updates.append(row)
        stats['updated'] += 1

    print('\n' + '=' * 100)
    print('SUMMARY')
    print('=' * 100)
    for key, value in stats.items():
        print(f'{key:<38} {value:,}')

    if unmatched_rows:
        print('\n' + '=' * 100)
        print('UNMATCHED ROWS')
        print('=' * 100)
        for row in unmatched_rows[:300]:
            print(row)
        if len(unmatched_rows) > 300:
            print(f'... truncated {len(unmatched_rows) - 300:,} more rows')

    if ambiguous_rows:
        print('\n' + '=' * 100)
        print('AMBIGUOUS ROWS')
        print('=' * 100)
        for row in ambiguous_rows[:300]:
            print(row)
        if len(ambiguous_rows) > 300:
            print(f'... truncated {len(ambiguous_rows) - 300:,} more rows')

    if dry_run:
        print('\nDRY RUN: no changes saved')
        print(f'ROWS THAT WOULD BE UPDATED             {len(updates):,}')
        return

    if not updates:
        print('\nNo updates needed')
        print('ROWS UPDATED                           0')
        return

    with transaction.atomic():
        StudentCourseAssessment.objects.bulk_update(updates, ['course_name'], batch_size=500)

    print(f'\nUpdated {len(updates):,} StudentCourseAssessment rows')
    print(f'ROWS UPDATED                           {len(updates):,}')



def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Update AEC/VAC/SEC StudentCourseAssessment.course_name from CourseStructure when normalized course_name matches within the same course_type.'
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')
    args = parser.parse_args()

    run(dry_run=args.dry_run)



if __name__ == '__main__':
    main()
