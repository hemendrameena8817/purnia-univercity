"""
Script to import UG Faculty, Department, Degree, Program, and CourseStructure data.
Reads all semester files from courses_data/ug/all_sem_courses/ folder.

Usage:
    poetry run python manage.py shell -c "exec(open('scripts/ug/import_ug_master_data.py').read()); import_ug_master_data()"
"""
import os
from openpyxl import load_workbook


# Common typo fixes for names
TYPO_FIXES = {
    'Hstory': 'History',
    'Phychology': 'Psychology',
    'Develovent': 'Development',
    'Oceanogaphy': 'Oceanography',
    'Calcules': 'Calculus',
    'Fundamentls': 'Fundamentals',
    'Fandamentals': 'Fundamentals',
    'Genral': 'General',
}


def clean_name(name):
    """Clean and fix typos in names."""
    if not name:
        return None
    name = str(name).strip()
    for typo, fix in TYPO_FIXES.items():
        name = name.replace(typo, fix)
    return name


def extract_faculty_name(row_text):
    """Extract faculty name from row like 'Faculty of Social Science - Semester-I'"""
    if not row_text or 'Faculty of' not in str(row_text):
        return None
    faculty_name = str(row_text).strip().split(' - ')[0].strip()
    return faculty_name


def extract_semester_from_filename(filename):
    """Extract semester number from filename."""
    filename_lower = filename.lower()
    if '1st' in filename_lower:
        return 1
    elif '2nd' in filename_lower:
        return 2
    elif '3rd' in filename_lower:
        return 3
    elif '4th' in filename_lower:
        return 4
    elif '5th' in filename_lower:
        return 5
    elif '6th' in filename_lower:
        return 6
    elif '7th' in filename_lower:
        return 7
    elif '8th' in filename_lower:
        return 8
    return None


def import_ug_master_data(clear_existing=False):
    """Import UG Faculty, Department, Degree, Program, and CourseStructure."""
    from university.models import University
    from ug.models import UGFaculty, UGDepartment, UGDegree, UGProgram, CourseStructure
    
    UG_COURSES_DIR = '/Users/anuprash/Desktop/projects/pup-umis-backend/courses_data/ug/all_sem_courses'
    
    print("="*70)
    print("IMPORTING UG MASTER DATA")
    print("(Faculty, Department, Degree, Program, CourseStructure)")
    print("="*70)
    
    # Get university
    university = University.objects.first()
    if not university:
        print("❌ No university found! Please create one first.")
        return
    print(f"University: {university.name}")
    
    # Clear existing data if requested
    if clear_existing:
        print("\n🗑️  Clearing existing UG master data...")
        CourseStructure.objects.all().delete()
        UGProgram.objects.all().delete()
        UGDepartment.objects.all().delete()
        UGDegree.objects.all().delete()
        UGFaculty.objects.all().delete()
        print("   Cleared all UG master data tables")
    
    # Track created records
    faculties_created = 0
    departments_created = 0
    courses_created = 0
    
    # Get all xlsx files
    xlsx_files = sorted([f for f in os.listdir(UG_COURSES_DIR) if f.endswith('.xlsx')])
    print(f"\nFound {len(xlsx_files)} xlsx files to process")
    
    for xlsx_file in xlsx_files:
        xlsx_path = os.path.join(UG_COURSES_DIR, xlsx_file)
        semester = extract_semester_from_filename(xlsx_file)
        print(f"\n📄 Processing: {xlsx_file} (Semester {semester})")
        
        if semester is None:
            print(f"   ⚠️  Could not determine semester, skipping...")
            continue
        
        wb = load_workbook(xlsx_path, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        
        current_faculty = None
        
        for i, row in enumerate(rows):
            # Skip empty rows
            if not any(row):
                continue
            
            # Check for Faculty header
            if row[0] and 'Faculty of' in str(row[0]):
                faculty_name = extract_faculty_name(row[0])
                if faculty_name:
                    # Create or get Faculty
                    faculty, created = UGFaculty.objects.get_or_create(
                        name=faculty_name,
                        defaults={
                            'university': university,
                            'short_name': ''.join([w[0] for w in faculty_name.split() if w[0].isupper()])
                        }
                    )
                    if created:
                        faculties_created += 1
                        print(f"   ✅ Created Faculty: {faculty_name}")
                    current_faculty = faculty
                continue
            
            # Skip header rows
            if row[0] and 'Department & Subject Name' in str(row[0]):
                continue
            
            # Skip note rows, title rows
            if row[0] and ('Note' in str(row[0]) or 'List of subjects' in str(row[0])):
                continue
            if len(row) > 3 and row[3] and 'MJC' in str(row[3]) and 'में' in str(row[3]):
                continue
            
            if not current_faculty:
                continue
            
            # Column structure (varies by file but generally):
            # 0: Department/Subject Name (for MJC)
            # 1: MJC course name
            # 2: MIC Subject Name (optional) or MIC course name
            # 3: MIC course name (optional)
            # 4: SEC course name
            # 5: VAC course name
            # 6: MDC Subject Name (optional)
            # 7: MDC course name
            # 8: AEC course name
            
            # --- Process MJC (Major Core Course) ---
            if row[0] and row[1]:
                dept_name = clean_name(row[0])
                course_name = clean_name(row[1])
                
                if dept_name and course_name and len(dept_name) < 100:
                    # Create department
                    dept, created = UGDepartment.objects.get_or_create(
                        name=dept_name,
                        faculty=current_faculty
                    )
                    if created:
                        departments_created += 1
                    
                    # Create course structure
                    cs, created = CourseStructure.objects.get_or_create(
                        name=course_name,
                        department=dept,
                        course_type='MJC',
                        code=f'MJC-{semester}',
                        semester=semester,
                        defaults={
                            'label': 'Major Core Course',
                            'description': f'Major Core Course for Semester {semester}',
                        }
                    )
                    if created:
                        courses_created += 1
            
            # --- Process MIC (Minor Core Course) ---
            # Check columns 2 and 3 for MIC data
            mic_dept_name = None
            mic_course_name = None
            
            if len(row) > 2 and row[2]:
                val = clean_name(row[2])
                # Determine if it's a department name or course name
                if val and 'MJC' not in str(val) and len(val) < 100:
                    if len(row) > 3 and row[3]:
                        mic_dept_name = val
                        mic_course_name = clean_name(row[3])
                    else:
                        mic_course_name = val
            
            if mic_course_name and current_faculty:
                # Use MJC department if MIC department not specified
                if mic_dept_name:
                    dept, created = UGDepartment.objects.get_or_create(
                        name=mic_dept_name,
                        faculty=current_faculty
                    )
                    if created:
                        departments_created += 1
                elif row[0]:
                    dept = UGDepartment.objects.filter(name=clean_name(row[0]), faculty=current_faculty).first()
                else:
                    dept = None
                
                if dept and 'MJC' not in str(mic_course_name) and 'में' not in str(mic_course_name):
                    cs, created = CourseStructure.objects.get_or_create(
                        name=mic_course_name,
                        department=dept,
                        course_type='MIC',
                        code=f'MIC-{semester}',
                        semester=semester,
                        defaults={
                            'label': 'Minor Core Course',
                            'description': f'Minor Core Course for Semester {semester}',
                        }
                    )
                    if created:
                        courses_created += 1
            
            # --- Process SEC (Skill Enhancement Course) ---
            sec_col = 4 if len(row) > 4 else None
            if sec_col and row[sec_col]:
                course_name = clean_name(row[sec_col])
                if course_name:
                    # Get first department for this faculty
                    dept = UGDepartment.objects.filter(faculty=current_faculty).first()
                    if dept:
                        cs, created = CourseStructure.objects.get_or_create(
                            name=course_name,
                            department=dept,
                            course_type='SEC',
                            code=f'SEC-{semester}',
                            semester=semester,
                            defaults={
                                'label': 'Skill Enhancement Course',
                                'description': f'Skill Enhancement Course for Semester {semester}',
                            }
                        )
                        if created:
                            courses_created += 1
            
            # --- Process VAC (Value Added Course) ---
            vac_col = 5 if len(row) > 5 else None
            if vac_col and row[vac_col]:
                course_name = clean_name(row[vac_col])
                if course_name and 'MDC' not in str(row[vac_col]):
                    dept = UGDepartment.objects.filter(faculty=current_faculty).first()
                    if dept:
                        cs, created = CourseStructure.objects.get_or_create(
                            name=course_name,
                            department=dept,
                            course_type='VAC',
                            code=f'VAC-{semester}',
                            semester=semester,
                            defaults={
                                'label': 'Value Added Course',
                                'description': f'Value Added Course for Semester {semester}',
                            }
                        )
                        if created:
                            courses_created += 1
            
            # --- Process MDC (Multi-Disciplinary Course) ---
            # Usually in columns 5/6 (subject) and 6/7 (course name)
            mdc_dept_col = None
            mdc_course_col = None
            
            for idx in [5, 6]:
                if len(row) > idx and row[idx]:
                    val = str(row[idx])
                    if 'MDC' in val or len(val) < 50:  # Likely department name
                        mdc_dept_col = idx
                        mdc_course_col = idx + 1 if len(row) > idx + 1 else None
                        break
            
            if mdc_dept_col and mdc_course_col and row[mdc_dept_col] and len(row) > mdc_course_col and row[mdc_course_col]:
                dept_name = clean_name(row[mdc_dept_col])
                course_name = clean_name(row[mdc_course_col])
                
                if dept_name and course_name and 'Note' not in str(dept_name):
                    dept, created = UGDepartment.objects.get_or_create(
                        name=dept_name,
                        faculty=current_faculty
                    )
                    if created:
                        departments_created += 1
                    
                    cs, created = CourseStructure.objects.get_or_create(
                        name=course_name,
                        department=dept,
                        course_type='MDC',
                        code=f'MDC-{semester}',
                        semester=semester,
                        defaults={
                            'label': 'Multi-Disciplinary Course',
                            'description': f'Multi-Disciplinary Course for Semester {semester}',
                        }
                    )
                    if created:
                        courses_created += 1
            
            # --- Process AEC (Ability Enhancement Course) ---
            aec_col = 7 if len(row) > 7 else (8 if len(row) > 8 else None)
            if aec_col and row[aec_col]:
                course_name = clean_name(row[aec_col])
                if course_name:
                    dept = UGDepartment.objects.filter(faculty=current_faculty).first()
                    if dept:
                        cs, created = CourseStructure.objects.get_or_create(
                            name=course_name,
                            department=dept,
                            course_type='AEC',
                            code=f'AEC-{semester}',
                            semester=semester,
                            defaults={
                                'label': 'Ability Enhancement Course - MIL',
                                'description': f'Ability Enhancement Course for Semester {semester}',
                            }
                        )
                        if created:
                            courses_created += 1
        
        wb.close()
    
    # Create default UG Degrees
    print("\n📚 Creating UG Degrees...")
    degrees_data = [
        {'name': 'Bachelor of Arts (Honours)', 'short_name': 'B.A. (Hons)', 'total_semesters': 8, 'total_years': 4},
        {'name': 'Bachelor of Science (Honours)', 'short_name': 'B.Sc. (Hons)', 'total_semesters': 8, 'total_years': 4},
        {'name': 'Bachelor of Commerce (Honours)', 'short_name': 'B.Com. (Hons)', 'total_semesters': 8, 'total_years': 4},
    ]
    
    for deg_data in degrees_data:
        degree, created = UGDegree.objects.get_or_create(
            name=deg_data['name'],
            defaults={
                'short_name': deg_data['short_name'],
                'total_semesters': deg_data['total_semesters'],
                'total_years': deg_data['total_years']
            }
        )
        if created:
            print(f"   ✅ Created Degree: {deg_data['name']}")
    
    print("\n" + "="*70)
    print("IMPORT SUMMARY")
    print("="*70)
    print(f"   Faculties created: {faculties_created}")
    print(f"   Departments created: {departments_created}")
    print(f"   CourseStructures created: {courses_created}")
    print(f"\n   Total UGFaculty: {UGFaculty.objects.count()}")
    print(f"   Total UGDepartment: {UGDepartment.objects.count()}")
    print(f"   Total UGDegree: {UGDegree.objects.count()}")
    print(f"   Total UGProgram: {UGProgram.objects.count()}")
    print(f"   Total CourseStructure: {CourseStructure.objects.count()}")


if __name__ == '__main__':
    import_ug_master_data()
