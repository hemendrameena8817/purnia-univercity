import os
import sys
import django
import pymysql

# Set up Django environment
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import VocationalResultCurrent

def migrate_vocational_result_current():
    # Source database configuration
    SOURCE_DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '12345',
        'database': 'pupdb_old',
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    try:
        print("Connecting to external database for vocational_result_current...")
        connection = pymysql.connect(**SOURCE_DB_CONFIG)
        
        with connection.cursor() as cursor:
            print("Fetching data from vocational_result_current...")
            cursor.execute("SELECT * FROM vocational_result_current")
            
            batch_size = 1000
            count = 0
            
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                
                objects_to_create = []
                for row in rows:
                    obj = VocationalResultCurrent(
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
                        status=row.get('status'),
                        exam_type=row.get('exam_type'),
                        maximum_mark=row.get('maximum_mark'),
                        pass_mark=row.get('pass_mark'),
                        mark_secured=row.get('mark_secured'),
                        subject_total_mark=row.get('subject_total_mark'),
                        subject_result=row.get('subject_result'),
                        final_result=row.get('final_result'),
                        grand_total_mark=row.get('grand_total_mark'),
                        total_secured_mark=row.get('total_secured_mark'),
                        total_per=row.get('total_per'),
                        agreegate=row.get('agreegate'),
                        institute_code=row.get('institute_code'),
                        record_status=row.get('record_status'),
                        grade=row.get('grade'),
                        subject_result_1=row.get('subject_result_1'),
                        subject_result_2=row.get('subject_result_2'),
                        hon=row.get('hon'),
                        student_check=row.get('student_check'),
                        total_secured_mark_1=row.get('total_secured_mark_1'),
                        total_secured_mark_2=row.get('total_secured_mark_2'),
                        grace_chk=row.get('grace_chk'),
                        pra=row.get('pra'),
                        paper_type_code=row.get('paper_type_code'),
                        discipline_code_temp=row.get('discipline_code_temp'),
                        end_term_sum=row.get('end_term_sum'),
                        lab_sum=row.get('lab_sum'),
                    )
                    objects_to_create.append(obj)
                
                VocationalResultCurrent.objects.bulk_create(objects_to_create)
                count += len(objects_to_create)
                print(f"Migrated {count} records from vocational_result_current...")
                
        print("vocational_result_current migration completed successfully.")

    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    # Optional: Clear existing records before migration
    # VocationalResultCurrent.objects.all().delete()
    migrate_vocational_result_current()
