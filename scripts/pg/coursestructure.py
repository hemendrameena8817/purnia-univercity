import os
import sys
import re
import pandas as pd
from decimal import Decimal
import django
# python scripts/pg/coursestructure.py
# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.models import PGCourseStructure, PGDepartment

def run(file_path=None):
    import subprocess
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Resolve file: use provided path or auto-detect .xlsx/.ods
    engine = None
    if not file_path:
        for fname, eng in [('structureofcourse.xlsx', 'openpyxl'), ('structureofcourse.ods', 'odf')]:
            candidate = os.path.join(base_dir, 'courses_data', 'pg', fname)
            if os.path.exists(candidate):
                file_path = candidate
                engine = eng
                break
        if not file_path:
            print("File not found. Use --file /path/to/structureofcourse.ods")
            return

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    # Auto-detect actual format (handles ODS renamed as .xlsx)
    result = subprocess.run(['file', file_path], capture_output=True, text=True)
    engine = 'odf' if 'OpenDocument' in result.stdout else 'openpyxl'

    print(f"Reading file: {file_path} (engine: {engine})")

    try:
        df = pd.read_excel(file_path, engine=engine)
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        print("Columns found:", df.columns.tolist())
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Map ODS columns to standardized keys
    col_map = {}
    for col in df.columns:
        c_lower = col.lower().replace(" ", "").replace(".", "")
        if 'coursename' in c_lower: 
            col_map['course_name'] = col
        elif 'semester' in c_lower: 
            col_map['semester'] = col
        elif 'department' in c_lower: 
            col_map['department'] = col
        elif 'totalcredits' in c_lower: 
            col_map['max_credit'] = col
        elif 'credits2' in c_lower: 
            col_map['effective_credit'] = col
        elif 'theorymaxmarks' in c_lower: 
            col_map['theory_max'] = col
        elif 'ciamaxmarks' in c_lower: 
            col_map['cia_max'] = col
        elif 'papercode' in c_lower: 
            col_map['paper_code'] = col
        elif 'coursecode' in c_lower: 
            col_map['course_code'] = col
        # Handle Min Marks columns - need to check exact column name
        elif col.strip() == 'Min Marks':
            col_map['theory_min'] = col
        elif col.strip() == 'Min Marks.1':
            col_map['cia_min'] = col

    print("Column Mapping:", col_map)
    print("\nProcessing courses...")

    count_created = 0
    count_skipped = 0

    for index, row in df.iterrows():
        # Extract basic fields
        course_name = row.get(col_map.get('course_name'))
        if pd.isna(course_name) or str(course_name).strip() == "":
            continue
        course_name = str(course_name).strip()

        dept_name = row.get(col_map.get('department'))
        semester = row.get(col_map.get('semester'))
        course_code = row.get(col_map.get('course_code'))
        paper_code = row.get(col_map.get('paper_code'))
        
        # Handle Paper Code (convert float 101.0 to "101")
        if not pd.isna(paper_code):
            paper_code = str(paper_code).strip()
            if paper_code.endswith(".0"):
                 paper_code = paper_code[:-2]
        else:
            paper_code = None

        if not pd.isna(course_code):
            course_code = str(course_code).strip()
        else:
            course_code = None

        # Clean Semester
        if not pd.isna(semester):
            semester = str(semester).strip()

        # Find Department
        department = None
        if not pd.isna(dept_name):
            dept_name = str(dept_name).strip()
            department = PGDepartment.objects.filter(name__iexact=dept_name).first()
            if not department:
                 print(f"  WARNING: Department '{dept_name}' not found for course '{course_name}'. Skipping.")
                 continue
        
        # Credits
        max_credit = 0
        if 'max_credit' in col_map and not pd.isna(row.get(col_map['max_credit'])):
            try:
                max_credit = int(float(row[col_map['max_credit']]))
            except:
                max_credit = 0
        
        # Effective Credit (from Credits2 column)
        effective_credit = 0
        if 'effective_credit' in col_map and not pd.isna(row.get(col_map['effective_credit'])):
            try:
                effective_credit = int(float(row[col_map['effective_credit']]))
            except:
                effective_credit = 0

        # Marks
        theory_max = Decimal(0)
        theory_min = Decimal(0)
        cia_max = Decimal(0)
        cia_min = Decimal(0)

        if 'theory_max' in col_map and not pd.isna(row[col_map['theory_max']]):
            try: theory_max = Decimal(str(row[col_map['theory_max']]))
            except: pass
        
        if 'theory_min' in col_map and not pd.isna(row[col_map['theory_min']]):
            try: theory_min = Decimal(str(row[col_map['theory_min']]))
            except: pass

        if 'cia_max' in col_map and not pd.isna(row[col_map['cia_max']]):
            try: cia_max = Decimal(str(row[col_map['cia_max']]))
            except: pass
            
        if 'cia_min' in col_map and not pd.isna(row[col_map['cia_min']]):
            try: cia_min = Decimal(str(row[col_map['cia_min']]))
            except: pass

        # Determine Course Type
        course_type = "CC" # Default
        if course_code:
            match = re.match(r'([A-Z]+)', course_code)
            if match:
                course_type = match.group(1)

        # Detect Practical
        is_practical = False
        practical_pattern = re.compile(r'practical|lab\b|practical\s*-\s*[IVX]+|practical\s*-\s*\d+', re.IGNORECASE)
        if practical_pattern.search(course_name) or 'practical' in course_name.lower():
            is_practical = True

        # Define Labels
        # If practical, we might want to use "CIA Practical" and "ESE Practical"? 
        # For now, sticking to standard CIA Theory / ESE Theory but using the correct marks columns.
        # If user explicitly wants "Practical" labels, we can adjust. 
        # Standard convention often separates Theory and Practical courses.
        
        labels_config = []
        
        # CIA
        labels_config.append({
            'name': 'CIA Practical' if is_practical else 'CIA Theory',
            'max_marks': cia_max,
            'min_marks': cia_min,
            'max_credit': max_credit, # Usually credit is for the whole course, or split? assigning full credit to each entry might be duplicated. 
                                     # Usually structure distinct entries share the credit or one has it. 
                                     # Let's assign max_credit to both for now as reference.
            'effective_credit': effective_credit
        })
        
        # ESE
        labels_config.append({
            'name': 'ESE Practical' if is_practical else 'ESE Theory',
            'max_marks': theory_max,
            'min_marks': theory_min,
            'max_credit': max_credit,
            'effective_credit': effective_credit
        })

        for config in labels_config:
            # Check for duplicates
            exists = PGCourseStructure.objects.filter(
                department=department,
                course_name=course_name,
                semester=semester,
                label=config['name'],
                code=course_code
            ).exists()

            if exists:
                # print(f"  Entry exists for {course_name} - {config['name']}. Skipping.")
                count_skipped += 1
                
                # Check if we should update existing?
                # For now, just skipping as per original script behavior roughly.
                # But if we want to populate missing fields (paper_code, marks), we might need to update.
                # Let's try to UPDATE if it exists to ensure new fields are populated.
                entry = PGCourseStructure.objects.get(
                    department=department,
                    course_name=course_name,
                    semester=semester,
                    label=config['name'],
                    code=course_code
                )
                updated = False
                
                # Always update paper_code if available from ODS
                if paper_code and entry.paper_code != paper_code:
                    entry.paper_code = paper_code
                    updated = True
                
                # Always update max_marks if available and different
                if config['max_marks'] > 0 and entry.max_marks != config['max_marks']:
                    entry.max_marks = config['max_marks']
                    updated = True
                
                # Always update min_marks if available and different
                if config['min_marks'] > 0 and entry.min_marks != config['min_marks']:
                    entry.min_marks = config['min_marks']
                    updated = True
                
                # Always update max_credit if available and different
                if max_credit > 0 and entry.max_credit != max_credit:
                    entry.max_credit = max_credit
                    updated = True
                
                # Always update effective_credit if available and different (including 0 for non-credit courses)
                if 'effective_credit' in col_map and entry.effective_credit != effective_credit:
                    entry.effective_credit = effective_credit
                    updated = True
                
                if updated:
                    entry.save()
                    print(f"✓ Updated: {course_name[:40]:40} | {config['name']:15} | Paper: {paper_code:5} | Credit: {config['max_credit']:2} | Eff Credit: {config['effective_credit']:2} | Max: {config['max_marks']:5} | Min: {config['min_marks']:5}")
                
                
                continue

            PGCourseStructure.objects.create(
                department=department,
                course_name=course_name,
                course_short_name=None,
                course_type=course_type,
                code=course_code,
                paper_code=paper_code,
                course_code=course_code,
                max_credit=config['max_credit'],
                effective_credit=config['effective_credit'],
                max_marks=config['max_marks'],
                min_marks=config['min_marks'],
                label=config['name'],
                semester=semester
            )
            count_created += 1
            print(f"✓ Created: {course_name} | {config['name']} | Paper: {paper_code} | Credit: {config['max_credit']} | Eff Credit: {config['effective_credit']} | Max: {config['max_marks']} | Min: {config['min_marks']}")

    print(f"Done. Created: {count_created}, Skipped/Updated: {count_skipped}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Import PG Course Structure')
    parser.add_argument('--file', type=str, default=None, help='Path to .ods or .xlsx file')
    args = parser.parse_args()
    run(file_path=args.file)
