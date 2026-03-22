"""
Management command to import center_institute_map_purnea data from staging
into pgoldresult.PGCenterInstituteMap model with course_code=PG filter.

Usage:
    python manage.py import_pg_center_institute --settings=pup_umis_backend.settings.development
    python manage.py import_pg_center_institute --batch-size=5000 --settings=pup_umis_backend.settings.development
    python manage.py import_pg_center_institute --clear --settings=pup_umis_backend.settings.development
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from staging.models import CenterInstituteMapPurnea
from pgoldresult.models import PGCenterInstituteMap


class Command(BaseCommand):
    help = 'Import center_institute_map_purnea data from staging to pgoldresult (filtered by PG course_code)'

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
            help='Clear existing PGCenterInstituteMap data before importing'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        clear_existing = options['clear']
        
        # Filter by course_code=PG from staging
        source_queryset = CenterInstituteMapPurnea.objects.filter(course_code='PG')
        total_count = source_queryset.count()
        
        self.stdout.write(self.style.WARNING(f"Found {total_count} records with course_code='PG' in staging.CenterInstituteMapPurnea"))
        
        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing PGCenterInstituteMap data...'))
            PGCenterInstituteMap.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No records to import.'))
            return
        
        # Process in batches
        imported_count = 0
        batch = []
        
        self.stdout.write(self.style.WARNING('Starting import...'))
        
        for source_record in source_queryset.iterator():
            obj = PGCenterInstituteMap(
                source_id=source_record.source_id,
                center_code=source_record.center_code,
                center_name=source_record.center_name,
                batch_code=source_record.batch_code,
                course_code=source_record.course_code,
                semester_code=source_record.semester_code,
                institute_code=source_record.institute_code,
                institute_name=source_record.institute_name,
                record_status=source_record.record_status,
                exam_type=source_record.exam_type,
                session_code=source_record.session_code,
                is_sem=source_record.is_sem,
            )
            batch.append(obj)
            
            if len(batch) >= batch_size:
                PGCenterInstituteMap.objects.bulk_create(batch, batch_size=batch_size)
                imported_count += len(batch)
                self.stdout.write(f"Imported {imported_count}/{total_count} records...")
                batch = []
        
        # Import remaining records
        if batch:
            PGCenterInstituteMap.objects.bulk_create(batch, batch_size=batch_size)
            imported_count += len(batch)
        
        # Final count in Django table
        final_count = PGCenterInstituteMap.objects.count()
        
        self.stdout.write(self.style.SUCCESS(
            f"\nImport completed!"
            f"\nRecords in source table (course_code=PG): {total_count}"
            f"\nRecords imported: {imported_count}"
            f"\nTotal records in pgoldresult.PGCenterInstituteMap: {final_count}"
        ))
