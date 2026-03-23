# -*- coding: utf-8 -*-
"""
Transfer all data from llb_result_current to StagingLLBResultCurrent

Run this:
poetry run python scripts/llb/dump/dump_to_staging.py
"""

import os
import sys
import django
from django.db import transaction

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

def transfer_data():
    """Transfer all data from external DB to staging"""
    
    try:
        import pymysql
        
        print("Connecting to purnea_exm_new database...")
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='root',
            database='purnea_exm_new',
            port=3306
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM llb_result_current")
            total_count = cursor.fetchone()[0]
            print(f"Total records: {total_count}")
            
            cursor.execute("SELECT * FROM llb_result_current")
            records = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            print(f"Columns: {len(column_names)}")
            
        connection.close()
        
        from staging.models import StagingLLBResultCurrent
        
        # Clear existing
        existing = StagingLLBResultCurrent.objects.count()
        if existing > 0:
            print(f"Clearing {existing} existing records...")
            StagingLLBResultCurrent.objects.all().delete()
        
        # Transfer in batches
        batch_size = 500
        transferred = 0
        
        print("Transferring data...")
        with transaction.atomic():
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                staging_records = []
                for record in batch:
                    record_dict = dict(zip(column_names, record))
                    
                    staging_record = StagingLLBResultCurrent(
                        source_id=str(record_dict.get('id', '')),
                        user_id=str(record_dict.get('user_id', '')),
                        college_roll_no=str(record_dict.get('college_roll_no', '')),
                        college_reg_no=str(record_dict.get('college_reg_no', '')),
                        student_name=str(record_dict.get('student_name', '')),
                        fathers_name=str(record_dict.get('fathers_name', '')),
                        mothers_name=str(record_dict.get('mothers_name', '')),
                        semester_code=str(record_dict.get('semester_code', '')),
                        batch_code=str(record_dict.get('batch_code', '')),
                        session_code=str(record_dict.get('session_code', '')),
                        course_code=str(record_dict.get('course_code', '')),
                        discipline_code=str(record_dict.get('discipline_code', '')),
                        paper_code=str(record_dict.get('paper_code', '')),
                        subject_code=str(record_dict.get('subject_code', '')),
                        subject_name=str(record_dict.get('subject_name', '')),
                        status=str(record_dict.get('status', '')),
                        exam_type=str(record_dict.get('exam_type', '')),
                        maximum_mark=str(record_dict.get('maximum_mark', '')),
                        pass_mark=str(record_dict.get('pass_mark', '')),
                        mark_secured=str(record_dict.get('mark_secured', '')),
                        mark_secured_his=str(record_dict.get('mark_secured_his', '')),
                        subject_total_mark=str(record_dict.get('subject_total_mark', '')),
                        subject_result=str(record_dict.get('subject_result', '')),
                        final_result=str(record_dict.get('final_result', '')),
                        grand_total_mark=str(record_dict.get('grand_total_mark', '')),
                        total_secured_mark=str(record_dict.get('total_secured_mark', '')),
                        total_secured_mark_his=str(record_dict.get('total_secured_mark_his', '')),
                        total_per=str(record_dict.get('total_per', '')),
                        agreegate=str(record_dict.get('agreegate', '')),
                        institute_code=str(record_dict.get('institute_code', '')),
                        record_status=record_dict.get('record_status'),
                        grade=str(record_dict.get('grade', '')),
                        sub_grace_chk=str(record_dict.get('sub_grace_chk', '')),
                        sub_wise_grace_chk=str(record_dict.get('sub_wise_grace_chk', '')),
                        total_grace_chk=str(record_dict.get('total_grace_chk', '')),
                        final_grace_list=str(record_dict.get('final_grace_list', '')),
                        grace_chk=str(record_dict.get('grace_chk', '')),
                        hon=str(record_dict.get('hon', '')),
                        spfc_chk=str(record_dict.get('spfc_chk', '')),
                        previous_course_code=str(record_dict.get('previous_course_code', '')),
                    )
                    staging_records.append(staging_record)
                
                StagingLLBResultCurrent.objects.bulk_create(staging_records)
                transferred += len(staging_records)
                print(f"Progress: {transferred}/{total_count}")
        
        final_count = StagingLLBResultCurrent.objects.count()
        print(f"\nCompleted!")
        print(f"Total transferred: {final_count}")
        
        if final_count == total_count:
            print("All records transferred successfully!")
        else:
            print(f"Warning: Expected {total_count}, got {final_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    transfer_data()
