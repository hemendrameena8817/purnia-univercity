import pymysql
import os
from decouple import config
import json

def get_full_describe():
    try:
        connection = pymysql.connect(
            host=config('DB_HOST', default='localhost'),
            user=config('DB_USER', default='root'),
            password=config('DB_PASSWORD', default='root'),
            database='purnea_exm_new',
            port=int(config('DB_PORT', default=3306))
        )
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("DESCRIBE UG_result_current")
            columns = cursor.fetchall()
            print(json.dumps(columns, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()


if __name__ == "__main__":
    import sys
    table = sys.argv[1] if len(sys.argv) > 1 else "UG_result_current"
    
    try:
        connection = pymysql.connect(
            host=config('DB_HOST', default='localhost'),
            user=config('DB_USER', default='root'),
            password=config('DB_PASSWORD', default='root'),
            database='purnea_exm_new',
            port=int(config('DB_PORT', default=3306))
        )
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            print(json.dumps(columns, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

