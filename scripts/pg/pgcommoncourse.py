"""
Script to import PG Common Course Structure data from ODS/XLSX file.

Usage:
    python scripts/pg/pgcommoncourse.py
    python scripts/pg/pgcommoncourse.py --file /path/to/structureofcourse.ods
    python scripts/pg/pgcommoncourse.py --file /path/to/structureofcourse.xlsx
    python scripts/pg/pgcommoncourse.py --clear   # wipe and re-import
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

def import_common_course_structure(clear_existing=False, file_path=None):
    """Import PG Common Course Structure data from ODS file."""
    import pandas as pd
    from pg.models import PGCommonCourseStructure, PGDepartment
    
    print("="*70)
    print("IMPORTING PG COMMON COURSE STRUCTURE FROM ODS FILE")
    print("="*70)
    
    # Resolve file: use --file arg or auto-detect .xlsx/.ods
    import subprocess
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    engine = None

    if not file_path:
        for fname, eng in [('structureofcourse.xlsx', 'openpyxl'), ('structureofcourse.ods', 'odf')]:
            candidate = os.path.join(base_dir, 'courses_data', 'pg', fname)
            if os.path.exists(candidate):
                file_path = candidate
                engine = eng
                break
        if not file_path:
            print("❌ File not found. Use --file /path/to/structureofcourse.ods")
            return

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    # Auto-detect actual format (handles ODS renamed as .xlsx)
    result = subprocess.run(['file', file_path], capture_output=True, text=True)
    engine = 'odf' if 'OpenDocument' in result.stdout else 'openpyxl'

    print(f"\n📁 Reading file: {file_path} (engine: {engine})")

    # Clear existing data if requested
    if clear_existing:
        print("\n🗑️  Clearing existing PGCommonCourseStructure data...")
        PGCommonCourseStructure.objects.all().delete()
        print("   Cleared all PGCommonCourseStructure records")

    # Read file
    df = pd.read_excel(file_path, engine=engine)
    
    print(f"   Total rows in ODS: {len(df)}")
    print(f"   Columns: {list(df.columns)}")
    
    # Expected columns: Faculty, Semester, Course Code, Department, Course Name, etc.
    required_cols = ['Semester', 'Course Code', 'Department', 'Course Name']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Missing required columns: {missing_cols}")
        return
    
    total_created = 0
    total_updated = 0
    total_skipped = 0
    
    # Group by course code to identify common courses (courses taught across multiple departments)
    course_groups = df.groupby(['Semester', 'Course Code'])
    
    print(f"\n📚 Found {len(course_groups)} unique Semester-Course Code combinations")
    print("="*70)
    
    for (semester, course_code), group in course_groups:
        # Skip if semester or course_code is NaN
        if pd.isna(semester) or pd.isna(course_code):
            total_skipped += 1
            continue
        
        semester_str = str(semester).split('.')[0]  # Convert 1.0 to '1'
        course_code_str = str(course_code).strip()
        
        # Get course name from the first row in group
        # NOTE: Different departments have different course names for same code
        # So we DON'T store department-specific course name here
        first_row = group.iloc[0]
        
        # Determine course_type from course_code
        # e.g., CC-I -> course_type = CC, AEC-I -> course_type = AEC
        if '-' in course_code_str:
            course_type = course_code_str.split('-')[0].strip()
        else:
            course_type = course_code_str
        
        # Use course_code as course_name (generic, not department-specific)
        course_name = course_code_str
        
        # Get marks and credits from the ODS (if available)
        credit = first_row.get('Credit', 5)
        if pd.isna(credit):
            credit = 5
        else:
            try:
                credit = int(float(credit))
            except:
                credit = 5
        
        # Try to get marks from Theory Max Marks and C.I.A Max Marks columns
        theory_max = first_row.get('Theory Max Marks', 70)
        cia_max = first_row.get('C.I.A Max Marks', 30)
        
        try:
            ese_marks = int(float(theory_max)) if not pd.isna(theory_max) else 70
        except:
            ese_marks = 70
        
        try:
            cia_marks = int(float(cia_max)) if not pd.isna(cia_max) else 30
        except:
            cia_marks = 30
        
        total_marks = ese_marks + cia_marks
        
        # Get all departments offering this course
        departments = []
        for idx, row in group.iterrows():
            dept_name = row.get('Department')
            if pd.notna(dept_name):
                dept_name_str = str(dept_name).strip()
                # Try to find department in database
                dept = PGDepartment.objects.filter(name=dept_name_str).first()
                if dept and dept not in departments:
                    departments.append(dept)
        
        # Create or update PGCommonCourseStructure
        # Unique key: semester + course_code
        cs, created = PGCommonCourseStructure.objects.update_or_create(
            semester=semester_str,
            course_code=course_code_str,
            defaults={
                'course_name': course_name,
                'course_type': course_type,
                'credit': credit,
                'marks': total_marks,
                'cia_marks': cia_marks,
                'ese_marks': ese_marks,
                'json_data': {
                    'departments_count': len(departments),
                    'departments_list': [d.name for d in departments]
                }
            }
        )
        
        # Link departments via ManyToMany
        if departments:
            cs.departments.set(departments)
        
        if created:
            total_created += 1
            dept_names = ', '.join([d.name for d in departments[:3]])
            if len(departments) > 3:
                dept_names += f' +{len(departments)-3} more'
            print(f"   ✅ Sem {semester_str} | {course_code_str:15} | {course_name[:40]:40} | Depts: {dept_names}")
        else:
            total_updated += 1
    
    print("\n" + "="*70)
    print("FINAL IMPORT SUMMARY")
    print("="*70)
    print(f"   Total records created: {total_created}")
    print(f"   Total records updated: {total_updated}")
    print(f"   Total records skipped: {total_skipped}")
    print(f"   Total PGCommonCourseStructure: {PGCommonCourseStructure.objects.count()}")
    print("="*70)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Import PG Common Course Structure')
    parser.add_argument('--file', type=str, default=None, help='Path to .ods or .xlsx file')
    parser.add_argument('--clear', action='store_true', help='Clear existing data before import')
    args = parser.parse_args()
    import_common_course_structure(clear_existing=args.clear, file_path=args.file)
