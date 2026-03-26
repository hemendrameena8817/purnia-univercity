#!/usr/bin/env python
from difflib import SequenceMatcher
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
MIN_NAME_MATCH_SCORE = 0.84
CANONICAL_ALIASES = {
    'MIL - Hindi': [
        'Hindi Communication',
        'Hindi Communicatin',
        'Hindi sahitya ka itihas',
        'fgUnh lkfgR; dk bfrgkl',
    ],
    'MIL - Urdu': [
        'Urdu Communication',
        'URDU COMMUNICATION',
        'Urdu communication',
        'URDU',
        'STUDY OF URDU GHAZAL',
    ],
    'MIL - Bengali': [
        'Bengla Communication',
    ],
    'MIL - Maithili': [
        'Maithili Communication',
    ],
    'MIL - English Communication': [
        'MIL.ENGLISH',
        'MIL - English',
        'MIL English',
        'English Communication',
        'English communicaton',
    ],
    'Communication in Everyday Life': [
        'Communication in Everyday life',
    ],
    'Swachh Bharat': [
        'Swachh Bharat',
    ],
}
CANONICAL_COURSES = [
    {'course_type': 'AEC', 'course_name': 'MIL - Hindi', 'new_course_code': 'U16002'},
    {'course_type': 'AEC', 'course_name': 'MIL - English Communication', 'new_course_code': 'U16001'},
    {'course_type': 'AEC', 'course_name': 'MIL - Urdu', 'new_course_code': 'U16004'},
    {'course_type': 'AEC', 'course_name': 'MIL - Bengali', 'new_course_code': 'U16005'},
    {'course_type': 'AEC', 'course_name': 'MIL - Maithili', 'new_course_code': 'U16003'},
    {'course_type': 'VAC', 'course_name': 'Swachh Bharat', 'new_course_code': 'U14002'},
    {'course_type': 'VAC', 'course_name': 'Art of Being Happy', 'new_course_code': 'U14001'},
    {'course_type': 'VAC', 'course_name': 'Fit India', 'new_course_code': 'U14003'},
    {'course_type': 'SEC', 'course_name': 'Creative Writing', 'new_course_code': 'U13003'},
    {'course_type': 'SEC', 'course_name': 'Communication in Everyday Life', 'new_course_code': 'U13002'},
    {'course_type': 'SEC', 'course_name': 'Basic IT Tools', 'new_course_code': 'U13005'},
    {'course_type': 'SEC', 'course_name': 'Public Speaking English Language and Leadership', 'new_course_code': 'U13001'},
    {'course_type': 'SEC', 'course_name': 'Digital Marketing', 'new_course_code': 'U13004'},
]



def normalize_text(value):
    return ' '.join(str(value or '').strip().split()).lower()



def normalize_course_name_key(value):
    return ''.join(ch.lower() for ch in str(value or '').strip() if ch.isalnum())



def choose_canonical_course_structure_name(course_names):
    cleaned_names = [str(course_name).strip() for course_name in course_names if str(course_name).strip()]
    if not cleaned_names:
        return None
    return sorted(cleaned_names, key=lambda name: (-len(name), name.lower()))[0]



def build_canonical_course_catalog():
    return {
        normalize_course_name_key(entry['course_name']): {
            'course_type': entry['course_type'],
            'course_name': entry['course_name'],
            'new_course_code': entry['new_course_code'],
        }
        for entry in CANONICAL_COURSES
    }



def build_canonical_alias_catalog(canonical_catalog):
    alias_catalog = {}
    for canonical_name, aliases in CANONICAL_ALIASES.items():
        canonical_entry = canonical_catalog.get(normalize_course_name_key(canonical_name))
        if not canonical_entry:
            continue
        for alias in aliases:
            alias_key = normalize_course_name_key(alias)
            if alias_key:
                alias_catalog[alias_key] = canonical_entry
    return alias_catalog



def resolve_canonical_entry_by_pattern(course_name, canonical_catalog):
    normalized_text = normalize_text(course_name)
    normalized_key = normalize_course_name_key(course_name)

    pattern_checks = [
        ('MIL - Urdu', lambda text, key: 'urdu' in text or 'urdu' in key or 'ghazal' in text or 'ghazal' in key),
        ('MIL - Hindi', lambda text, key: 'hindi' in text or 'sahitya' in text or 'fgunh' in key or 'lkfg' in key or 'bfrgkl' in key),
        ('MIL - Bengali', lambda text, key: 'bengla' in text or 'bangla' in text or 'bengali' in text or 'bengla' in key or 'bangla' in key),
        ('MIL - Maithili', lambda text, key: 'maithili' in text or 'maithili' in key),
        ('MIL - English Communication', lambda text, key: 'english communication' in text or ('english' in text and 'communication' in text)),
        ('Communication in Everyday Life', lambda text, key: 'everyday' in text and 'communication' in text),
        ('Public Speaking English Language and Leadership', lambda text, key: 'public speaking' in text or ('leadership' in text and 'english' in text)),
        ('Creative Writing', lambda text, key: 'creative writing' in text),
        ('Basic IT Tools', lambda text, key: 'basic it' in text or 'it tools' in text),
        ('Digital Marketing', lambda text, key: 'digital marketing' in text),
        ('Swachh Bharat', lambda text, key: 'swachh bharat' in text or ('swachh' in text and 'bharat' in text)),
        ('Art of Being Happy', lambda text, key: 'art of being happy' in text or ('being happy' in text and 'art' in text)),
        ('Fit India', lambda text, key: 'fit india' in text or ('fit' in text and 'india' in text)),
    ]

    matches = [canonical_name for canonical_name, matcher in pattern_checks if matcher(normalized_text, normalized_key)]
    if len(matches) != 1:
        return None
    return canonical_catalog.get(normalize_course_name_key(matches[0]))



def resolve_canonical_entry(course_name, canonical_catalog):
    course_name_key = normalize_course_name_key(course_name)
    if not course_name_key:
        return None, None

    exact_match = canonical_catalog.get(course_name_key)
    if exact_match:
        return exact_match, 'exact'

    pattern_match = resolve_canonical_entry_by_pattern(course_name, canonical_catalog)
    if pattern_match:
        return pattern_match, 'pattern'

    best_entry = None
    best_score = 0.0
    second_best_score = 0.0
    for canonical_key, entry in canonical_catalog.items():
        score = SequenceMatcher(None, course_name_key, canonical_key).ratio()
        if score > best_score:
            second_best_score = best_score
            best_score = score
            best_entry = entry
        elif score > second_best_score:
            second_best_score = score

    if best_entry and best_score >= MIN_NAME_MATCH_SCORE and (best_score - second_best_score) >= 0.03:
        return best_entry, f'fuzzy:{best_score:.3f}'

    return None, None



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
    canonical_catalog = build_canonical_course_catalog()

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
        canonical_entry = canonical_catalog.get(course_name_key)
        if not canonical_entry:
            continue
        mapping_candidates[(normalize_text(canonical_entry['course_type']), course_name_key)].add(row.course_name.strip())

    resolved_mapping = {}
    for key, values in mapping_candidates.items():
        canonical_name = choose_canonical_course_structure_name(values)
        if canonical_name:
            resolved_mapping[key] = canonical_name

    return resolved_mapping



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
    print('Matched rows will also update          new_course_code')
    canonical_catalog = build_canonical_course_catalog()
    canonical_alias_catalog = build_canonical_alias_catalog(canonical_catalog)

    resolved_mapping = build_course_structure_mapping()
    print(f'Unique structure name keys             {len(resolved_mapping):,}')

    queryset = StudentCourseAssessment.objects.filter(
        semester=TARGET_SEMESTER,
        session=TARGET_SESSION,
        course_type__in=['AEC', 'VAC', 'SEC'],
    ).only(
        'id',
        'course_name',
        'course_type',
        'new_course_code',
        'semester',
        'session',
        'label',
    )

    stats = {
        'total': 0,
        'updated': 0,
        'already_correct': 0,
        'missing_course_name': 0,
        'canonical_match_found': 0,
        'alias_match_found': 0,
        'exact_match_found': 0,
        'pattern_match_found': 0,
        'fuzzy_match_found': 0,
        'mapping_not_found': 0,
        'course_type_corrected': 0,
        'new_course_code_corrected': 0,
    }
    updates = []
    unmatched_rows = []

    for row in queryset.iterator(chunk_size=1000):
        stats['total'] += 1
        course_name_key = normalize_course_name_key(row.course_name)

        if not course_name_key:
            stats['missing_course_name'] += 1
            unmatched_rows.append(
                f'id={row.id} | reason=missing_course_name | course_type={row.course_type or "-"} | label={row.label or "-"}'
            )
            continue

        canonical_entry = canonical_alias_catalog.get(course_name_key)
        match_mode = 'alias' if canonical_entry else None
        if not canonical_entry:
            canonical_entry, match_mode = resolve_canonical_entry(row.course_name, canonical_catalog)
        if not canonical_entry:
            stats['mapping_not_found'] += 1
            unmatched_rows.append(
                f'id={row.id} | reason=mapping_not_found | course_type={row.course_type or "-"} | label={row.label or "-"} | current_course_name={row.course_name or "-"}'
            )
            continue

        stats['canonical_match_found'] += 1
        if match_mode == 'alias':
            stats['alias_match_found'] += 1
        elif match_mode == 'exact':
            stats['exact_match_found'] += 1
        elif match_mode == 'pattern':
            stats['pattern_match_found'] += 1
        else:
            stats['fuzzy_match_found'] += 1
        target_course_type = canonical_entry['course_type']
        target_new_course_code = canonical_entry['new_course_code']
        canonical_course_name_key = normalize_course_name_key(canonical_entry['course_name'])
        target_course_name = resolved_mapping.get(
            (normalize_text(target_course_type), canonical_course_name_key),
            canonical_entry['course_name'],
        )

        changed = False
        if (row.course_name or '').strip() != target_course_name:
            row.course_name = target_course_name
            changed = True

        if (row.course_type or '').strip() != target_course_type:
            row.course_type = target_course_type
            stats['course_type_corrected'] += 1
            changed = True

        if (row.new_course_code or '').strip() != target_new_course_code:
            row.new_course_code = target_new_course_code
            stats['new_course_code_corrected'] += 1
            changed = True

        if not changed:
            stats['already_correct'] += 1
            continue

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

    if dry_run:
        print('\nDRY RUN: no changes saved')
        print(f'ROWS THAT WOULD BE UPDATED             {len(updates):,}')
        return

    if not updates:
        print('\nNo updates needed')
        print('ROWS UPDATED                           0')
        return

    with transaction.atomic():
        StudentCourseAssessment.objects.bulk_update(updates, ['course_name', 'course_type', 'new_course_code'], batch_size=500)

    print(f'\nUpdated {len(updates):,} StudentCourseAssessment rows')
    print(f'ROWS UPDATED                           {len(updates):,}')



def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix AEC/VAC/SEC StudentCourseAssessment course_name, course_type, and new_course_code using the canonical course catalog and exact CourseStructure names.'
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')
    args = parser.parse_args()

    run(dry_run=args.dry_run)



if __name__ == '__main__':
    main()
