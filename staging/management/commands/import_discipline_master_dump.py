"""
Management command to import discipline_master data from purnea_exm_new dump database
into Django DisciplineMasterDump staging model.

Usage:
    python manage.py import_discipline_master_dump --settings=pup_umis_backend.settings.development
    python manage.py import_discipline_master_dump --clear --settings=pup_umis_backend.settings.development
"""

import MySQLdb
from django.core.management.base import BaseCommand
from django.conf import settings
from staging.models import DisciplineMasterDump


class Command(BaseCommand):
    help = 'Import discipline_master data from purnea_exm_new dump database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to insert in each batch (default: 1000)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before importing'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        clear_existing = options['clear']
        
        # Database connection settings for dump database
        db_settings = settings.DATABASES['default']
        
        self.stdout.write(self.style.WARNING('Connecting to purnea_exm_new database...'))
        
        # Connect to the dump database
        connection = MySQLdb.connect(
            host=db_settings['HOST'],
            user=db_settings['USER'],
            passwd=db_settings['PASSWORD'],
            db='purnea_exm_new',
            port=int(db_settings['PORT']),
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM discipline_master")
        total_count = cursor.fetchone()[0]
        self.stdout.write(f"Total records to import: {total_count}")
        
        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing DisciplineMasterDump data...'))
            DisciplineMasterDump.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
        
        # Column mapping from dump table to Django model
        columns = [
            'id', 'discipline_code', 'discipline', 'discipline_name', 'discipline_name_new',
            'subject_name', 'institute_code', 'created_by', 'created_on', 'updated_by',
            'updated_on', 'record_status', 'last_updated', 'discipline_name_hindi'
        ]
        
        query = f"SELECT {', '.join(columns)} FROM discipline_master"
        cursor.execute(query)
        
        # Process in batches
        imported_count = 0
        batch = []
        
        self.stdout.write(self.style.WARNING('Starting import...'))
        
        for row in cursor:
            obj = DisciplineMasterDump(
                source_id=str(row[0]) if row[0] is not None else None,
                discipline_code=str(row[1]) if row[1] is not None else None,
                discipline=str(row[2]) if row[2] is not None else None,
                discipline_name=str(row[3]) if row[3] is not None else None,
                discipline_name_new=str(row[4]) if row[4] is not None else None,
                subject_name=str(row[5]) if row[5] is not None else None,
                institute_code=str(row[6]) if row[6] is not None else None,
                created_by=str(row[7]) if row[7] is not None else None,
                created_on=str(row[8]) if row[8] is not None else None,
                updated_by=str(row[9]) if row[9] is not None else None,
                updated_on=str(row[10]) if row[10] is not None else None,
                record_status=str(row[11]) if row[11] is not None else None,
                last_updated=str(row[12]) if row[12] is not None else None,
                discipline_name_hindi=str(row[13]) if row[13] is not None else None,
            )
            batch.append(obj)
            
            if len(batch) >= batch_size:
                DisciplineMasterDump.objects.bulk_create(batch, ignore_conflicts=True)
                imported_count += len(batch)
                self.stdout.write(f"Imported {imported_count}/{total_count} records...")
                batch = []
        
        # Import remaining records
        if batch:
            DisciplineMasterDump.objects.bulk_create(batch, ignore_conflicts=True)
            imported_count += len(batch)
        
        cursor.close()
        connection.close()
        
        # Final count in Django table
        final_count = DisciplineMasterDump.objects.count()
        
        self.stdout.write(self.style.SUCCESS(
            f"\nImport completed!"
            f"\nRecords in source table: {total_count}"
            f"\nRecords imported: {imported_count}"
            f"\nTotal records in Django table: {final_count}"
        ))
