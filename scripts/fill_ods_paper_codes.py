
import os
import sys
import pandas as pd
import django

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import PGResultCurrent

def update_ods_from_db(ods_path):
    print(f"Reading {ods_path}...")
    
    try:
        # Read the ODS file
        df = pd.read_excel(ods_path, engine='odf')
        
        # Clean column names
        original_columns = df.columns.tolist()
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identify Paper Code and Course Name columns
        paper_code_col = None
        course_name_col = None
        
        for col in df.columns:
            clean_col = col.lower().replace(" ", "")
            if clean_col == 'papercode':
                paper_code_col = col
            elif clean_col == 'coursename':
                course_name_col = col
                
        if not paper_code_col:
            print(f"ERROR: 'Paper Code' column not found! Available: {df.columns.tolist()}")
            return
        if not course_name_col:
            print(f"ERROR: 'Course Name' column not found! Available: {df.columns.tolist()}")
            return
            
        print(f"Using '{course_name_col}' for matching and '{paper_code_col}' for updating.")
        
        # Map DB Subjects to Paper Codes
        # Only take records that HAVE a paper_code
        print("Fetching mappings from PGResultCurrent...")
        db_data = PGResultCurrent.objects.filter(paper_code__isnull=False).exclude(paper_code='').values('subject_name', 'paper_code').distinct()
        
        # Create a dictionary for lookup: subject_name_clean -> paper_code
        db_map = {}
        # Also keep a list for fuzzy matching if needed
        db_list = []
        
        for item in db_data:
            s_name = item['subject_name']
            if s_name:
                clean_name = s_name.lower().strip()
                p_code = item['paper_code']
                db_map[clean_name] = p_code
                db_list.append({'name': clean_name, 'code': p_code, 'orig_name': s_name})
                
        print(f"Loaded {len(db_map)} unique subject-paper_code pairs from DB.")
        
        updated_count = 0
        
        # Iterate through ODS rows and update
        for index, row in df.iterrows():
            course_name = str(row[course_name_col]).strip()
            current_code = str(row[paper_code_col]).strip()
            
            # Skip if course name is empty
            if not course_name or course_name.lower() == 'nan':
                continue
                
            # Skip if paper code is already present (Optional: overwrite? User said "add paper code", often implies filling gaps)
            # Assuming we overwrite to ensure accuracy or fill if missing.
            # Let's check for match
            
            clean_course = course_name.lower().strip()
            found_code = None
            match_type = ""
            
            # 1. Exact Match
            if clean_course in db_map:
                found_code = db_map[clean_course]
                match_type = "Exact"
                
            # 2. Fuzzy Containment Match (One way)
            if not found_code:
                # Check if DB name is inside ODS Course Name (e.g. ODS: "Hist of India (Part 1)", DB: "Hist of India")
                for item in db_list:
                    if item['name'] in clean_course and len(item['name']) > 5:
                        found_code = item['code']
                        match_type = "DB-in-ODS"
                        break
            
            # 3. Fuzzy Containment Match (Other way)
            if not found_code:
                # Check if ODS Course Name is inside DB name (e.g. ODS: "Hist of India", DB: "History of India (PG)")
                for item in db_list:
                    if clean_course in item['name'] and len(clean_course) > 5:
                        found_code = item['code']
                        match_type = "ODS-in-DB"
                        break
            
            if found_code:
                # Update the cell
                # Note: 'nan' check is needed because read_excel might import empty cells as nan float
                if found_code != current_code and current_code.lower() != 'nan':
                     # print(f"Updating '{course_name}': {current_code} -> {found_code} ({match_type})")
                     pass
                
                df.at[index, paper_code_col] = found_code
                updated_count += 1
            else:
                # print(f"No match for '{course_name}'")
                pass

        print(f"Updated {updated_count} rows in dataframe.")
        
        # Restore original column names if possible or just save
        # Saving...
        output_path = ods_path # Overwrite original
        print(f"Saving to {output_path}...")
        
        # Using odf writer
        with pd.ExcelWriter(output_path, engine='odf') as writer:
            df.to_excel(writer, index=False)
            
        print("Done!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    ods_file = 'courses_data/pg/structureofcourse.ods'
    full_path = os.path.join(BASE_DIR, ods_file)
    update_ods_from_db(full_path)
