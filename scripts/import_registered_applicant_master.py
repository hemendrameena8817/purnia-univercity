"""
Import registered_applicant_master from purnea_exm_new dump database to staging.

Usage:
    poetry run python scripts/import_registered_applicant_master.py
    
This script will:
1. Delete all existing RegisteredApplicantMaster records
2. Import all data from purnea_exm_new.registered_applicant_master
"""
import os
import sys
import django
import pymysql
from datetime import datetime

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import RegisteredApplicantMaster
from django.db import transaction

# Source database configuration (dump database)
SOURCE_DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Locus@1234',
    'database': 'purnea_exm_new',
    'charset': 'utf8mb4',
}

# Column mapping: dump column name -> model field name
COLUMN_MAPPING = {
    'id': 'csv_id',
    'reg_no': 'reg_no',
    'sams_id': 'sams_id',
    'college_roll_no': 'college_roll_no',
    'college_reg_no': 'college_reg_no',
    'center': 'center',
    '3rdcenter2017_old': 'center2017_old',
    '3rdcenter2017': 'center2017',
    'roll_no': 'roll_no',
    'result': 'result',
    'exam_type_code': 'exam_type_code',
    'student_name': 'student_name',
    'fathers_name': 'fathers_name',
    'mothers_name': 'mothers_name',
    'appl_no': 'appl_no',
    'course_code': 'course_code',
    'discipline_code': 'discipline_code',
    'semester_code': 'semester_code',
    'batch_code': 'batch_code',
    'syllabus_year': 'syllabus_year',
    'institute_code': 'institute_code',
    'session_code': 'session_code',
    'phone': 'phone',
    'dob': 'dob',
    'gender': 'gender',
    'category': 'category',
    'Approve': 'approve',
    'full_address': 'full_address',
    'institute_pub_status': 'institute_pub_status',
    'student_pub_status': 'student_pub_status',
    'last_board': 'last_board',
    'aadhar_card_no': 'aadhar_card_no',
    'created_by': 'created_by',
    'created_on': 'created_on',
    'updated_by': 'updated_by',
    'updated_on': 'updated_on',
    'record_status': 'record_status',
    'last_updated': 'last_updated',
    'payment_status': 'payment_status',
    'is_sem': 'is_sem',
    'ABC_Id': 'abc_id',
    'Addmision_date': 'addmision_date',
    'api_status': 'api_status',
}

BATCH_SIZE = 5000


def import_data(limit=None):
    """
    Import data from purnea_exm_new.registered_applicant_master to staging.RegisteredApplicantMaster
    
    Args:
        limit: Optional limit on number of records to import (for testing)
    """
    print(f"\n{'='*80}")
    print(f"Importing registered_applicant_master from purnea_exm_new")
    print(f"{'='*80}\n")
    
    # Always clear existing records as per requirement
    print("🗑️  Clearing ALL existing records...")
    deleted_count = RegisteredApplicantMaster.objects.all().delete()[0]
    print(f"   ✅ Deleted {deleted_count:,} existing records\n")
    
    # Connect to source database
    print("📡 Connecting to source database...")
    try:
        connection = pymysql.connect(**SOURCE_DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        print("   ✅ Connected successfully\n")
    except Exception as e:
        print(f"   ❌ Connection failed: {str(e)}")
        return 0
    
    # Count records
    cursor.execute("SELECT COUNT(*) as total FROM registered_applicant_master")
    total_in_source = cursor.fetchone()['total']
    print(f"📊 Total records in source: {total_in_source:,}")
    
    # Build query
    query = "SELECT * FROM registered_applicant_master"
    if limit:
        query += f" LIMIT {limit}"
        print(f"   (Limited to {limit:,} records for testing)")
    
    print("\n🔄 Fetching data from source...")
    cursor.execute(query)
    
    imported = 0
    errors = []
    batch = []
    
    print("🚀 Starting import...\n")
    start_time = datetime.now()
    
    for row in cursor:
        try:
            # Map columns
            model_data = {}
            for source_col, model_field in COLUMN_MAPPING.items():
                value = row.get(source_col)
                # Convert to string if not None
                if value is not None:
                    model_data[model_field] = str(value)
                else:
                    model_data[model_field] = None
            
            batch.append(RegisteredApplicantMaster(**model_data))
            
            # Bulk insert when batch is full
            if len(batch) >= BATCH_SIZE:
                with transaction.atomic():
                    RegisteredApplicantMaster.objects.bulk_create(batch, ignore_conflicts=True)
                imported += len(batch)
                batch = []
                
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = imported / elapsed if elapsed > 0 else 0
                print(f"   ✅ Imported {imported:,} records... ({rate:.0f} records/sec)")
                
        except Exception as e:
            errors.append(f"Row {row.get('id')}: {str(e)}")
            if len(errors) <= 5:
                print(f"   ⚠️ Error: {str(e)[:100]}")
    
    # Insert remaining batch
    if batch:
        with transaction.atomic():
            RegisteredApplicantMaster.objects.bulk_create(batch, ignore_conflicts=True)
        imported += len(batch)
    
    cursor.close()
    connection.close()
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Summary
    print(f"\n{'='*80}")
    print(f"Import Complete")
    print(f"{'='*80}")
    print(f"✅ Records imported: {imported:,}")
    print(f"❌ Errors: {len(errors)}")
    if elapsed > 0:
        print(f"⏱️  Time: {elapsed:.1f} seconds ({imported/elapsed:.0f} records/sec)")
    print(f"📊 Total in staging now: {RegisteredApplicantMaster.objects.count():,}")
    print(f"{'='*80}\n")
    
    if errors and len(errors) <= 10:
        print("\n⚠️ Error details:")
        for error in errors[:10]:
            print(f"   - {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")
    
    return imported


if __name__ == '__main__':
    import_data()
