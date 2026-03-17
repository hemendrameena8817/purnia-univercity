"""
Management command to sync specific UGStudentProfile records
from the local (default) database to the live database.

Usage:
    # Sync specific students by registration number
    python manage.py sync_students_to_live --reg-nos 2024001 2024002 2024003

    # Sync from a text file (one reg no per line)
    python manage.py sync_students_to_live --file reg_nos.txt

    # Dry run (no changes made)
    python manage.py sync_students_to_live --reg-nos 2024001 --dry-run

How it works:
    - Reads UGStudentProfile + UserAccount from 'default' DB
    - Creates/updates UserAccount in 'live' DB (username = registration_no)
    - Creates/updates UGStudentProfile in 'live' DB
    - FK relations (college, department, program, degree, batch, major/minor/mdc)
      are matched by NAME on the live DB — they must already exist there.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync UGStudentProfile records from default DB to live DB by registration number'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--reg-nos',
            nargs='+',
            type=str,
            help='List of registration numbers to sync'
        )
        group.add_argument(
            '--file',
            type=str,
            help='Path to a text file with one registration number per line'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Simulate the sync without writing to live DB'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # ── Collect registration numbers ──────────────────────────────────────
        if options['reg_nos']:
            reg_nos = [r.strip() for r in options['reg_nos'] if r.strip()]
        else:
            try:
                with open(options['file'], 'r') as f:
                    reg_nos = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                raise CommandError(f"File not found: {options['file']}")

        if not reg_nos:
            raise CommandError("No registration numbers provided.")

        self.stdout.write(f"📋 Found {len(reg_nos)} registration number(s) to sync")
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN — no changes will be written to live DB"))

        # ── Import models here to avoid circular import issues ────────────────
        from accounts.models import UserAccount
        from ug.models import UGStudentProfile, UGDepartment, UGProgram, UGDegree, UGBatch, SemesterRegistration
        from colleges.models import College  # adjust if your app name differs
        from django.utils import timezone
        import datetime

        # Fixed values for SemesterRegistration
        SEM_REG_START = datetime.datetime(2026, 2, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)
        SEM_REG_END   = datetime.datetime(2026, 2, 22, 00, 00, 00, tzinfo=datetime.timezone.utc)

        stats = {'synced': 0, 'skipped': 0, 'errors': 0}

        for reg_no in reg_nos:
            self.stdout.write(f"\n── Processing: {reg_no}")

            # ── 1. Fetch from local (default) DB ──────────────────────────────
            try:
                local_profile = UGStudentProfile.objects.using('default').select_related(
                    'user', 'college', 'department', 'program', 'degree', 'batch',
                    'major_course', 'minor_course', 'mdc_course'
                ).get(registration_no=reg_no)
            except UGStudentProfile.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"  ✗ Profile not found in local DB for: {reg_no}"))
                stats['errors'] += 1
                continue

            local_user = local_profile.user

            # ── 2. Resolve FK relationships on live DB by name ────────────────
            live_college = None
            if local_profile.college:
                live_college = College.objects.using('live').filter(
                    college_code=local_profile.college.college_code
                ).first()
                if not live_college:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ College '{local_profile.college.name}' not found on live DB — will be set to NULL"
                    ))

            live_department = None
            if local_profile.department:
                live_department = UGDepartment.objects.using('live').filter(
                    code=local_profile.department.code
                ).first()
                if not live_department:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ Department code '{local_profile.department.code}' not found on live DB — will be set to NULL"
                    ))

            live_program = None
            if local_profile.program:
                live_program = UGProgram.objects.using('live').filter(
                    name=local_profile.program.name
                ).first()
                if not live_program:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ Program '{local_profile.program.name}' not found on live DB — will be set to NULL"
                    ))

            live_degree = None
            if local_profile.degree:
                live_degree = UGDegree.objects.using('live').filter(
                    short_name=local_profile.degree.short_name
                ).first()
                if not live_degree:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ Degree '{local_profile.degree.short_name}' not found on live DB — will be set to NULL"
                    ))

            live_batch = None
            if local_profile.batch:
                live_batch = UGBatch.objects.using('live').filter(
                    name=local_profile.batch.name
                ).first()
                if not live_batch:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ Batch '{local_profile.batch.name}' not found on live DB — will be set to NULL"
                    ))

            live_major = None
            if local_profile.major_course:
                live_major = UGDepartment.objects.using('live').filter(
                    code=local_profile.major_course.code,
                    is_publish=True
                ).first()
                if not live_major:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ major_course code '{local_profile.major_course.code}' not found (published) on live DB"
                    ))

            live_minor = None
            if local_profile.minor_course:
                live_minor = UGDepartment.objects.using('live').filter(
                    code=local_profile.minor_course.code,
                    is_publish=True
                ).first()
                if not live_minor:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ minor_course code '{local_profile.minor_course.code}' not found (published) on live DB"
                    ))

            live_mdc = None
            if local_profile.mdc_course:
                live_mdc = UGDepartment.objects.using('live').filter(
                    code=local_profile.mdc_course.code,
                    is_publish=True
                ).first()
                if not live_mdc:
                    self.stderr.write(self.style.WARNING(
                        f"  ⚠ mdc_course code '{local_profile.mdc_course.code}' not found (published) on live DB"
                    ))

            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ [DRY RUN] Would sync: {local_user.username} / {reg_no}"
                ))
                stats['synced'] += 1
                continue

            # ── 3. Create UserAccount on live DB (skip if already exists) ──────
            try:
                with transaction.atomic(using='live'):
                    live_user = UserAccount.objects.using('live').filter(
                        username=local_user.username
                    ).first()

                    if live_user:
                        # Only update current_profile, leave everything else untouched
                        UserAccount.objects.using('live').filter(pk=live_user.pk).update(
                            current_profile='ug'
                        )
                        self.stdout.write(f"  ✓ UserAccount exists: {live_user.username} — updated current_profile to 'ug'")
                    else:
                        live_user = UserAccount.objects.using('live').create(
                            username=local_user.username,   # username == registration_no
                            email=local_user.email,
                            first_name=local_user.first_name,
                            last_name=local_user.last_name,
                            phone=local_user.phone,
                            user_type=local_user.user_type,
                            current_profile='ug',
                            college=live_college,
                            is_verified=local_user.is_verified,
                            is_active=local_user.is_active,
                            is_staff=local_user.is_staff,
                            # is_password_changed=local_user.is_password_changed,
                            # password=local_user.password,  # copy hashed password as-is
                        )
                        self.stdout.write(f"  ✓ Created UserAccount: {live_user.username}")

                    # ── 4. Create or Update UGStudentProfile on live DB ──────────
                    existing = UGStudentProfile.objects.using('live').filter(
                        registration_no=reg_no
                    ).first()

                    profile_fields = dict(
                        user=live_user,
                        first_name=local_profile.first_name,
                        last_name=local_profile.last_name,
                        hindi_name=local_profile.hindi_name,
                        address=local_profile.address,
                        admission_date=local_profile.admission_date,
                        date_of_birth=local_profile.date_of_birth,
                        aadhar_no=local_profile.aadhar_no,
                        apaar_id=local_profile.apaar_id,
                        mobile_no=local_profile.mobile_no,
                        migration_submitted=local_profile.migration_submitted,
                        last_university=local_profile.last_university,
                        gender=local_profile.gender,
                        caste=local_profile.caste,
                        enrollment_date=local_profile.enrollment_date,
                        roll_no=local_profile.roll_no,
                        father_name=local_profile.father_name,
                        mother_name=local_profile.mother_name,
                        current_semester=2,
                        session='2025-26',
                        status=local_profile.status,
                        is_active=local_profile.is_active,
                        json_data=local_profile.json_data,
                        # Resolved FKs
                        college=live_college,
                        department=live_department,
                        program=live_program,
                        degree=live_degree,
                        batch=live_batch,
                        major_course=live_major,
                        minor_course=live_minor,
                        mdc_course=live_mdc,
                    )

                    if existing:
                        # Update all fields on existing profile
                        for field, val in profile_fields.items():
                            setattr(existing, field, val)
                        existing.save(using='live', update_fields=list(profile_fields.keys()))
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✓ Updated UGStudentProfile: {reg_no} "
                            f"(MJC={live_major}, MIC={live_minor}, MDC={live_mdc})"
                        ))
                        stats['synced'] += 1
                    else:
                        UGStudentProfile.objects.using('live').create(
                            registration_no=reg_no,
                            **profile_fields,
                            # Note: profile_image/signature not copied — shared S3 storage
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✓ Created UGStudentProfile: {reg_no}"
                        ))
                        stats['synced'] += 1

                    # ── 5. SemesterRegistration on live DB (skip if already exists) ──
                    # Get the live profile reference (whether just created or pre-existing)
                    live_ug_profile = UGStudentProfile.objects.using('live').filter(
                        registration_no=reg_no
                    ).first()

                    if live_ug_profile:
                        sem_reg_exists = SemesterRegistration.objects.using('live').filter(
                            student=live_ug_profile,
                            sem=3,
                            session='2025-26'
                        ).exists()

                        # if sem_reg_exists:
                        #     self.stdout.write(f"  ⏭  SemesterRegistration already exists for {reg_no} sem=3 — skipping")
                        # else:
                        #     SemesterRegistration.objects.using('live').create(
                        #         student=live_ug_profile,
                        #         batch=live_batch,
                        #         sem=3,
                        #         session='2025-26',
                        #         status='OPEN',
                        #         is_open=True,
                        #         start_date=SEM_REG_START,
                        #         end_date=SEM_REG_END,
                        #     )
                        #     self.stdout.write(self.style.SUCCESS(
                        #         f"  ✓ Created SemesterRegistration: {reg_no} sem=3 session=2025-26"
                        #     ))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  ✗ Failed for {reg_no}: {e}"))
                logger.exception(f"sync_students_to_live error for {reg_no}")
                stats['errors'] += 1

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("\n" + "═" * 50)
        self.stdout.write(f"✅ Synced:  {stats['synced']}")
        self.stdout.write(f"⏭  Skipped: {stats['skipped']}")
        self.stdout.write(f"❌ Errors:  {stats['errors']}")
        self.stdout.write("═" * 50)
