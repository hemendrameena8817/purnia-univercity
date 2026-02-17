import pymysql
import os
from decouple import config

def get_columns():
    try:
        connection = pymysql.connect(
            host=config('DB_HOST', default='localhost'),
            user=config('DB_USER', default='root'),
            password=config('DB_PASSWORD', default='root'),
            database='purnea_exm_new',
            port=int(config('DB_PORT', default=3306))
        )
        with connection.cursor() as cursor:
            cursor.execute("DESCRIBE UG_result_current")
            columns = cursor.fetchall()
            for col in columns:
                print(col[0])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    get_columns()
