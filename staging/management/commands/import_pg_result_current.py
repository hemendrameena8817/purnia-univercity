"""
Management command to import PG_result_current data from purnea_exm_new dump database
into Django PGResultCurrent staging model.

Usage:
    python manage.py import_pg_result_current --settings=pup_umis_backend.settings.development
    python manage.py import_pg_result_current --batch-size=5000 --settings=pup_umis_backend.settings.development
"""

import MySQLdb
from django.core.management.base import BaseCommand
from django.conf import settings
from staging.models import PGResultCurrent


class Command(BaseCommand):
    help = 'Import PG_result_current data from purnea_exm_new dump database'

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
        cursor.execute("SELECT COUNT(*) FROM PG_result_current")
        total_count = cursor.fetchone()[0]
        self.stdout.write(f"Total records to import: {total_count}")
        
        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing PGResultCurrent data...'))
            PGResultCurrent.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
        
        # Column mapping from dump table to Django model
        columns = [
            'id', 'user_id', 'college_roll_no', 'college_reg_no', 'student_name',
            'fathers_name', 'mothers_name', 'semester_code', 'batch_code', 'session_code',
            'course_code', 'discipline_code', 'paper_code', 'subject_code', 'subject_name',
            'faculty', 'status', 'exam_type_his', 'exam_type', 'maximum_mark',
            'pass_mark', 'mark_secured', 'subject_total_mark', 'subject_ca', 'subject_ng',
            'subject_ce', 'subject_gp', 'total_ca', 'total_ce', 'subject_result',
            'final_result', 'grand_total_mark', 'total_secured_mark', 'total_per', 'institute_code',
            'gpa', 'cgpa', 'numrical_let_grad', 'let_grad_sub', 'let_grad',
            'dsc_grad', 'agreegate', 'grade', 'record_status', 'final_sheet_status',
            'student_name_hindi', 'max_total_mark'
        ]
        
        query = f"SELECT {', '.join(columns)} FROM PG_result_current"
        cursor.execute(query)
        
        # Process in batches
        imported_count = 0
        batch = []
        
        self.stdout.write(self.style.WARNING('Starting import...'))
        
        for row in cursor:
            obj = PGResultCurrent(
                source_id=str(row[0]) if row[0] is not None else None,
                user_id=str(row[1]) if row[1] is not None else None,
                college_roll_no=str(row[2]) if row[2] is not None else None,
                college_reg_no=str(row[3]) if row[3] is not None else None,
                student_name=str(row[4]) if row[4] is not None else None,
                fathers_name=str(row[5]) if row[5] is not None else None,
                mothers_name=str(row[6]) if row[6] is not None else None,
                semester_code=str(row[7]) if row[7] is not None else None,
                batch_code=str(row[8]) if row[8] is not None else None,
                session_code=str(row[9]) if row[9] is not None else None,
                course_code=str(row[10]) if row[10] is not None else None,
                discipline_code=str(row[11]) if row[11] is not None else None,
                paper_code=str(row[12]) if row[12] is not None else None,
                subject_code=str(row[13]) if row[13] is not None else None,
                subject_name=str(row[14]) if row[14] is not None else None,
                faculty=str(row[15]) if row[15] is not None else None,
                status=str(row[16]) if row[16] is not None else None,
                exam_type_his=str(row[17]) if row[17] is not None else None,
                exam_type=str(row[18]) if row[18] is not None else None,
                maximum_mark=str(row[19]) if row[19] is not None else None,
                pass_mark=str(row[20]) if row[20] is not None else None,
                mark_secured=str(row[21]) if row[21] is not None else None,
                subject_total_mark=str(row[22]) if row[22] is not None else None,
                subject_ca=str(row[23]) if row[23] is not None else None,
                subject_ng=str(row[24]) if row[24] is not None else None,
                subject_ce=str(row[25]) if row[25] is not None else None,
                subject_gp=str(row[26]) if row[26] is not None else None,
                total_ca=str(row[27]) if row[27] is not None else None,
                total_ce=str(row[28]) if row[28] is not None else None,
                subject_result=str(row[29]) if row[29] is not None else None,
                final_result=str(row[30]) if row[30] is not None else None,
                grand_total_mark=str(row[31]) if row[31] is not None else None,
                total_secured_mark=str(row[32]) if row[32] is not None else None,
                total_per=str(row[33]) if row[33] is not None else None,
                institute_code=str(row[34]) if row[34] is not None else None,
                gpa=str(row[35]) if row[35] is not None else None,
                cgpa=str(row[36]) if row[36] is not None else None,
                numrical_let_grad=str(row[37]) if row[37] is not None else None,
                let_grad_sub=str(row[38]) if row[38] is not None else None,
                let_grad=str(row[39]) if row[39] is not None else None,
                dsc_grad=str(row[40]) if row[40] is not None else None,
                agreegate=str(row[41]) if row[41] is not None else None,
                grade=str(row[42]) if row[42] is not None else None,
                record_status=str(row[43]) if row[43] is not None else None,
                final_sheet_status=str(row[44]) if row[44] is not None else None,
                student_name_hindi=str(row[45]) if row[45] is not None else None,
                max_total_mark=str(row[46]) if row[46] is not None else None,
            )
            batch.append(obj)
            
            if len(batch) >= batch_size:
                PGResultCurrent.objects.bulk_create(batch, ignore_conflicts=True)
                imported_count += len(batch)
                self.stdout.write(f"Imported {imported_count}/{total_count} records...")
                batch = []
        
        # Import remaining records
        if batch:
            PGResultCurrent.objects.bulk_create(batch, ignore_conflicts=True)
            imported_count += len(batch)
        
        cursor.close()
        connection.close()
        
        # Final count in Django table
        final_count = PGResultCurrent.objects.count()
        
        self.stdout.write(self.style.SUCCESS(
            f"\nImport completed!"
            f"\nRecords in source table: {total_count}"
            f"\nRecords imported: {imported_count}"
            f"\nTotal records in Django table: {final_count}"
        ))
