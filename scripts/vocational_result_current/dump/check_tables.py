import pymysql
import os
from decouple import config

def check_tables():
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='12345',
            database='pupdb_old',
            port=3306
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
