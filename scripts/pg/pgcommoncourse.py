"""
Script to import PG Common Course Structure data from Excel file.
This data is based on Subject Detail_PG.xlsx with multiple semester sheets.

Usage:
    python manage.py shell -c "exec(open('scripts/pg/pgcommoncourse.py').read()); import_common_course_structure()"
"""

import os

def import_common_course_structure(clear_existing=False):
    """Import PG Common Course Structure data from Excel file."""
    import pandas as pd
    from pg.models import PGCommonCourseStructure
    
    print("="*70)
    print("IMPORTING PG COMMON COURSE STRUCTURE FROM EXCEL")
    print("="*70)
    
    # Path to Excel file
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                              'courses_data', 'pg', 'Subject Detail_PG.xlsx')
    
    # Check if file exists
    if not os.path.exists(excel_path):
        excel_path = 'courses_data/pg/Subject Detail_PG.xlsx'
        if not os.path.exists(excel_path):
            print(f"❌ Excel file not found at: {excel_path}")
            return
    
    print(f"\n📁 Reading Excel file: {excel_path}")
    
    # Clear existing data if requested
    if clear_existing:
        print("\n🗑️  Clearing existing PGCommonCourseStructure data...")
        PGCommonCourseStructure.objects.all().delete()
        print("   Cleared all PGCommonCourseStructure records")
    
    excel_file = pd.ExcelFile(excel_path)
    print(f"   Available sheets: {excel_file.sheet_names}")
    
    # Define sheet configurations for each semester
    # semester_num is used for both semester field and old_code prefix
    sheet_configs = [
        {
            'sheet': 'PG I SEMESTER (2)',
            'semester_num': 1,
            'header_row': 1,
            'columns': {
                'subject': 'Subject',
                'paper': 'Paper ',
                'title': 'Title',
                'ese_max': 'Max_Marks',
                'cia_max': 'Max_Marks.1',
                'credit': 'Credit'
            }
        },
        {
            'sheet': 'PG II SEMESTER',
            'semester_num': 2,
            'header_row': 1,
            'columns': {
                'subject': 'Subject',
                'paper': 'Paper',
                'title': 'Paper Name',
                'ese_max': 'Max Marks',
                'cia_max': 'Unnamed: 7',
                'credit': None
            }
        },
        {
            'sheet': 'PG III SEMESTER',
            'semester_num': 3,
            'header_row': 1,
            'columns': {
                'subject': 'Subjects',
                'paper': 'Course Code',
                'title': 'Papers',
                'ese_max': 'Max Marks',
                'cia_max': 'Unnamed: 7',
                'credit': 'Credit'
            }
        },
        {
            'sheet': 'PG IV SEMESTER',
            'semester_num': 4,
            'header_row': 1,
            'columns': {
                'subject': 'Subject',
                'paper': 'PAPER ',
                'title': 'PAPER NAME',
                'ese_max': 'Max Marks',
                'cia_max': 'Unnamed: 6',
                'credit': None
            }
        },
    ]
    
    total_created = 0
    total_updated = 0
    total_skipped = 0
    
    for config in sheet_configs:
        sheet_name = config['sheet']
        semester_num = config['semester_num']
        col_map = config['columns']
        
        if sheet_name not in excel_file.sheet_names:
            print(f"\n⚠️  Sheet '{sheet_name}' not found, skipping...")
            continue
        
        print(f"\n{'='*70}")
        print(f"📚 Processing Semester {semester_num} from sheet: {sheet_name}")
        print("="*70)
        
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=config['header_row'])
        
        # Forward fill subject column (subjects span multiple rows)
        if col_map['subject'] in df.columns:
            df[col_map['subject']] = df[col_map['subject']].ffill()
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Reset old_code counter for each semester (e.g., 1001 for sem1, 2001 for sem2)
        old_code_counter = semester_num * 1000 + 1
        
        for idx, row in df.iterrows():
            # Get subject
            subject = row.get(col_map['subject']) if col_map['subject'] else None
            if pd.isna(subject) or str(subject).strip().lower() in ['nan', '', 'subjects', 'subject']:
                skipped_count += 1
                continue
            subject = str(subject).strip()
            
            # Get paper code (this becomes course_type)
            paper = row.get(col_map['paper']) if col_map['paper'] else None
            if pd.isna(paper) or str(paper).strip().lower() in ['nan', '', 'paper', 'paper ', 'course code']:
                skipped_count += 1
                continue
            paper = str(paper).strip()
            
            # Normalize course_type: convert Arabic numerals to Roman numerals for consistency
            # e.g., AEC-1 -> AEC-I, CC-2 -> CC-II to avoid duplicates
            def normalize_course_type(code):
                # Map Arabic to Roman numerals
                arabic_to_roman = {
                    '1': 'I', '2': 'II', '3': 'III', '4': 'IV', '5': 'V',
                    '6': 'VI', '7': 'VII', '8': 'VIII', '9': 'IX'
                }
                if '-' in code:
                    parts = code.split('-')
                    base = parts[0].strip()
                    suffix = parts[1].strip()
                    # If suffix is a single digit, convert to Roman
                    if suffix in arabic_to_roman:
                        suffix = arabic_to_roman[suffix]
                    return f"{base}-{suffix}"
                return code
            
            # course_type = normalized paper code (e.g., "CC-I", "AEC-I")
            course_type = normalize_course_type(paper)
            
            # course_name = extract base name from paper code (e.g., "CC" from "CC-I" or "CC-1")
            if '-' in paper:
                course_name = paper.split('-')[0].strip()
            else:
                course_name = paper
            
            # Get title (for reference only, stored in json_data if needed)
            title = row.get(col_map['title']) if col_map['title'] else None
            if pd.isna(title) or str(title).strip().lower() in ['nan', '']:
                title_str = f"{subject} - {paper}"
            else:
                title_str = str(title).strip()
            
            # Get marks
            ese_max = row.get(col_map['ese_max']) if col_map['ese_max'] else 70
            cia_max = row.get(col_map['cia_max']) if col_map['cia_max'] else 30
            
            try:
                ese_marks = int(float(ese_max)) if not pd.isna(ese_max) else 70
            except:
                ese_marks = 70
            
            try:
                cia_marks = int(float(cia_max)) if not pd.isna(cia_max) else 30
            except:
                cia_marks = 30
            
            total_marks = ese_marks + cia_marks
            
            # Get credit
            credit_col = col_map.get('credit')
            if credit_col and credit_col in df.columns:
                credit = row.get(credit_col)
                try:
                    credit_value = int(float(credit)) if not pd.isna(credit) else 5
                except:
                    credit_value = 5
            else:
                credit_value = 5
            
            # Generate old_code based on semester (1001, 1002 for sem1; 2001, 2002 for sem2, etc.)
            old_code = str(old_code_counter)
            old_code_counter += 1
            
            
            # new_code is left blank (to be filled later if needed)
            new_code = None
            
            # Semester is just the number: "1", "2", "3", "4"
            semester = str(semester_num)
            
            # Create or update PGCommonCourseStructure
            # Unique key: semester + course_type (subject stored in json_data)
            cs, created = PGCommonCourseStructure.objects.update_or_create(
                semester=semester,
                course_type=course_type,
                defaults={
                    'course_name': course_name,  # Just "CC", "AECC", etc.
                    'credit': credit_value,
                    'marks': total_marks,
                    'old_code': old_code,
                    'cia_marks': cia_marks,
                    'ese_marks': ese_marks,
                    'new_code': new_code,
                    'json_data': {'title': title_str, 'subject': subject}
                }
            )
            
            if created:
                created_count += 1
                print(f"   ✅ Sem:{semester} | {course_name} | {course_type[:30]}... | old_code:{old_code}")
            else:
                updated_count += 1
        
        print(f"\n   📊 Semester {semester_num}: Created={created_count}, Updated={updated_count}, Skipped={skipped_count}")
        total_created += created_count
        total_updated += updated_count
        total_skipped += skipped_count
    
    print("\n" + "="*70)
    print("FINAL IMPORT SUMMARY")
    print("="*70)
    print(f"   Total records created: {total_created}")
    print(f"   Total records updated: {total_updated}")
    print(f"   Total records skipped: {total_skipped}")
    print(f"   Total PGCommonCourseStructure: {PGCommonCourseStructure.objects.count()}")
    print("="*70)


if __name__ == '__main__':
    import_common_course_structure()
