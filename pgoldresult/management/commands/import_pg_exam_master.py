"""
Management command to import exam_master data from staging.ExamMasterDump
into pgoldresult.PGExamMasterDump model (course_code=PG only).

Usage:
    python manage.py import_pg_exam_master
    python manage.py import_pg_exam_master --batch-size=5000
    python manage.py import_pg_exam_master --clear
"""

from django.core.management.base import BaseCommand
from staging.models import ExamMasterDump
from pgoldresult.models import PGExamMasterDump


class Command(BaseCommand):
    help = 'Import exam_master data from staging.ExamMasterDump to pgoldresult.PGExamMasterDump (PG only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=5000,
            help='Number of records to insert in each batch (default: 5000)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing PGExamMasterDump data before importing'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        clear_existing = options['clear']

        # Filter by course_code=PG from staging
        source_queryset = ExamMasterDump.objects.filter(course_code='PG')
        total_count = source_queryset.count()

        self.stdout.write(self.style.WARNING(
            f"Found {total_count} records with course_code='PG' in staging.ExamMasterDump"
        ))

        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing PGExamMasterDump data...'))
            PGExamMasterDump.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        if total_count == 0:
            self.stdout.write(self.style.WARNING('No records found with course_code=PG. Import skipped.'))
            return

        # Process in batches
        imported_count = 0
        batch = []

        self.stdout.write(self.style.WARNING('Starting import...'))

        for source in source_queryset.iterator():
            obj = PGExamMasterDump(
                source_id=source.source_id,
                exam_type=source.exam_type,
                exam_code=source.exam_code,
                exam_name=source.exam_name,
                batch_code=source.batch_code,
                session_code=source.session_code,
                course_code=source.course_code,
                discipline_code=source.discipline_code,
                semester_code=source.semester_code,
                publish_all=source.publish_all,
                actual_exam_month=source.actual_exam_month,
                year=source.year,
                sl_no=source.sl_no,
                exam_month=source.exam_month,
                exam_year=source.exam_year,
                exam_start_date=source.exam_start_date,
                exam_end_date=source.exam_end_date,
                apply_start_date=source.apply_start_date,
                apply_end_date=source.apply_end_date,
                exam_mark_entry_date=source.exam_mark_entry_date,
                online_payment_transaction_no=source.online_payment_transaction_no,
                omr_no=source.omr_no,
                template_code=source.template_code,
                publish_status=source.publish_status,
                institute_code=source.institute_code,
                created_by=source.created_by,
                created_on=source.created_on,
                updated_by=source.updated_by,
                updated_on=source.updated_on,
                record_status=source.record_status,
                last_updated=source.last_updated,
                is_sem=source.is_sem,
                copied_from_staging=True,
            )
            batch.append(obj)

            if len(batch) >= batch_size:
                PGExamMasterDump.objects.bulk_create(batch, batch_size=batch_size)
                imported_count += len(batch)
                self.stdout.write(f"Imported {imported_count}/{total_count} records...")
                batch = []

        # Import remaining records
        if batch:
            PGExamMasterDump.objects.bulk_create(batch, batch_size=batch_size)
            imported_count += len(batch)

        final_count = PGExamMasterDump.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f"\nImport completed!"
            f"\nRecords in source table (course_code=PG): {total_count}"
            f"\nRecords imported this run: {imported_count}"
            f"\nTotal records in pgoldresult.PGExamMasterDump: {final_count}"
        ))
