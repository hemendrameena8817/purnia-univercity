import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

import django
import pymysql

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.hashers import make_password
from accounts.models import UserAccount
from colleges.models import College
from ug.models import UGStudentProfile, UGDepartment, UGDegree, UGProgram, UGBatch

SOURCE_DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Locus@1234',
    'database': 'purnea_exm_new',
    'charset': 'utf8mb4',
}

DEFAULT_MISSING_FILE = BASE_DIR / 'scripts' / 'ug' / 'output' / 'missing_students.txt'
DEFAULT_PASSWORD_HASH = make_password('password')


def read_registration_numbers(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f'Missing students file not found: {file_path}')

    with file_path.open('r', encoding='utf-8') as file:
        values = [line.strip() for line in file if line.strip() and line.strip() != '.']

    return list(dict.fromkeys(values))


def parse_date(date_str):
    if not date_str:
        return None

    value = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y', '%d-%B-%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def map_gender(value):
    value = (value or '').strip().upper()
    if value == 'M':
        return 'Male'
    if value == 'F':
        return 'Female'
    return None


def split_name(name):
    clean_name = ' '.join((name or '').strip().split())
    if not clean_name:
        return '', ''
    parts = clean_name.split(' ', 1)
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]


def get_or_create_department(code, cache):
    code = (code or '').strip()
    if not code:
        return None
    if code == 'CORP':
        code = 'AC'
    if code == 'M18':
        return None
    if code in cache:
        return cache[code]

    department, _ = UGDepartment.objects.get_or_create(
        code=code,
        defaults={'name': f'Dept {code}'}
    )
    cache[code] = department
    return department


def get_or_create_degree(code, cache):
    code = (code or '').strip()
    if not code:
        return None
    if code in cache:
        return cache[code]

    degree, _ = UGDegree.objects.get_or_create(
        short_name=code,
        defaults={
            'name': f'Degree {code}',
            'total_semesters': 8,
            'total_years': 4,
        }
    )
    cache[code] = degree
    return degree


def get_or_create_program(degree, department, cache):
    if not degree:
        return None

    key = (degree.id, department.id if department else None)
    if key in cache:
        return cache[key]

    existing = UGProgram.objects.filter(degree=degree, department=department).first()
    if existing:
        cache[key] = existing
        return existing

    name = degree.short_name or degree.name
    if department:
        name = f'{name} - {department.name}'

    program = UGProgram.objects.create(
        name=name,
        short_name=degree.short_name,
        degree=degree,
        department=department,
    )
    cache[key] = program
    return program


def get_or_create_batch(batch_code, program, cache):
    batch_code = (batch_code or '').strip()
    if not batch_code:
        return None

    key = (batch_code, program.id if program else None)
    if key in cache:
        return cache[key]

    existing = UGBatch.objects.filter(name=batch_code, program=program).first()
    if existing:
        cache[key] = existing
        return existing

    batch = UGBatch.objects.create(name=batch_code, program=program)
    cache[key] = batch
    return batch


def fetch_registered_applicants_by_college_reg_no(registration_numbers):
    connection = pymysql.connect(**SOURCE_DB_CONFIG)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            placeholders = ','.join(['%s'] * len(registration_numbers))
            query = f'''
                SELECT college_reg_no, student_name, fathers_name, mothers_name, batch_code,
                       session_code, course_code, discipline_code, semester_code, dob, gender,
                       institute_code, roll_no, phone, category, full_address, aadhar_card_no,
                       addmision_date
                FROM registered_applicant_master
                WHERE college_reg_no IN ({placeholders})
            '''
            cursor.execute(query, registration_numbers)
            rows = cursor.fetchall()
    finally:
        connection.close()

    applicant_map = {}
    for row in rows:
        college_reg_no = (row.get('college_reg_no') or '').strip()
        if college_reg_no and college_reg_no not in applicant_map:
            applicant_map[college_reg_no] = row
    return applicant_map


def reset_existing_records(reg_nos):
    profiles_qs = UGStudentProfile.objects.filter(registration_no__in=reg_nos)
    users_qs = UserAccount.objects.filter(username__in=reg_nos, user_type='student')

    profile_count = profiles_qs.count()
    user_count = users_qs.count()

    with transaction.atomic():
        if profile_count:
            profiles_qs.delete()
        if user_count:
            users_qs.delete()

    print(f'Reset deleted profiles: {profile_count}')
    print(f'Reset deleted users: {user_count}')


def create_profiles(missing_file, reset=False):
    reg_nos = read_registration_numbers(missing_file)
    print(f'Loaded {len(reg_nos)} registration numbers from {missing_file}')

    if not reg_nos:
        print('No registration numbers found.')
        return

    if reset:
        reset_existing_records(reg_nos)

    users = UserAccount.objects.filter(username__in=reg_nos)
    user_map = {user.username: user for user in users}
    existing_profiles = set(
        UGStudentProfile.objects.filter(registration_no__in=reg_nos).values_list('registration_no', flat=True)
    )
    colleges = {college.college_code: college for college in College.objects.all() if college.college_code}
    department_cache = {dept.code: dept for dept in UGDepartment.objects.all() if dept.code}
    degree_cache = {degree.short_name: degree for degree in UGDegree.objects.all() if degree.short_name}
    program_cache = {
        (program.degree_id, program.department_id if program.department_id else None): program
        for program in UGProgram.objects.select_related('degree', 'department').all()
    }
    batch_cache = {
        (batch.name, batch.program_id if batch.program_id else None): batch
        for batch in UGBatch.objects.select_related('program').all()
    }

    applicants_by_college_reg_no = fetch_registered_applicants_by_college_reg_no(reg_nos)
    print(f'Found {len(applicants_by_college_reg_no)} rows in registered_applicant_master by college_reg_no')

    created_count = 0
    missing_user = []
    missing_source = []
    skipped_existing_profile = []
    pending_profiles = []
    created_users = 0

    for reg_no in reg_nos:
        if reg_no in existing_profiles:
            skipped_existing_profile.append(reg_no)
            print(f'SKIP PROFILE EXISTS: {reg_no}')
            continue

        source_row = applicants_by_college_reg_no.get(reg_no)
        if not source_row:
            missing_source.append(reg_no)
            print(f'SOURCE NOT FOUND BY college_reg_no: {reg_no}')
            continue

        college = colleges.get((source_row.get('institute_code') or '').strip())
        student_name = ' '.join((source_row.get('student_name') or '').strip().split())

        user = user_map.get(reg_no)
        if not user:
            user = UserAccount.objects.create(
                username=reg_no,
                first_name=(student_name or reg_no)[:100],
                last_name='',
                email=None,
                phone=(source_row.get('phone') or '').strip() or None,
                user_type='student',
                current_profile='ug',
                college=college,
                is_active=True,
                is_verified=False,
                password=DEFAULT_PASSWORD_HASH,
            )
            user_map[reg_no] = user
            created_users += 1
            print(f'USER CREATED: {reg_no}')

        department = get_or_create_department(source_row.get('discipline_code'), department_cache)
        degree = get_or_create_degree(source_row.get('course_code'), degree_cache)
        program = get_or_create_program(degree, department, program_cache)
        batch = get_or_create_batch(source_row.get('batch_code'), program, batch_cache)
        aadhar_no = (source_row.get('aadhar_card_no') or '').strip() or None
        if aadhar_no and len(aadhar_no) > 12:
            aadhar_no = None

        pending_profiles.append(UGStudentProfile(
            user=user,
            first_name=student_name[:255] if student_name else '',
            last_name='',
            registration_no=reg_no,
            address=(source_row.get('full_address') or '').strip() or None,
            admission_date=parse_date(source_row.get('addmision_date')),
            date_of_birth=parse_date(source_row.get('dob')),
            aadhar_no=aadhar_no,
            mobile_no=(source_row.get('phone') or '').strip() or None,
            gender=map_gender(source_row.get('gender')),
            caste=(source_row.get('category') or '').strip()[:20] or None,
            roll_no=(source_row.get('roll_no') or '').strip() or None,
            father_name=(source_row.get('fathers_name') or '').strip()[:255] or None,
            mother_name=(source_row.get('mothers_name') or '').strip()[:255] or None,
            current_semester=int(source_row.get('semester_code')) if str(source_row.get('semester_code') or '').isdigit() else None,
            session=(source_row.get('session_code') or '').strip() or None,
            status='Active',
            college=college,
            department=department,
            program=program,
            degree=degree,
            major_course=department,
            batch=batch,
            is_active=True,
            json_data={
                'source_table': 'registered_applicant_master',
                'source_database': SOURCE_DB_CONFIG['database'],
                'discipline_code': (source_row.get('discipline_code') or '').strip() or None,
                'course_code': (source_row.get('course_code') or '').strip() or None,
                'batch_code': (source_row.get('batch_code') or '').strip() or None,
                'college_reg_no': reg_no,
            },
        ))
        print(f'CREATE PROFILE: {reg_no}')

    if pending_profiles:
        with transaction.atomic():
            UGStudentProfile.objects.bulk_create(pending_profiles, ignore_conflicts=True)
        created_count = len(pending_profiles)

    print('')
    print(f'Users created: {created_users}')
    print(f'Profiles created: {created_count}')
    print(f'Profile already exists: {len(skipped_existing_profile)}')
    print(f'User not found: {len(missing_user)}')
    print(f'Source row not found: {len(missing_source)}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('missing_file', nargs='?', default=None)
    parser.add_argument('--file-path', dest='file_path', default=None)
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    input_file = args.file_path or args.missing_file or str(DEFAULT_MISSING_FILE)

    create_profiles(
        missing_file=Path(input_file),
        reset=args.reset,
    )


if __name__ == '__main__':
    main()
