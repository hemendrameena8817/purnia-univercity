import pymysql
import os
from decouple import config

def get_columns():
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='12345',
            database='pupdb_old',
            port=3306
        )
        with connection.cursor() as cursor:
            cursor.execute("DESCRIBE vocational_result_current")
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
