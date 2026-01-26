"""
Management command to import registered_applicant_master data from purnea_exm_new dump database
into Django RegisteredApplicantMaster staging model.

Usage:
    python manage.py import_registered_applicant_master --settings=pup_umis_backend.settings.development
    python manage.py import_registered_applicant_master --clear --settings=pup_umis_backend.settings.development
"""

import MySQLdb
from django.core.management.base import BaseCommand
from django.conf import settings
from staging.models import RegisteredApplicantMaster


class Command(BaseCommand):
    help = 'Import registered_applicant_master data from purnea_exm_new dump database'

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
        cursor.execute("SELECT COUNT(*) FROM registered_applicant_master")
        total_count = cursor.fetchone()[0]
        self.stdout.write(f"Total records to import: {total_count}")
        
        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing RegisteredApplicantMaster data...'))
            RegisteredApplicantMaster.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
        
        # Column mapping from dump table to Django model
        # Note: backticks for columns starting with numbers
        query = """
            SELECT 
                id, reg_no, sams_id, college_roll_no, college_reg_no,
                center, `3rdcenter2017_old`, `3rdcenter2017`, roll_no, result,
                exam_type_code, student_name, fathers_name, mothers_name, appl_no,
                course_code, discipline_code, semester_code, batch_code, syllabus_year,
                institute_code, session_code, phone, dob, gender,
                category, Approve, full_address, institute_pub_status, student_pub_status,
                last_board, aadhar_card_no, created_by, created_on, updated_by,
                updated_on, record_status, last_updated, payment_status, is_sem,
                ABC_Id, Addmision_date, api_status
            FROM registered_applicant_master
        """
        cursor.execute(query)
        
        # Process in batches
        imported_count = 0
        batch = []
        
        self.stdout.write(self.style.WARNING('Starting import...'))
        
        for row in cursor:
            obj = RegisteredApplicantMaster(
                csv_id=str(row[0]) if row[0] is not None else None,
                reg_no=str(row[1]) if row[1] is not None else None,
                sams_id=str(row[2]) if row[2] is not None else None,
                college_roll_no=str(row[3]) if row[3] is not None else None,
                college_reg_no=str(row[4]) if row[4] is not None else None,
                center=str(row[5]) if row[5] is not None else None,
                center2017_old=str(row[6]) if row[6] is not None else None,
                center2017=str(row[7]) if row[7] is not None else None,
                roll_no=str(row[8]) if row[8] is not None else None,
                result=str(row[9]) if row[9] is not None else None,
                exam_type_code=str(row[10]) if row[10] is not None else None,
                student_name=str(row[11]) if row[11] is not None else None,
                fathers_name=str(row[12]) if row[12] is not None else None,
                mothers_name=str(row[13]) if row[13] is not None else None,
                appl_no=str(row[14]) if row[14] is not None else None,
                course_code=str(row[15]) if row[15] is not None else None,
                discipline_code=str(row[16]) if row[16] is not None else None,
                semester_code=str(row[17]) if row[17] is not None else None,
                batch_code=str(row[18]) if row[18] is not None else None,
                syllabus_year=str(row[19]) if row[19] is not None else None,
                institute_code=str(row[20]) if row[20] is not None else None,
                session_code=str(row[21]) if row[21] is not None else None,
                phone=str(row[22]) if row[22] is not None else None,
                dob=str(row[23]) if row[23] is not None else None,
                gender=str(row[24]) if row[24] is not None else None,
                category=str(row[25]) if row[25] is not None else None,
                approve=str(row[26]) if row[26] is not None else None,
                full_address=str(row[27]) if row[27] is not None else None,
                institute_pub_status=str(row[28]) if row[28] is not None else None,
                student_pub_status=str(row[29]) if row[29] is not None else None,
                last_board=str(row[30]) if row[30] is not None else None,
                aadhar_card_no=str(row[31]) if row[31] is not None else None,
                created_by=str(row[32]) if row[32] is not None else None,
                created_on=str(row[33]) if row[33] is not None else None,
                updated_by=str(row[34]) if row[34] is not None else None,
                updated_on=str(row[35]) if row[35] is not None else None,
                record_status=str(row[36]) if row[36] is not None else None,
                last_updated=str(row[37]) if row[37] is not None else None,
                payment_status=str(row[38]) if row[38] is not None else None,
                is_sem=str(row[39]) if row[39] is not None else None,
                abc_id=str(row[40]) if row[40] is not None else None,
                addmision_date=str(row[41]) if row[41] is not None else None,
                api_status=str(row[42]) if row[42] is not None else None,
            )
            batch.append(obj)
            
            if len(batch) >= batch_size:
                RegisteredApplicantMaster.objects.bulk_create(batch, ignore_conflicts=True)
                imported_count += len(batch)
                self.stdout.write(f"Imported {imported_count}/{total_count} records...")
                batch = []
        
        # Import remaining records
        if batch:
            RegisteredApplicantMaster.objects.bulk_create(batch, ignore_conflicts=True)
            imported_count += len(batch)
        
        cursor.close()
        connection.close()
        
        # Final count in Django table
        final_count = RegisteredApplicantMaster.objects.count()
        
        self.stdout.write(self.style.SUCCESS(
            f"\nImport completed!"
            f"\nRecords in source table: {total_count}"
            f"\nRecords imported: {imported_count}"
            f"\nTotal records in Django table: {final_count}"
        ))
