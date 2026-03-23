import pymysql
import os
from decouple import config

def get_table_structure():
    try:
        connection = pymysql.connect(
            host=config('DB_HOST', default='localhost'),
            user=config('DB_USER', default='root'),
            password=config('DB_PASSWORD', default='root'),
            database='purnea_exm_new',
            port=int(config('DB_PORT', default=3306))
        )
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'llb_result_current'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("❌ Table 'llb_result_current' not found")
                
                # Show available tables
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                print("\nAvailable tables with 'llb' or 'result':")
                for table in tables:
                    if 'llb' in table[0].lower() or 'result' in table[0].lower():
                        print(f"  - {table[0]}")
                return
            
            print("✅ Table 'llb_result_current' found")
            
            # Get detailed column information
            cursor.execute("DESCRIBE llb_result_current")
            columns = cursor.fetchall()
            
            print(f"\n📊 Table Structure:")
            print(f"Total columns: {len(columns)}")
            print("-" * 80)
            
            for i, col in enumerate(columns, 1):
                field = col[0]
                type_info = col[1]
                null_allowed = "YES" if col[2] == "YES" else "NO"
                key = col[3] if col[3] else ""
                default = col[4] if col[4] else ""
                extra = col[5] if col[5] else ""
                
                print(f"{i:2d}. {field:30s} {type_info:20s} NULL:{null_allowed:3s} {key:10s} {default:10s} {extra}")
            
            # Get record count
            cursor.execute("SELECT COUNT(*) FROM llb_result_current")
            count = cursor.fetchone()[0]
            print(f"\n📈 Total records: {count}")
            
            # Show sample data
            if count > 0:
                cursor.execute("SELECT * FROM llb_result_current LIMIT 3")
                records = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                
                print(f"\n📋 Sample Data (first 3 records):")
                print("-" * 80)
                
                for record_idx, record in enumerate(records, 1):
                    print(f"\nRecord {record_idx}:")
                    for i, (col_name, value) in enumerate(zip(column_names, record)):
                        if value:  # Only show non-null values for readability
                            print(f"  {col_name:30s}: {value}")
                    if record_idx < len(records):
                        print("-" * 40)
                        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    get_table_structure()
