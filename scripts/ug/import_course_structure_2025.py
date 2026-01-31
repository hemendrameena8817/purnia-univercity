import os
import sys
import django
import pandas as pd
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import CourseStructure, UGDepartment, UGBatch, UGFaculty
from university.models import University

# Excel file path
EXCEL_FILE = BASE_DIR / 'UG - Course Structure [2025-29].xlsx'
BATCH_NAME = '2025-2029'

# Course type to paper code mapping (verified from CommonCourseStructure database)
COURSE_TYPE_CODES = {
    # Semester I - codes updated to match database
    'MJC-1': '1001', 'MIC-1': '1002', 'SEC-1': '1003', 'VAC-1': '1004', 'MDC-1': '1005', 'AEC-1': '1006',
    # Semester II - codes updated to match database
    'MJC-2': '2001', 'MIC-2': '2002', 'SEC-2': '2003', 'VAC-2': '2004', 'MDC-2': '2005', 'AEC-2': '2006',
    # Semester III - codes updated to match database
    'MJC-3': '3001', 'MJC-4': '3002', 'MIC-3': '3003', 'SEC-3': '3004', 'MDC-3': '3005', 'AEC-3': '3006',
    # Semester IV - verified
    'MJC-5': '4001', 'MJC-6': '4002', 'MJC-7': '4003', 'MIC-4': '4004', 'AEC-4': '4005',
    # Semester V - verified
    'MJC-8': '5001', 'MJC-9': '5002', 'MIC-5': '5003', 'MIC-6': '5004', 'INT-1': '5005',
    # Semester VI - verified
    'MJC-10': '6001', 'MJC-11': '6002', 'MJC-12': '6003', 'MIC-7': '6004', 'MIC-8': '6005',
    # Semester VII - verified
    'MJC-13': '7001', 'MJC-14': '7002', 'MJC-15': '7003', 'MIC-9': '7004',
    # Semester VIII - verified
    'MJC-16': '8001', 'MIC-10': '8002', 'RP-1': '8003',
}


def determine_course_type(course_name):
    """Determine if course is theory, practical, or both."""
    course_name_str = str(course_name)
    has_theory = '(T)' in course_name_str
    has_practical = '(P)' in course_name_str
    
    if has_theory and has_practical:
        return 'both'  # Should not happen in same row, but handle it
    elif has_practical:
        return 'practical'
    else:
        # Default to theory if no marker
        return 'theory'


def strip_markers(course_name):
    """Remove (T) and (P) markers from course name."""
    return str(course_name).replace('(T)', '').replace('(P)', '').strip()


def generate_paper_code(semester, course_type):
    """Generate paper code based on semester and course type."""
    # Get code from mapping, or generate default
    code = COURSE_TYPE_CODES.get(course_type)
    if code:
        return code
    
    # Fallback: use semester + incremental number
    return f"{semester}999"


def create_short_name(course_name):
    """Create abbreviated course name (first letter of each word)."""
    words = course_name.split()
    if len(words) <= 2:
        return course_name[:20]  # Short enough already
    
    # Take first letter of each significant word
    abbrev = ''.join([w[0].upper() for w in words if len(w) > 2])
    return abbrev[:20] if abbrev else course_name[:20]


def import_course_structure():
    print("=" * 80)
    print("📚 COURSE STRUCTURE IMPORT: UG 2025-2029")
    print("=" * 80)
    
    # Read Excel file
    print(f"\n📖 Reading Excel file: {EXCEL_FILE.name}...")
    df = pd.read_excel(EXCEL_FILE)
    print(f"✅ Loaded {len(df)} rows")
    
    # Get university (use first one or create default)
    print(f"\n🏛️  Getting university...")
    university = University.objects.first()
    if not university:
        university = University.objects.create(name="Purnea University")
        print(f"✅ Created default university: {university.name}")
    else:
        print(f"✅ Using university: {university.name}")
    
    # Get or create batch
    print(f"\n📦 Getting or creating batch: {BATCH_NAME}...")
    batch, created = UGBatch.objects.get_or_create(
        name=BATCH_NAME,
        defaults={'json_data': {'source': 'excel_import'}}
    )
    if created:
        print(f"✅ Created new batch: {BATCH_NAME}")
    else:
        print(f"✅ Found existing batch: {BATCH_NAME}")
    
    # Clear existing course structures for this batch
    existing_count = CourseStructure.objects.filter(batch=batch).count()
    if existing_count > 0:
        print(f"\n🗑️  Deleting {existing_count} existing course structures for batch {BATCH_NAME}...")
        CourseStructure.objects.filter(batch=batch).delete()
        print(f"✅ Cleared existing data")
    
    # Track statistics
    stats = {
        'total_rows': 0,
        'theory_only': 0,
        'practical_only': 0,
        'both': 0,
        'created_entries': 0,
        'faculties_created': 0,
        'departments_created': 0,
    }
    
    # Process each row
    course_entries = []
    faculties_cache = {}
    departments_cache = {}
    
    print(f"\n🔄 Processing courses...")
    
    for idx, row in df.iterrows():
        stats['total_rows'] += 1
        
        # Extract data
        faculty_name = str(row['Faculty']).strip()
        semester = str(int(row['Semester']))
        course_code = str(row['Course Code']).strip()
        dept_name = str(row['Department']).strip() if pd.notna(row['Department']) else None
        course_name_raw = str(row['Course Name']).strip()
        total_marks = int(row['Total Marks']) if pd.notna(row['Total Marks']) else 100
        total_credits = int(row['Total Credits']) if pd.notna(row['Total Credits']) else 0
        
        # Determine course type
        ctype = determine_course_type(course_name_raw)
        course_name_clean = strip_markers(course_name_raw)
        course_short_name = create_short_name(course_name_clean)
        
        # Update stats
        if ctype == 'theory':
            stats['theory_only'] += 1
        elif ctype == 'practical':
            stats['practical_only'] += 1
        else:
            stats['both'] += 1
        
        # Get or create faculty
        if faculty_name not in faculties_cache:
            faculty, created = UGFaculty.objects.get_or_create(
                name=faculty_name,
                defaults={
                    'short_name': faculty_name[:50],
                    'university': university,
                    'json_data': {'source': 'course_structure_import'}
                }
            )
            faculties_cache[faculty_name] = faculty
            if created:
                stats['faculties_created'] += 1
                print(f"  ✨ Created faculty: {faculty_name}")
        else:
            faculty = faculties_cache[faculty_name]
        
        # Get or create department (if specified)
        department = None
        if dept_name:
            dept_key = f"{faculty_name}::{dept_name}"
            if dept_key not in departments_cache:
                department, created = UGDepartment.objects.get_or_create(
                    name=dept_name,
                    faculty=faculty,
                    defaults={'json_data': {'source': 'course_structure_import'}}
                )
                departments_cache[dept_key] = department
                if created:
                    stats['departments_created'] += 1
                    print(f"  ✨ Created department: {dept_name} ({faculty_name})")
            else:
                department = departments_cache[dept_key]
        
        # Generate paper code
        paper_code = generate_paper_code(semester, course_code)
        
        # Extract course type (MJC from MJC-1, MIC from MIC-1, etc.)
        course_type = course_code.split('-')[0] if '-' in course_code else course_code
        
        # Determine which labels to create
        labels_to_create = []
        if ctype in ['theory', 'both']:
            labels_to_create.extend(['CIA-Theory', 'ESE-Theory'])
        if ctype in ['practical', 'both']:
            labels_to_create.extend(['CIA-Practical', 'ESE-Practical'])
        
        # Create CourseStructure entries for each label
        for label in labels_to_create:
            course_entries.append(CourseStructure(
                course_name=course_name_clean,
                course_short_name=course_short_name,
                department=department,
                course_type=course_type,  # Use extracted type (MJC, MIC, etc.)
                course_code=course_code,  # Keep full code (MJC-1, MIC-1, etc.)
                paper_code=paper_code,
                max_credit=total_credits,
                max_marks=total_marks,
                label=label,
                semester=semester,
                batch=batch,
                json_data={
                    'faculty': faculty_name,
                    'department': dept_name,
                    'original_course_name': course_name_raw,
                    'excel_row': idx + 2,  # Excel row number (1-indexed + header)
                }
            ))
            stats['created_entries'] += 1
        
        # Progress indicator
        if (idx + 1) % 100 == 0:
            print(f"  📊 Processed {idx + 1}/{len(df)} rows...")
    
    # Bulk create all course structures
    print(f"\n💾 Bulk creating {len(course_entries)} course structure entries...")
    CourseStructure.objects.bulk_create(course_entries, batch_size=500)
    print(f"✅ Created {len(course_entries)} course structures")
    
    # Print statistics
    print(f"\n{'='*80}")
    print(f"📊 IMPORT STATISTICS")
    print(f"{'='*80}")
    print(f"Excel rows processed: {stats['total_rows']}")
    print(f"  - Theory only: {stats['theory_only']} (→ {stats['theory_only'] * 2} entries)")
    print(f"  - Practical only: {stats['practical_only']} (→ {stats['practical_only'] * 2} entries)")
    print(f"  - Both T+P: {stats['both']} (→ {stats['both'] * 4} entries)")
    print(f"\nFaculties created: {stats['faculties_created']}")
    print(f"Departments created: {stats['departments_created']}")
    print(f"\nTotal CourseStructure entries: {stats['created_entries']}")
    print(f"\n✅ Import complete!\n")
    
    # Verification
    print(f"{'='*80}")
    print(f"🔍 VERIFICATION")
    print(f"{'='*80}")
    for label in ['CIA-Theory', 'ESE-Theory', 'CIA-Practical', 'ESE-Practical']:
        count = CourseStructure.objects.filter(label=label, batch=batch).count()
        print(f"{label}: {count} entries")
    
    print(f"\nTotal in database: {CourseStructure.objects.filter(batch=batch).count()}")
    print()


if __name__ == '__main__':
    import_course_structure()
