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
TARGET_COURSE_TYPES = {'mjc', 'mic', 'mdc'}



def normalize_text(value):
    return ' '.join(str(value or '').strip().split()).lower()



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
    ).select_related('department').only(
        'id',
        'course_name',
        'course_type',
        'department__name',
        'department_id',
        'semester',
        'label',
    )

    for row in queryset.iterator(chunk_size=500):
        key = (normalize_text(row.course_type), row.department_id)
        if not key[0] or key[0] not in TARGET_COURSE_TYPES or row.department_id is None:
            continue
        mapping_candidates[key].add((row.course_name.strip(), row.id, row.label or ''))

    resolved_mapping = {}
    ambiguous_mapping = {}

    for key, values in mapping_candidates.items():
        unique_names = {course_name for course_name, _, _ in values if course_name}
        if len(unique_names) == 1:
            resolved_mapping[key] = next(iter(unique_names))
        elif len(unique_names) > 1:
            ambiguous_mapping[key] = sorted(unique_names)

    return resolved_mapping, ambiguous_mapping



def print_ambiguous_mapping(ambiguous_mapping):
    if not ambiguous_mapping:
        return

    print('\n' + '=' * 100)
    print('AMBIGUOUS COURSE STRUCTURE KEYS')
    print('=' * 100)
    for (course_type_key, department_id), names in sorted(ambiguous_mapping.items()):
        print(
            f'course_type={course_type_key or "-"} | department_id={department_id or "-"} | course_names={", ".join(names)}'
        )



def resolve_ambiguous_candidate_names(current_course_name, candidate_names):
    current_name_key = normalize_text(current_course_name)
    if not current_name_key:
        return None

    matches = [candidate_name for candidate_name in candidate_names if normalize_text(candidate_name) == current_name_key]
    if len(matches) == 1:
        return matches[0]
    return None



def run(dry_run=False):
    print('\n' + '=' * 100)
    print('UPDATE STUDENT ASSESSMENT COURSE NAMES FROM COURSE STRUCTURE')
    print('=' * 100)
    if dry_run:
        print('MODE: DRY RUN')
    else:
        print('MODE: LIVE UPDATE')
    print(f'Semester                               {TARGET_SEMESTER}')
    print(f'Session                                {TARGET_SESSION}')
    print(f'CourseStructure semester values        {", ".join(get_course_structure_semester_values(TARGET_SEMESTER))}')

    resolved_mapping, ambiguous_mapping = build_course_structure_mapping()
    print(f'Unique course structure keys           {len(resolved_mapping):,}')
    print(f'Ambiguous course structure keys        {len(ambiguous_mapping):,}')
    print_ambiguous_mapping(ambiguous_mapping)

    queryset = StudentCourseAssessment.objects.filter(
        semester=TARGET_SEMESTER,
        session=TARGET_SESSION,
        course_type__in=['MJC', 'MIC', 'MDC'],
    ).select_related('department').only(
        'id',
        'course_name',
        'course_type',
        'department__name',
        'department_id',
        'semester',
        'session',
        'label',
    )

    stats = {
        'total': 0,
        'updated': 0,
        'already_correct': 0,
        'missing_course_type': 0,
        'missing_department': 0,
        'mapping_not_found': 0,
        'ambiguous_mapping': 0,
        'resolved_from_current_name': 0,
        'skipped_non_target_course_type': 0,
    }
    updates = []
    missing_rows = []
    ambiguous_rows = []

    for row in queryset.iterator(chunk_size=1000):
        stats['total'] += 1

        course_type_key = normalize_text(row.course_type)
        if not course_type_key:
            stats['missing_course_type'] += 1
            missing_rows.append(
                f'id={row.id} | reason=missing_course_type | department={getattr(row.department, "name", "-") or "-"} | label={row.label or "-"} | current_course_name={row.course_name or "-"}'
            )
            continue

        if course_type_key not in TARGET_COURSE_TYPES:
            stats['skipped_non_target_course_type'] += 1
            continue

        if row.department_id is None:
            stats['missing_department'] += 1
            missing_rows.append(
                f'id={row.id} | reason=missing_department | course_type={row.course_type or "-"} | label={row.label or "-"} | current_course_name={row.course_name or "-"}'
            )
            continue

        key = (course_type_key, row.department_id)
        if key in ambiguous_mapping:
            target_course_name = resolve_ambiguous_candidate_names(row.course_name, ambiguous_mapping[key])
            if target_course_name:
                stats['resolved_from_current_name'] += 1
                if (row.course_name or '').strip() == target_course_name:
                    stats['already_correct'] += 1
                    continue

                row.course_name = target_course_name
                updates.append(row)
                stats['updated'] += 1
                continue

            stats['ambiguous_mapping'] += 1
            ambiguous_rows.append(
                f'id={row.id} | course_type={row.course_type or "-"} | department={getattr(row.department, "name", "-") or "-"} | label={row.label or "-"} | current_course_name={row.course_name or "-"} | candidate_names={", ".join(ambiguous_mapping[key])}'
            )
            continue

        target_course_name = resolved_mapping.get(key)
        if not target_course_name:
            stats['mapping_not_found'] += 1
            missing_rows.append(
                f'id={row.id} | reason=mapping_not_found | course_type={row.course_type or "-"} | department={getattr(row.department, "name", "-") or "-"} | label={row.label or "-"} | current_course_name={row.course_name or "-"}'
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

    if missing_rows:
        print('\n' + '=' * 100)
        print('MISSING OR UNMATCHED ROWS')
        print('=' * 100)
        for row in missing_rows[:300]:
            print(row)
        if len(missing_rows) > 300:
            print(f'... truncated {len(missing_rows) - 300:,} more rows')

    if ambiguous_rows:
        print('\n' + '=' * 100)
        print('ASSESSMENT ROWS SKIPPED DUE TO AMBIGUOUS COURSE STRUCTURE MATCH')
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
        description='Update StudentCourseAssessment.course_name from CourseStructure using department and course_type for MJC/MIC/MDC rows in 1ST sem, 2025-26 session.'
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')
    args = parser.parse_args()

    run(dry_run=args.dry_run)



if __name__ == '__main__':
    main()
