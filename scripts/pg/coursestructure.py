import os
import sys
import zipfile
import re
import xml.etree.ElementTree as ET
from decimal import Decimal
import django
# ~/.pyenv/versions/pup-umis/bin/python scripts/pg/coursestructure.py
# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.models import PGCourseStructure, PGDepartment

def run():
    # Adjusted path relative to project root since we are running from project root effectively or handling path carefully
    # If running from scripts/pg/, the path to courses_data is ../../courses_data/
    # But usually we run from root. Let's assume absolute path or relative to root.
    # The user input was: @[pup-umis-backend/courses_data/pg/structureofcourse.ods]
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(base_dir, 'courses_data/pg/structureofcourse.ods')
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print("Reading ODS file...")
    
    ns = {
        'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
    }

    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            with z.open('content.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
    except Exception as e:
        print(f"Error opening ODS file: {e}")
        return

    table = root.find('.//table:table', ns)
    if table is None:
        print("No table found in ODS.")
        return

    rows = table.findall('table:table-row', ns)
    print(f"Total Rows Found: {len(rows)}")

    # Skip header row (index 0)
    for i, row in enumerate(rows):
        if i == 0:
            continue
            
        cells = row.findall('table:table-cell', ns)
        row_data = []
        for cell in cells:
            repeat = cell.get(f"{{{ns['table']}}}number-columns-repeated")
            count = int(repeat) if repeat else 1
            texts = [t.text for t in cell.findall('text:p', ns) if t.text]
            cell_text = " ".join(texts).strip()
            for _ in range(count):
                row_data.append(cell_text)
        
        # Ensure we have enough columns (at least 7)
        if len(row_data) < 7:
            continue

        faculty_name = row_data[0]
        semester = row_data[1]
        course_code = row_data[2]
        dept_name = row_data[3]
        course_name = row_data[4]
        try:
            credit = int(float(row_data[5])) if row_data[5] else 0
        except ValueError:
            credit = 0
            
        try:
            total_marks = Decimal(row_data[6]) if row_data[6] else Decimal(0)
        except:
            total_marks = Decimal(0)

        if not course_name: 
            continue

        print(f"Processing: {course_name} ({course_code}) - Sem {semester}")
        
        # Find Department
        department = None
        if dept_name:
            department = PGDepartment.objects.filter(name__iexact=dept_name).first()
            if not department:
                 print(f"  WARNING: Department '{dept_name}' not found. Skipping.")
                 continue

        # Determine if Practical
        is_practical = False
        practical_pattern = re.compile(r'practical|lab\b|practical\s*-\s*[IVX]+|practical\s*-\s*\d+', re.IGNORECASE)
        
        if practical_pattern.search(course_name) or 'practical' in course_name.lower():
            is_practical = True

        # Determine Course Type
        course_type = "CC" # Default
        if course_code:
            match = re.match(r'([A-Z]+)', course_code)
            if match:
                course_type = match.group(1)

        # Labels - ALWAYS use CIA Theory and ESE Theory as per user request
        labels = [
            {'name': 'CIA Theory', 'marks': Decimal(30)},
            {'name': 'ESE Theory', 'marks': Decimal(70)}
        ]
            
        for lbl in labels:
            exists = PGCourseStructure.objects.filter(
                department=department,
                course_name=course_name,
                semester=semester,
                label=lbl['name'],
                code=course_code
            ).exists()
            
            if exists:
                print(f"  Entry exists for {lbl['name']}. Skipping.")
                continue
                
            PGCourseStructure.objects.create(
                department=department,
                course_name=course_name,
                course_short_name=None,
                course_type=course_type,
                code=course_code,
                paper_code=course_code,
                max_credit=credit,
                max_marks=lbl['marks'],
                label=lbl['name'],
                semester=semester
            )
            print(f"  Created {lbl['name']}")

    print("Done.")

if __name__ == "__main__":
    run()
