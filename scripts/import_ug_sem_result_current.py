"""
Import UG_SEM_result_current from purnea_exm_new dump database to staging.

Usage:
    poetry run python scripts/import_ug_sem_result_current.py
    
    # Or with limit for testing:
    poetry run python manage.py shell -c "exec(open('scripts/import_ug_sem_result_current.py').read()); import_data(limit=1000)"
"""
import os
import sys
import django
import pymysql
from datetime import datetime

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pupumis.settings')
django.setup()

from staging.models import UGSemResultCurrent
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
# (handles columns that start with numbers or have special chars)
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
    'faculty': 'faculty',
    'status': 'status',
    'exam_type_his': 'exam_type_his',
    'exam_type': 'exam_type',
    'maximum_mark': 'maximum_mark',
    'pass_mark': 'pass_mark',
    'mark_secured': 'mark_secured',
    'subject_total_mark': 'subject_total_mark',
    'grace_given': 'grace_given',
    'final_mark': 'final_mark',
    'subject_total_mark_grace': 'subject_total_mark_grace',
    'subject_ca': 'subject_ca',
    'subject_ng': 'subject_ng',
    'subject_ce': 'subject_ce',
    'subject_gp': 'subject_gp',
    'total_gp': 'total_gp',
    'total_ca': 'total_ca',
    'total_ce': 'total_ce',
    'subject_result': 'subject_result',
    'final_result': 'final_result',
    'final_status': 'final_status',
    'grand_total_mark': 'grand_total_mark',
    'total_secured_mark': 'total_secured_mark',
    'total_per': 'total_per',
    'institute_code': 'institute_code',
    'gpa': 'gpa',
    'cgpa': 'cgpa',
    'numrical_let_grad': 'numrical_let_grad',
    'let_grad_sub': 'let_grad_sub',
    'let_grad': 'let_grad',
    'dsc_grad': 'dsc_grad',
    'is_lab_1001': 'is_lab_1001',
    'is_lab_1002': 'is_lab_1002',
    'is_lab_1005': 'is_lab_1005',
    'is_lab_2001': 'is_lab_2001',
    'is_lab_2002': 'is_lab_2002',
    'is_lab_2003': 'is_lab_2003',
    'is_lab_2004': 'is_lab_2004',
    'is_lab_2005': 'is_lab_2005',
    'is_lab_3001': 'is_lab_3001',
    'is_lab_3002': 'is_lab_3002',
    'is_lab_3003': 'is_lab_3003',
    'is_lab_3005': 'is_lab_3005',
    'is_lab_4001': 'is_lab_4001',
    'is_lab_4002': 'is_lab_4002',
    'is_lab_4003': 'is_lab_4003',
    'is_lab_4004': 'is_lab_4004',
    'is_lab': 'is_lab',
    '1st_sem_total_ce': 'sem_1_total_ce',
    '2nd_sem_total_ce': 'sem_2_total_ce',
    '3rd_sem_total_ce': 'sem_3_total_ce',
    '1st_final_result': 'sem_1_final_result',
    'is_grace': 'is_grace',
    'gpa_grace': 'gpa_grace',
    'record_status': 'record_status',
    'final_merit': 'final_merit',
    'final_sheet_status': 'final_sheet_status',
    'student_name_hindi': 'student_name_hindi',
}

BATCH_SIZE = 5000


def import_data(limit=None, clear_existing=False):
    """
    Import data from purnea_exm_new.UG_SEM_result_current to staging.UGSemResultCurrent
    
    Args:
        limit: Optional limit on number of records to import (for testing)
        clear_existing: If True, delete all existing records before import
    """
    print(f"\n{'='*60}")
    print(f"Importing UG_SEM_result_current from purnea_exm_new")
    print(f"{'='*60}\n")
    
    if clear_existing:
        print("🗑️  Clearing existing records...")
        deleted_count = UGSemResultCurrent.objects.all().delete()[0]
        print(f"   Deleted {deleted_count} existing records")
    
    # Connect to source database
    print("📡 Connecting to source database...")
    connection = pymysql.connect(**SOURCE_DB_CONFIG)
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    
    # Count records
    cursor.execute("SELECT COUNT(*) as total FROM UG_SEM_result_current")
    total_in_source = cursor.fetchone()['total']
    print(f"📊 Total records in source: {total_in_source:,}")
    
    # Build query
    query = "SELECT * FROM UG_SEM_result_current"
    if limit:
        query += f" LIMIT {limit}"
        print(f"   (Limited to {limit} records for testing)")
    
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
            
            batch.append(UGSemResultCurrent(**model_data))
            
            # Bulk insert when batch is full
            if len(batch) >= BATCH_SIZE:
                with transaction.atomic():
                    UGSemResultCurrent.objects.bulk_create(batch)
                imported += len(batch)
                batch = []
                
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = imported / elapsed if elapsed > 0 else 0
                print(f"   Imported {imported:,} records... ({rate:.0f} records/sec)")
                
        except Exception as e:
            errors.append(f"Row {row.get('id')}: {str(e)}")
            if len(errors) <= 5:
                print(f"   ⚠️ Error: {str(e)[:100]}")
    
    # Insert remaining batch
    if batch:
        with transaction.atomic():
            UGSemResultCurrent.objects.bulk_create(batch)
        imported += len(batch)
    
    cursor.close()
    connection.close()
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Import Complete")
    print(f"{'='*60}")
    print(f"✅ Records imported: {imported:,}")
    print(f"❌ Errors: {len(errors)}")
    print(f"⏱️  Time: {elapsed:.1f} seconds ({imported/elapsed:.0f} records/sec)" if elapsed > 0 else "")
    print(f"📊 Total in staging now: {UGSemResultCurrent.objects.count():,}")
    print()
    
    return imported


if __name__ == '__main__':
    import_data()
