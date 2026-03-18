"""
Import vocational_result_current from pupdb_old database to staging.

Usage:
    python scripts/vocational_result_current/dump/import_data.py
    
    # Or with limit for testing:
    python manage.py shell -c "exec(open('scripts/vocational_result_current/dump/import_data.py').read()); import_data(limit=1000)"
"""
import os
import sys
import django
import pymysql
from datetime import datetime

# Django setup
# Get the absolute path of the project root (4 levels up from this script: dump -> vocational_result_current -> scripts -> root)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import VocationalResultCurrent
from django.db import transaction

# Source database configuration
SOURCE_DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345',
    'database': 'pupdb_old',
    'charset': 'utf8mb4',
}

# Column mapping: source column name -> model field name
COLUMN_MAPPING = {
    'id': 'source_id',
    'user_id': 'user_id',
    'college_roll_no': 'college_roll_no',
    'college_reg_no': 'college_reg_no',
    'student_name': 'student_name',
    'fathers_name': 'fathers_name',
    'mothers_name': 'mothers_name',
    'semester_code': 'semester_code',
    'batch_code': 'batch_code',
    'session_code': 'session_code',
    'course_code': 'course_code',
    'discipline_code': 'discipline_code',
    'paper_code': 'paper_code',
    'subject_code': 'subject_code',
    'subject_name': 'subject_name',
    'status': 'status',
    'exam_type': 'exam_type',
    'maximum_mark': 'maximum_mark',
    'pass_mark': 'pass_mark',
    'mark_secured': 'mark_secured',
    'subject_total_mark': 'subject_total_mark',
    'subject_result': 'subject_result',
    'final_result': 'final_result',
    'grand_total_mark': 'grand_total_mark',
    'total_secured_mark': 'total_secured_mark',
    'total_per': 'total_per',
    'agreegate': 'agreegate',
    'institute_code': 'institute_code',
    'record_status': 'record_status',
    'grade': 'grade',
    'subject_result_1': 'subject_result_1',
    'subject_result_2': 'subject_result_2',
    'hon': 'hon',
    'student_check': 'student_check',
    'total_secured_mark_1': 'total_secured_mark_1',
    'total_secured_mark_2': 'total_secured_mark_2',
    'grace_chk': 'grace_chk',
    'pra': 'pra',
    'paper_type_code': 'paper_type_code',
    'discipline_code_temp': 'discipline_code_temp',
    'end_term_sum': 'end_term_sum',
    'lab_sum': 'lab_sum',
}

BATCH_SIZE = 5000

def import_data(limit=None, clear_existing=False):
    """
    Import data from pupdb_old.vocational_result_current to staging.VocationalResultCurrent
    """
    print(f"\n{'='*60}")
    print(f"Importing vocational_result_current from pupdb_old")
    print(f"{'='*60}\n")
    
    if clear_existing:
        print("Clearing existing records...")
        deleted_count = VocationalResultCurrent.objects.all().delete()[0]
        print(f"   Deleted {deleted_count} existing records")
    
    # Connect to source database
    print("Connecting to source database...")
    try:
        connection = pymysql.connect(**SOURCE_DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)
    except Exception as e:
        print(f"Connection failed: {e}")
        return
    
    # Count records
    cursor.execute("SELECT COUNT(*) as total FROM vocational_result_current")
    total_in_source = cursor.fetchone()['total']
    print(f"Total records in source: {total_in_source:,}")
    
    # Build query
    query = "SELECT * FROM vocational_result_current"
    if limit:
        query += f" LIMIT {limit}"
        print(f"   (Limited to {limit} records for testing)")
    
    print("\nFetching data from source...")
    cursor.execute(query)
    
    imported = 0
    errors = []
    batch = []
    
    print("Starting import...\n")
    start_time = datetime.now()
    
    for row in cursor:
        try:
            model_data = {}
            for source_col, model_field in COLUMN_MAPPING.items():
                value = row.get(source_col)
                if value is not None:
                    model_data[model_field] = str(value)
                else:
                    model_data[model_field] = None
            
            batch.append(VocationalResultCurrent(**model_data))
            
            if len(batch) >= BATCH_SIZE:
                with transaction.atomic():
                    VocationalResultCurrent.objects.bulk_create(batch)
                imported += len(batch)
                batch = []
                
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = imported / elapsed if elapsed > 0 else 0
                print(f"   Imported {imported:,} records... ({rate:.0f} records/sec)")
                
        except Exception as e:
            errors.append(f"Row {row.get('id')}: {str(e)}")
            if len(errors) <= 5:
                print(f"   Error: {str(e)[:100]}")
    
    if batch:
        with transaction.atomic():
            VocationalResultCurrent.objects.bulk_create(batch)
        imported += len(batch)
    
    cursor.close()
    connection.close()
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n{'='*60}")
    print(f"Import Complete")
    print(f"{'='*60}")
    print(f"Records imported: {imported:,}")
    print(f"Errors: {len(errors)}")
    print(f"Time: {elapsed:.1f} seconds ({imported/elapsed:.0f} records/sec)" if elapsed > 0 else "")
    try:
        print(f"Total in staging now: {VocationalResultCurrent.objects.count():,}")
    except:
        pass
    print()
    
    return imported

if __name__ == '__main__':
    import_data()
