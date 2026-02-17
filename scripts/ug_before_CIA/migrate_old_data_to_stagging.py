import os
import sys
import django
import pymysql
from decouple import config

# Set up Django environment
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import UGResultCurrent, UGSemResultCurrent

def migrate_ug_result_current():
    # External database credentials
    ext_db_config = {
        'host': config('DB_HOST', default='localhost'),
        'user': config('DB_USER', default='root'),
        'password': config('DB_PASSWORD', default='root'),
        'database': 'purnea_exm_new',
        'port': int(config('DB_PORT', default=3306)),
        'cursorclass': pymysql.cursors.DictCursor
    }

    try:
        print("Connecting to external database for UG_result_current...")
        connection = pymysql.connect(**ext_db_config)
        
        with connection.cursor() as cursor:
            print("Fetching data from UG_result_current...")
            cursor.execute("SELECT * FROM UG_result_current")
            
            # Use fetchmany to avoid loading everything into memory at once
            batch_size = 1000
            count = 0
            
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                
                objects_to_create = []
                for row in rows:
                    # Map SQL row fields to Django model fields
                    # We use .get(field_name) to handle missing fields safely
                    obj = UGResultCurrent(
                        source_id=row.get('id'),
                        user_id=row.get('user_id'),
                        college_roll_no=row.get('college_roll_no'),
                        college_reg_no=row.get('college_reg_no'),
                        student_name=row.get('student_name'),
                        fathers_name=row.get('fathers_name'),
                        mothers_name=row.get('mothers_name'),
                        semester_code=row.get('semester_code'),
                        batch_code=row.get('batch_code'),
                        session_code=row.get('session_code'),
                        course_code=row.get('course_code'),
                        discipline_code=row.get('discipline_code'),
                        temp_paper_code=row.get('temp_paper_code'),
                        paper_code_correction=row.get('paper_code_correction'),
                        subject_code_correction=row.get('subject_code_correction'),
                        paper_code=row.get('paper_code'),
                        subject_code=row.get('subject_code'),
                        subject_name=row.get('subject_name'),
                        theory=row.get('theory'),
                        sessional=row.get('sessional'),
                        status=row.get('status'),
                        pra=row.get('pra'),
                        exam_type=row.get('exam_type'),
                        maximum_mark=row.get('maximum_mark'),
                        pass_mark=row.get('pass_mark'),
                        mark_secured=row.get('mark_secured'),
                        mark_secured_history=row.get('mark_secured_history'),
                        subject_total_mark=row.get('subject_total_mark'),
                        subject_result=row.get('subject_result'),
                        subject_result_1=row.get('subject_result_1'),
                        subject_result_2=row.get('subject_result_2'),
                        final_result=row.get('final_result'),
                        grand_total_mark=row.get('grand_total_mark'),
                        total_secured_mark_1=row.get('total_secured_mark_1'),
                        total_secured_mark_2=row.get('total_secured_mark_2'),
                        total_secured_mark=row.get('total_secured_mark'),
                        hon=row.get('hon'),
                        total_per=row.get('total_per'),
                        agreegate=row.get('agreegate'),
                        institute_code=row.get('institute_code'),
                        record_status_check=row.get('record_status_check'),
                        record_status=row.get('record_status'),
                        grade=row.get('grade'),
                        student_check=row.get('student_check'),
                        grace_chk=row.get('grace_chk'),
                        remark=row.get('remark'),
                        paper_type_code=row.get('paper_type_code'),
                        sub_reult_com=row.get('sub_reult_com'),
                        ExRegular_chk=row.get('ExRegular_chk'),
                        subject_count=row.get('subject_count'),
                        exam_type_his=row.get('exam_type_his'),
                        aggregate_hindi=row.get('aggregate_hindi'),
                    )
                    objects_to_create.append(obj)
                
                # Bulk create for efficiency
                UGResultCurrent.objects.bulk_create(objects_to_create)
                count += len(objects_to_create)
                print(f"Migrated {count} records from UG_result_current...")
                
        print("UG_result_current migration completed successfully.")

    except Exception as e:
        print(f"Error during UG_result_current migration: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

def migrate_ug_sem_result_current():
    # External database credentials
    ext_db_config = {
        'host': config('DB_HOST', default='localhost'),
        'user': config('DB_USER', default='root'),
        'password': config('DB_PASSWORD', default='root'),
        'database': 'purnea_exm_new',
        'port': int(config('DB_PORT', default=3306)),
        'cursorclass': pymysql.cursors.DictCursor
    }

    try:
        print("Connecting to external database for ug_sem_result_current...")
        connection = pymysql.connect(**ext_db_config)
        
        with connection.cursor() as cursor:
            print("Fetching data from ug_sem_result_current...")
            cursor.execute("SELECT * FROM ug_sem_result_current")
            
            # Use fetchmany to avoid loading everything into memory at once
            batch_size = 1000
            count = 0
            
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                
                objects_to_create = []
                for row in rows:
                    obj = UGSemResultCurrent(
                        source_id=row.get('id'),
                        user_id=row.get('user_id'),
                        college_roll_no=row.get('college_roll_no'),
                        college_reg_no=row.get('college_reg_no'),
                        student_name=row.get('student_name'),
                        fathers_name=row.get('fathers_name'),
                        mothers_name=row.get('mothers_name'),
                        semester_code=row.get('semester_code'),
                        batch_code=row.get('batch_code'),
                        session_code=row.get('session_code'),
                        course_code=row.get('course_code'),
                        discipline_code=row.get('discipline_code'),
                        paper_code=row.get('paper_code'),
                        subject_code=row.get('subject_code'),
                        subject_name=row.get('subject_name'),
                        faculty=row.get('faculty'),
                        status=row.get('status'),
                        exam_type_his=row.get('exam_type_his'),
                        exam_type=row.get('exam_type'),
                        maximum_mark=row.get('maximum_mark'),
                        pass_mark=row.get('pass_mark'),
                        mark_secured=row.get('mark_secured'),
                        subject_total_mark=row.get('subject_total_mark'),
                        grace_given=row.get('grace_given'),
                        final_mark=row.get('final_mark'),
                        subject_total_mark_grace=row.get('subject_total_mark_grace'),
                        subject_ca=row.get('subject_ca'),
                        subject_ng=row.get('subject_ng'),
                        subject_ce=row.get('subject_ce'),
                        subject_gp=row.get('subject_gp'),
                        total_gp=row.get('total_gp'),
                        total_ca=row.get('total_ca'),
                        total_ce=row.get('total_ce'),
                        subject_result=row.get('subject_result'),
                        final_result=row.get('final_result'),
                        final_status=row.get('final_status'),
                        grand_total_mark=row.get('grand_total_mark'),
                        total_secured_mark=row.get('total_secured_mark'),
                        total_per=row.get('total_per'),
                        institute_code=row.get('institute_code'),
                        gpa=row.get('gpa'),
                        cgpa=row.get('cgpa'),
                        numrical_let_grad=row.get('numrical_let_grad'),
                        let_grad_sub=row.get('let_grad_sub'),
                        let_grad=row.get('let_grad'),
                        dsc_grad=row.get('dsc_grad'),
                        is_lab_1001=row.get('is_lab_1001'),
                        is_lab_1002=row.get('is_lab_1002'),
                        is_lab_1005=row.get('is_lab_1005'),
                        is_lab_2001=row.get('is_lab_2001'),
                        is_lab_2002=row.get('is_lab_2002'),
                        is_lab_2003=row.get('is_lab_2003'),
                        is_lab_2004=row.get('is_lab_2004'),
                        is_lab_2005=row.get('is_lab_2005'),
                        is_lab_3001=row.get('is_lab_3001'),
                        is_lab_3002=row.get('is_lab_3002'),
                        is_lab_3003=row.get('is_lab_3003'),
                        is_lab_3005=row.get('is_lab_3005'),
                        is_lab_4001=row.get('is_lab_4001'),
                        is_lab_4002=row.get('is_lab_4002'),
                        is_lab_4003=row.get('is_lab_4003'),
                        is_lab_4004=row.get('is_lab_4004'),
                        is_lab=row.get('is_lab'),
                        sem_1_total_ce=row.get('1st_sem_total_ce'),
                        sem_2_total_ce=row.get('2nd_sem_total_ce'),
                        sem_3_total_ce=row.get('3rd_sem_total_ce'),
                        sem_1_final_result=row.get('1st_final_result'),
                        is_grace=row.get('is_grace'),
                        gpa_grace=row.get('gpa_grace'),
                        record_status=row.get('record_status'),
                        final_merit=row.get('final_merit'),
                        final_sheet_status=row.get('final_sheet_status'),
                        student_name_hindi=row.get('student_name_hindi'),
                    )
                    objects_to_create.append(obj)
                
                # Bulk create for efficiency
                UGSemResultCurrent.objects.bulk_create(objects_to_create)
                count += len(objects_to_create)
                print(f"Migrated {count} records from ug_sem_result_current...")
                
        print("ug_sem_result_current migration completed successfully.")

    except Exception as e:
        print(f"Error during ug_sem_result_current migration: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    # Optional: Clear existing records before migration
    # UGResultCurrent.objects.all().delete()
    # UGSemResultCurrent.objects.all().delete()
    
    migrate_ug_result_current()
    migrate_ug_sem_result_current()

