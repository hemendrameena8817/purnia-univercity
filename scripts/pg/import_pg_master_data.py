"""
Script to import PG Faculty, Department, Degree, Program, and PGCourseStructure data.
Reads from courses_data/pg/ folder.

Usage:
    poetry run python manage.py shell -c "exec(open('scripts/pg/import_pg_master_data.py').read()); import_pg_master_data()"
"""
import os
from openpyxl import load_workbook


def clean_name(name):
    """Clean name."""
    if not name:
        return None
    return str(name).strip()


def get_semester_from_sheet_name(sheet_name):
    """Extract semester number from sheet name."""
    name_upper = sheet_name.upper()
    if 'IV SEMESTER' in name_upper or 'IVTH SEMESTER' in name_upper or '4TH SEMESTER' in name_upper:
        return 4
    elif 'III SEMESTER' in name_upper or 'IIIRD SEMESTER' in name_upper or '3RD SEMESTER' in name_upper:
        return 3
    elif 'II SEMESTER' in name_upper or 'IIND SEMESTER' in name_upper or '2ND SEMESTER' in name_upper:
        return 2
    elif 'I SEMESTER' in name_upper or 'IST SEMESTER' in name_upper or '1ST SEMESTER' in name_upper:
        return 1
    return None


def import_pg_master_data(clear_existing=False):
    """Import PG Faculty, Department, Degree, Program, and PGCourseStructure."""
    from university.models import University
    from pg.models import PGFaculty, PGDepartment, PGDegree, PGProgram, PGCourseStructure
    
    PG_COURSES_DIR = '/Users/anuprash/Desktop/projects/pup-umis-backend/courses_data/pg'
    
    print("="*70)
    print("IMPORTING PG MASTER DATA")
    print("(Faculty, Department, Degree, Program, PGCourseStructure)")
    print("="*70)
    
    # Get university
    university = University.objects.first()
    if not university:
        print("❌ No university found! Please create one first.")
        return
    print(f"University: {university.name}")
    
    # Clear existing data if requested
    if clear_existing:
        print("\n🗑️  Clearing existing PG master data...")
        PGCourseStructure.objects.all().delete()
        PGProgram.objects.all().delete()
        PGDepartment.objects.all().delete()
        PGDegree.objects.all().delete()
        PGFaculty.objects.all().delete()
        print("   Cleared all PG master data tables")
    
    # Track created records
    departments_created = set()
    courses_created = 0
    
    # Get all xlsx files
    xlsx_files = [f for f in os.listdir(PG_COURSES_DIR) if f.endswith('.xlsx')]
    print(f"\nFound {len(xlsx_files)} xlsx files to process")
    
    # Create default PG Faculty
    print("\n📁 Creating PG Faculty...")
    pg_faculty, created = PGFaculty.objects.get_or_create(
        name='Postgraduate Studies',
        defaults={
            'university': university,
            'short_name': 'PG'
        }
    )
    if created:
        print(f"   ✅ Created Faculty: Postgraduate Studies")
    
    # Create PG Degrees
    print("\n📚 Creating PG Degrees...")
    degrees_data = [
        {'name': 'Master of Arts', 'short_name': 'M.A.', 'total_semesters': 4, 'total_years': 2},
        {'name': 'Master of Science', 'short_name': 'M.Sc.', 'total_semesters': 4, 'total_years': 2},
        {'name': 'Master of Commerce', 'short_name': 'M.Com.', 'total_semesters': 4, 'total_years': 2},
    ]
    
    for deg_data in degrees_data:
        degree, created = PGDegree.objects.get_or_create(
            name=deg_data['name'],
            defaults={
                'short_name': deg_data['short_name'],
                'total_semesters': deg_data['total_semesters'],
                'total_years': deg_data['total_years']
            }
        )
        if created:
            print(f"   ✅ Created Degree: {deg_data['name']}")
    
    for xlsx_file in xlsx_files:
        xlsx_path = os.path.join(PG_COURSES_DIR, xlsx_file)
        print(f"\n📄 Processing: {xlsx_file}")
        
        wb = load_workbook(xlsx_path, read_only=True)
        
        # Process each sheet
        for sheet_name in wb.sheetnames:
            # Skip non-semester sheets
            semester = get_semester_from_sheet_name(sheet_name)
            if semester is None:
                print(f"   ⏭️  Skipping sheet: {sheet_name} (not a semester sheet)")
                continue
            
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))
            
            print(f"\n   📋 Sheet: {sheet_name} (Semester {semester}) - {len(rows)} rows")
            
            # Detect column structure by finding header row
            subject_col = None
            paper_col = None
            paper_name_col = None
            paper_code_col = None
            max_marks_col = None
            min_marks_col = None
            credit_col = None
            
            for i, row in enumerate(rows[:5]):
                if not row:
                    continue
                for j, cell in enumerate(row):
                    if cell:
                        cell_str = str(cell).lower().strip()
                        if 'subject' in cell_str and subject_col is None:
                            subject_col = j
                        elif 'paper name' in cell_str or 'title' in cell_str or 'papers' in cell_str:
                            paper_name_col = j
                        elif 'paper code' in cell_str or 'course code' in cell_str:
                            paper_code_col = j
                        elif cell_str == 'paper' or cell_str == 'paper ':
                            paper_col = j
                        elif 'max' in cell_str and 'mark' in cell_str:
                            max_marks_col = j
                        elif 'min' in cell_str and 'mark' in cell_str:
                            min_marks_col = j
                        elif 'credit' in cell_str:
                            credit_col = j
            
            # Default column indices if not found
            if subject_col is None:
                subject_col = 0 if rows and rows[0] and 'Subject' in str(rows[0][0] or '') else 1
            if paper_name_col is None:
                paper_name_col = 2 if paper_col else 3
            if paper_code_col is None:
                paper_code_col = paper_col if paper_col else 1
            
            print(f"      Detected columns - Subject: {subject_col}, Paper: {paper_col}, Name: {paper_name_col}, Code: {paper_code_col}")
            
            # Find where data starts (after header rows)
            data_start = 0
            for i, row in enumerate(rows):
                if not any(row):
                    continue
                # Look for row with actual subject data
                if len(row) > subject_col and row[subject_col]:
                    val = str(row[subject_col]).strip()
                    if val and 'Subject' not in val and 'Course' not in val and len(val) > 2:
                        data_start = i
                        break
            
            # Process data rows
            current_subject = None
            sheet_courses = 0
            
            for row in rows[data_start:]:
                if not any(row):
                    continue
                
                # Get subject (department)
                if len(row) > subject_col and row[subject_col]:
                    subject_name = clean_name(row[subject_col])
                    if subject_name and 'Subject' not in subject_name and 'M.Sc' not in subject_name and 'M.A' not in subject_name:
                        current_subject = subject_name
                
                if not current_subject:
                    continue
                
                # Get paper name
                paper_name = None
                if paper_name_col is not None and len(row) > paper_name_col:
                    paper_name = clean_name(row[paper_name_col])
                
                if not paper_name:
                    continue
                
                # Skip header-like rows
                if 'Paper Name' in paper_name or 'Title' in paper_name:
                    continue
                
                # Get paper code
                paper_code = None
                if paper_code_col is not None and len(row) > paper_code_col:
                    paper_code = clean_name(row[paper_code_col])
                
                # Create department
                if current_subject not in departments_created:
                    dept, created = PGDepartment.objects.get_or_create(
                        name=current_subject,
                        faculty=pg_faculty
                    )
                    if created:
                        departments_created.add(current_subject)
                        print(f"      ✅ Created Department: {current_subject}")
                else:
                    dept = PGDepartment.objects.filter(name=current_subject, faculty=pg_faculty).first()
                
                if not dept:
                    continue
                
                # Determine course type from paper code
                course_type = 'CC'  # Default to Core Course
                if paper_code:
                    code_upper = str(paper_code).upper()
                    if 'EC' in code_upper and 'AEC' not in code_upper:
                        course_type = 'EC'
                    elif 'GE' in code_upper:
                        course_type = 'GE'
                    elif 'SEC' in code_upper:
                        course_type = 'SEC'
                    elif 'AECC' in code_upper or 'AEC' in code_upper:
                        course_type = 'AECC'
                    elif 'CC' in code_upper:
                        course_type = 'CC'
                
                # Get marks info
                max_marks = None
                min_marks = None
                max_credit = None
                
                if max_marks_col and len(row) > max_marks_col:
                    try:
                        max_marks = int(float(row[max_marks_col])) if row[max_marks_col] else None
                    except (ValueError, TypeError):
                        pass
                
                if min_marks_col and len(row) > min_marks_col:
                    try:
                        min_marks = float(row[min_marks_col]) if row[min_marks_col] else None
                    except (ValueError, TypeError):
                        pass
                
                if credit_col and len(row) > credit_col:
                    try:
                        max_credit = int(float(row[credit_col])) if row[credit_col] else None
                    except (ValueError, TypeError):
                        pass
                
                # Create PGCourseStructure
                cs, created = PGCourseStructure.objects.get_or_create(
                    name=paper_name,
                    department=dept,
                    code=paper_code,
                    semester=semester,
                    defaults={
                        'course_type': course_type,
                        'label': paper_code or course_type,
                        'description': f'{course_type} for Semester {semester}',
                        'max_marks': max_marks,
                        'min_mark': int(min_marks) if min_marks else None,
                        'max_credit': max_credit,
                    }
                )
                if created:
                    courses_created += 1
                    sheet_courses += 1
            
            print(f"      Courses created from this sheet: {sheet_courses}")
        
        wb.close()
    
    print("\n" + "="*70)
    print("IMPORT SUMMARY")
    print("="*70)
    print(f"   Departments created: {len(departments_created)}")
    print(f"   PGCourseStructures created: {courses_created}")
    print(f"\n   Total PGFaculty: {PGFaculty.objects.count()}")
    print(f"   Total PGDepartment: {PGDepartment.objects.count()}")
    print(f"   Total PGDegree: {PGDegree.objects.count()}")
    print(f"   Total PGProgram: {PGProgram.objects.count()}")
    print(f"   Total PGCourseStructure: {PGCourseStructure.objects.count()}")


if __name__ == '__main__':
    import_pg_master_data()
