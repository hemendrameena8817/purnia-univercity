#!/usr/bin/env python
import argparse
import os
import sys

import django
from django.db import transaction

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug.models import ExamRegistration, StudentCourseAssessment


SEMESTER_TEXT_MAP = {
    1: '1ST',
    2: '2ND',
    3: '3RD',
    4: '4TH',
    5: '5TH',
    6: '6TH',
    7: '7TH',
    8: '8TH',
}


def get_semester_variants(sem_value):
    variants = set()
    if sem_value is None:
        return variants

    sem_text = str(sem_value).strip()
    if not sem_text:
        return variants

    variants.add(sem_text)

    if sem_text.isdigit():
        sem_int = int(sem_text)
        mapped_text = SEMESTER_TEXT_MAP.get(sem_int)
        if mapped_text:
            variants.add(mapped_text)
    else:
        normalized = sem_text.upper()
        variants.add(normalized)
        reverse_map = {value: key for key, value in SEMESTER_TEXT_MAP.items()}
        if normalized in reverse_map:
            variants.add(str(reverse_map[normalized]))

    return variants


def map_exam_registration_assessments(session=None, sem=None, exam_type=None, only_empty=False, batch_size=500, dry_run=False):
    queryset = ExamRegistration.objects.select_related('student').prefetch_related('assessment').all().order_by('id')

    if session:
        queryset = queryset.filter(session=session)
    if sem is not None:
        queryset = queryset.filter(sem=sem)
    if exam_type:
        queryset = queryset.filter(exam_type=exam_type)
    if only_empty:
        queryset = queryset.filter(assessment__isnull=True).distinct()

    total = queryset.count()

    stats = {
        'processed': 0,
        'updated': 0,
        'skipped_no_session': 0,
        'skipped_no_sem': 0,
        'skipped_no_matches': 0,
        'unchanged': 0,
        'linked_assessments': 0,
    }

    print('=' * 100)
    print('MAP EXAM REGISTRATION ASSESSMENTS')
    print('=' * 100)
    print(f'Total registrations to process: {total:,}')
    if session:
        print(f'Session filter: {session}')
    if sem is not None:
        print(f'Sem filter: {sem}')
    if exam_type:
        print(f'Exam type filter: {exam_type}')
    if only_empty:
        print('Only empty registrations: yes')
    print(f'Mode: {"DRY RUN" if dry_run else "LIVE"}')
    print('-' * 100)

    for index, registration in enumerate(queryset.iterator(chunk_size=batch_size), 1):
        stats['processed'] += 1

        if not registration.session:
            stats['skipped_no_session'] += 1
            continue

        if registration.sem is None:
            stats['skipped_no_sem'] += 1
            continue

        semester_variants = get_semester_variants(registration.sem)
        if not semester_variants:
            stats['skipped_no_sem'] += 1
            continue

        matches_qs = StudentCourseAssessment.objects.filter(
            student=registration.student,
            session=registration.session,
            semester__in=semester_variants,
        ).order_by('id')

        if exam_type:
            matches_qs = matches_qs.filter(exam_type__iexact=exam_type)

        match_ids = list(matches_qs.values_list('id', flat=True))

        if not match_ids:
            stats['skipped_no_matches'] += 1
            continue

        existing_ids = set(registration.assessment.values_list('id', flat=True))
        missing_ids = [assessment_id for assessment_id in match_ids if assessment_id not in existing_ids]

        if not missing_ids:
            stats['unchanged'] += 1
            continue

        stats['updated'] += 1
        stats['linked_assessments'] += len(missing_ids)

        if not dry_run:
            registration.assessment.add(*missing_ids)

        if index % batch_size == 0:
            print(f'Processed {index:,}/{total:,} registrations...')

    print('\n' + '=' * 100)
    print('SUMMARY')
    print('=' * 100)
    print(f"Processed:                 {stats['processed']:,}")
    print(f"Updated registrations:     {stats['updated']:,}")
    print(f"Linked assessments:        {stats['linked_assessments']:,}")
    print(f"Unchanged:                 {stats['unchanged']:,}")
    print(f"Skipped (no session):      {stats['skipped_no_session']:,}")
    print(f"Skipped (no sem):          {stats['skipped_no_sem']:,}")
    print(f"Skipped (no matches):      {stats['skipped_no_matches']:,}")
    print('=' * 100)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Map StudentCourseAssessment rows to ExamRegistration.assessment')
    parser.add_argument('--session', type=str, help='Filter exam registrations by session')
    parser.add_argument('--sem', type=int, help='Filter exam registrations by semester integer')
    parser.add_argument('--exam-type', type=str, help='Optional exam type filter for both registrations and assessments')
    parser.add_argument('--only-empty', action='store_true', help='Only process exam registrations with no assessment links yet')
    parser.add_argument('--batch-size', type=int, default=500, help='Iterator batch size')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not save')
    args = parser.parse_args()

    if not args.dry_run:
        with transaction.atomic():
            map_exam_registration_assessments(
                session=args.session,
                sem=args.sem,
                exam_type=args.exam_type,
                only_empty=args.only_empty,
                batch_size=args.batch_size,
                dry_run=False,
            )
    else:
        map_exam_registration_assessments(
            session=args.session,
            sem=args.sem,
            exam_type=args.exam_type,
            only_empty=args.only_empty,
            batch_size=args.batch_size,
            dry_run=True,
        )
