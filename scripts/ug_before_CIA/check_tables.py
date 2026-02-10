import pymysql
import os
from decouple import config

def check_tables():
    try:
        connection = pymysql.connect(
            host=config('DB_HOST', default='localhost'),
            user=config('DB_USER', default='root'),
            password=config('DB_PASSWORD', default='root'),
            database='purnea_exm_new',
            port=int(config('DB_PORT', default=3306))
        )
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            for table in tables:
                print(table[0])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    check_tables()
