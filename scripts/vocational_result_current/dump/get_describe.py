import pymysql
import os
from decouple import config
import json
import sys

def get_full_describe(table="vocational_result_current"):
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='12345',
            database='pupdb_old',
            port=3306
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


if __name__ == "__main__":
    table_name = sys.argv[1] if len(sys.argv) > 1 else "vocational_result_current"
    get_full_describe(table_name)
