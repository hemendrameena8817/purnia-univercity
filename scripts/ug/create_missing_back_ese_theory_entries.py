#!/usr/bin/env python
import argparse
import os
import sys
import uuid
from decimal import Decimal

import django
from django.db import transaction

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug.models import StudentCourseAssessment


THEORY_LABEL = 'ESE-Theory'
PRACTICAL_LABEL = 'ESE-Practical'
BACK_EXAM_TYPE = 'BACK'
THEORY_MAX_MARKS = 70
THEORY_PASS_MARKS = Decimal('31.50')


def get_paper_code_match_key(paper_code):
    if not paper_code:
        return None

    paper_code_str = str(paper_code).strip()
    prefix = paper_code_str.split('-')[0].split('/')[0].strip()
    digits = ''.join(ch for ch in prefix if ch.isdigit())
    if digits:
        return digits[-3:]

    return prefix[-3:].upper() if len(prefix) >= 3 else prefix.upper()


def build_theory_entry(practical: StudentCourseAssessment) -> StudentCourseAssessment:
    return StudentCourseAssessment(
        uid=uuid.uuid4(),
        course_name=practical.course_name,
        course_short_name=practical.course_short_name,
        student=practical.student,
        course_type=practical.course_type,
        course_code=practical.course_code,
        paper_code=practical.paper_code,
        semester=practical.semester,
        label=THEORY_LABEL,
        department=practical.department,
        degree=practical.degree,
        session=practical.session,
        batch=practical.batch,
        college_code=practical.college_code,
        exam_type=practical.exam_type,
        attendance=None,
        ind_max_marks=THEORY_MAX_MARKS,
        ind_pass_marks=THEORY_PASS_MARKS,
        ind_is_absent=False,
        ind_marks_obtained=None,
        ind_grace_obtained=Decimal('0.00'),
        ind_final_marks_obtained=None,
        ind_is_pass=None,
        comb_max_marks=Decimal('0.00'),
        comb_max_credits=Decimal('0.00'),
        comb_pass_marks=Decimal('0.00'),
        comb_marks_obtained=None,
        comb_grace_obtained=Decimal('0.00'),
        comb_final_marks_obtained=None,
        comb_credit_obtained=None,
        comb_numeric_grade=None,
        comb_letter_grade=None,
        comb_grade_point=None,
        course_max_marks=Decimal('0.00'),
        course_max_credits=Decimal('0.00'),
        course_pass_marks=Decimal('0.00'),
        course_marks_obtained=None,
        course_grace_obtained=Decimal('0.00'),
        course_final_marks_obtained=None,
        course_credit_obtained=None,
        course_grade_point=None,
        sem_max_credit=None,
        sem_credit_obtained=None,
        sgpa=None,
        sem_result=None,
        next_sem_status=None,
        sem_grace_obtained=Decimal('0.00'),
        cia_filled_on=None,
        is_migrated=practical.is_migrated,
        json_data=practical.json_data,
    )


def find_candidates(session=None, semester=None, reg_no=None, username=None):
    queryset = StudentCourseAssessment.objects.select_related('student', 'student__user').filter(
        exam_type__iexact=BACK_EXAM_TYPE,
        label=PRACTICAL_LABEL,
    ).order_by('student__registration_no', 'paper_code', 'id')

    if session:
        queryset = queryset.filter(session=session)
    if semester:
        queryset = queryset.filter(semester=semester)
    if reg_no:
        queryset = queryset.filter(student__registration_no=reg_no)
    if username:
        queryset = queryset.filter(student__user__username=username)

    theory_queryset = StudentCourseAssessment.objects.filter(
        exam_type__iexact=BACK_EXAM_TYPE,
        label=THEORY_LABEL,
    )

    if session:
        theory_queryset = theory_queryset.filter(session=session)
    if semester:
        theory_queryset = theory_queryset.filter(semester=semester)
    if reg_no:
        theory_queryset = theory_queryset.filter(student__registration_no=reg_no)
    if username:
        theory_queryset = theory_queryset.filter(student__user__username=username)

    theory_keys = set()
    for theory in theory_queryset.iterator(chunk_size=500):
        paper_code_key = get_paper_code_match_key(theory.paper_code)
        if not paper_code_key:
            continue
        theory_keys.add((theory.student_id, theory.session, theory.semester, paper_code_key))

    candidates = []
    seen_practical_keys = set()
    for practical in queryset.iterator(chunk_size=500):
        paper_code_key = get_paper_code_match_key(practical.paper_code)
        if not paper_code_key:
            continue

        match_key = (practical.student_id, practical.session, practical.semester, paper_code_key)
        if match_key in theory_keys or match_key in seen_practical_keys:
            continue

        seen_practical_keys.add(match_key)
        candidates.append(practical)

    return candidates


def run(session=None, semester=None, reg_no=None, username=None, batch_size=500, dry_run=False):
    candidates = find_candidates(session=session, semester=semester, reg_no=reg_no, username=username)

    print('=' * 120)
    print('BACK ESE PRACTICAL-ONLY CHECK')
    print('=' * 120)
    print(f'Candidates found: {len(candidates):,}')
    print(f'Total {THEORY_LABEL} entries to create: {len(candidates):,}')
    if session:
        print(f'Session filter: {session}')
    if semester:
        print(f'Semester filter: {semester}')
    if reg_no:
        print(f'Registration No filter: {reg_no}')
    if username:
        print(f'Username filter: {username}')
    print(f'Mode: {"DRY RUN" if dry_run else "LIVE"}')
    print('-' * 120)

    if not candidates:
        print('No BACK ESE-Practical-only entries found.')
        return

    for practical in candidates:
        student = practical.student
        user = getattr(student, 'user', None)
        username_value = getattr(user, 'username', '-') if user else '-'
        print(
            f"reg_no={getattr(student, 'registration_no', '-') or '-'} | "
            f"username={username_value or '-'} | "
            f"student_id={student.id} | "
            f"paper_code={practical.paper_code or '-'} | "
            f"paper_code_key={get_paper_code_match_key(practical.paper_code) or '-'} | "
            f"course_code={practical.course_code or '-'} | "
            f"course_type={practical.course_type or '-'} | "
            f"session={practical.session or '-'} | "
            f"semester={practical.semester or '-'} | "
            f"practical_id={practical.id}"
        )

    if dry_run:
        print(f'\nDry-run total {THEORY_LABEL} entries to create: {len(candidates):,}')
        print('\nDry run only. No theory entries created.')
        return

    to_create = [build_theory_entry(practical) for practical in candidates]

    with transaction.atomic():
        StudentCourseAssessment.objects.bulk_create(to_create, batch_size=batch_size)

    print('\n' + '=' * 120)
    print(f'Total {THEORY_LABEL} entries created: {len(to_create):,}')
    print(f'Created {len(to_create):,} missing {THEORY_LABEL} entries.')
    print('=' * 120)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create missing BACK ESE-Theory entries wherever only ESE-Practical exists for a paper.'
    )
    parser.add_argument('--session', type=str, help='Filter by session, e.g. 2025-26')
    parser.add_argument('--semester', type=str, help='Filter by semester text, e.g. 1ST')
    parser.add_argument('--reg-no', type=str, help='Filter by student registration number')
    parser.add_argument('--username', type=str, help='Filter by student username')
    parser.add_argument('--batch-size', type=int, default=500, help='Bulk create batch size')
    parser.add_argument('--dry-run', action='store_true', help='Preview matching students/papers without saving')
    args = parser.parse_args()

    run(
        session=args.session,
        semester=args.semester,
        reg_no=args.reg_no,
        username=args.username,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
