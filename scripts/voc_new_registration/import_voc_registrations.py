"""
VOC New Registration Import Script
===================================

Imports student registration data from Excel files into the database.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.voc_new_registration.import_voc_registrations import run_import
>>> run_import('old_data/All B.Ed Data 2025-27.xlsx')
>>> run_import('path/to/file.xlsx', dry_run=True)  # Test first
>>> run_import('path/to/file.xlsx', sheet='Sheet2', skip_errors=True)

OR run directly:
poetry run python scripts/voc_new_registration/import_voc_registrations.py path/to/file.xlsx --skip-errors

Excel columns required: STUDENT NAME, FATHER'S NAME, MOTHER'S NAME, COURSE, GENDER, 
CASTE, DOB, MOBILE NO, AADHAAR NO., EMAIL, COLLEGE NAME (must match database)
"""

import pandas as pd
import sys
import os
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db.models import Q

# Setup Django if running standalone
if __name__ == '__main__':
    import django
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
    django.setup()

from colleges.models import College
from voc_new_registration.models import VocNewRegistration
from academics.models import Course, Batch, Session


class Command(BaseCommand):
# ... (add_arguments stays same)

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        sheet = options['sheet']
        skip_errors = options['skip_errors']
        dry_run = options['dry_run']

        self.stdout.write(self.style.NOTICE(f'Reading Excel file: {excel_file}'))
        
        try:
            # Read Excel file
            if isinstance(sheet, str) and not sheet.isdigit():
                df = pd.read_excel(excel_file, sheet_name=sheet)
            else:
                df = pd.read_excel(excel_file, sheet_name=int(sheet))
            
            self.stdout.write(self.style.SUCCESS(f'Found {len(df)} rows in Excel file'))
            
            # Column mapping
            column_mapping = {
                'STUDENT NAME': 'student_name',
                'STUDENT NAME IN HINDI': 'student_name_hindi',
                'FATHER\'S NAME': 'father_name',
                'MOTHER\'S NAME': 'mother_name',
                'COURSE': 'course',
                'BATCH': 'batch',
                'GENDER': 'gender',
                'CASTE': 'caste',
                'DOB': 'dob',
                'MOBILE NO': 'mobile_no',
                'AADHAAR NUMBER': 'aadhaar_no',
                'EMAIL': 'email',
                'MIGRATION SUBMITTED': 'migration_submitted',
                'LAST ATTENDED UNIVERSITY': 'last_attended_university',
                'COLLEGE NAME': 'college_name',
                'BATCH': 'batch',
                'SESSION': 'session',
            }
            
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    row_data = {str(k).upper().strip(): v for k, v in row.items()}

                    data = {}
                    for excel_col, model_field in column_mapping.items():
                    
                        if excel_col in row_data:
                            value = row_data.get(excel_col)
                            if pd.isna(value):
                                value = None
                            elif isinstance(value, str):
                                value = value.strip()
                            data[model_field] = value
                    
                    # Handle Batch Lookup
                    batch_name = data.pop('batch', None)
                    data['batch'] = None
                    
                    if batch_name:
                        batch_name = str(batch_name).strip()
                        if batch_name.upper() not in ['NULL', 'NAN', 'NONE', '']:
                            batch_obj = Batch.objects.filter(name__iexact=batch_name).first()
                            if batch_obj:
                                data['batch'] = batch_obj
                            else:
                                if not skip_errors:
                                    # Warning only as requested to be optional
                                    pass 
                                self.stdout.write(self.style.WARNING(f"Warning: Batch '{batch_name}' not found for row {index+2}"))

                    # Handle Session Lookup
                    session_name = data.pop('session', None)
                    data['session'] = None
                    
                    if session_name:
                        session_name = str(session_name).strip()
                        if session_name.upper() not in ['NULL', 'NAN', 'NONE', '']:
                            session_obj = Session.objects.filter(name__iexact=session_name).first()
                            if session_obj:
                                data['session'] = session_obj
                            else:
                                self.stdout.write(self.style.WARNING(f"Warning: Session '{session_name}' not found for row {index+2}"))

                    # Handle Course Lookup
                    course_name = data.pop('course', None)
                    if course_name:
                        # Try to find course by code or name
                        course_obj = Course.objects.filter(code__iexact=course_name).first()
                        if not course_obj:
                            course_obj = Course.objects.filter(name__iexact=course_name).first()
                        
                        if course_obj:
                            data['course'] = course_obj
                        else:
                            if not skip_errors:
                                raise ValueError(f"Course '{course_name}' not found")
                            data['course'] = None
                            self.stdout.write(self.style.WARNING(f"Warning: Course '{course_name}' not found for row {index+2}"))

                    # Handle College Lookup (Name, Short Name, or Code)
                    college_name = data.pop('college_name', None)
                    college_obj = None
                    
                    if college_name:
                        c_name = str(college_name).strip()
                        # Try finding by Name OR Short Name OR Code (case-insensitive)
                        college_obj = College.objects.filter(
                            Q(name__iexact=c_name) | 
                            Q(short_name__iexact=c_name) | 
                            Q(college_code__iexact=c_name)
                        ).first()
                        
                        if not college_obj:
                            self.stdout.write(self.style.WARNING(f"Warning: College '{c_name}' not found for row {index+2}. Setting to NULL."))
                    
                    data['college'] = college_obj
                    
                    # Convert gender to single character
                    if 'gender' in data and data['gender']:
                        gender_str = str(data['gender']).upper()
                        if gender_str in ['M', 'MALE']:
                            data['gender'] = 'M'
                        elif gender_str in ['F', 'FEMALE']:
                            data['gender'] = 'F'
                        else:
                            data['gender'] = 'O'
                    
                    # Handle Caste Mapping
                    if 'caste' in data and data['caste']:
                        caste_val = str(data['caste']).upper().strip()
                        
                        # Map common variations
                        if caste_val in ['UNRESERVED', 'UR', 'GENERAL']:
                            caste_val = 'GEN'
                        
                        # Validate against allowed choices
                        valid_castes = ['GEN', 'OBC', 'SC', 'ST', 'EWS', 'EBC', 'RBC', 'FDC']
                        
                        if caste_val in valid_castes:
                            data['caste'] = caste_val
                        else:
                            # If unknown or too long, keep it blank
                            data['caste'] = None
                            self.stdout.write(self.style.WARNING(f"Warning: Invalid/Unknown caste '{caste_val}' for row {index+2}. Setting to NULL."))
                    else:
                        data['caste'] = None
                    
                    # Convert Aadhaar to string if numeric
                    if 'aadhaar_no' in data and data['aadhaar_no']:
                        try:
                            val = data['aadhaar_no']
                            if isinstance(val, (int, float)):
                                data['aadhaar_no'] = str(int(val))
                            else:
                                data['aadhaar_no'] = str(val).strip()
                        except:
                            data['aadhaar_no'] = ''
                    
                    # Convert mobile to string
                    if 'mobile_no' in data:
                        val = data['mobile_no']
                        if val:
                            try:
                                if isinstance(val, (int, float)):
                                    data['mobile_no'] = str(int(val))
                                else:
                                    data['mobile_no'] = str(val).strip()
                            except:
                                data['mobile_no'] = None
                        else:
                            data['mobile_no'] = None
                    
                    # Clean email
                    if 'email' in data and data['email']:
                        data['email'] = str(data['email']).strip().lower()

                    # Handle DOB
                    # user requested: if only number like 959385 or 34784 just make it empty
                    if 'dob' in data:
                        dob_val = data['dob']
                        if dob_val:
                            parsed_dob = None
                            if hasattr(dob_val, 'date'):
                                parsed_dob = dob_val.date()
                            elif isinstance(dob_val, str):
                                # Check if it looks like a number string
                                if dob_val.isdigit():
                                    parsed_dob = None # Invalid number string as requested
                                else:
                                    parsed_dob = parse_date(dob_val)
                            
                            data['dob'] = parsed_dob
                    
                    # Handle Migration Submitted
                    # Yes -> True, No/Dues/Empty -> False
                    mig_sub = data.get('migration_submitted')
                    if mig_sub:
                        mig_str = str(mig_sub).upper().strip()
                        data['migration_submitted'] = (mig_str == 'YES')
                    else:
                        data['migration_submitted'] = False

                    # Handle Migrated From Other University
                    # Check last_attended_university
                    data['migrated_from_other_university'] = False
                    last_uni = data.get('last_attended_university')
                    if last_uni:
                        uni_str = str(last_uni).upper().strip()
                        # If Purnia/Purnea/PUP -> False, else True
                        if any(x in uni_str for x in ['PURNIA', 'PURNEA', 'PUP']):
                            data['migrated_from_other_university'] = False
                        else:
                            data['migrated_from_other_university'] = True
                    
                    # Set defaults for account creation
                    data['is_account_created'] = False
                    data['is_registration_completed'] = False
                    
                    # Remove admission_only if it exists in data but not in model anymore
                    # The user removed ADMISSION_CHOICES and admission_only field from model in diff
                    if 'admission_only' in data:
                        del data['admission_only']
                    
                    # Validate required fields
                    if not data.get('student_name'):
                        raise ValueError("Student name is required")
                    
                    if not data.get('aadhaar_no'):
                        raise ValueError("Aadhaar number is required")
                    
                    if not dry_run:
                        # Check for duplicate by Aadhaar
                        if VocNewRegistration.objects.filter(aadhaar_no=data['aadhaar_no']).exists():
                            self.stdout.write(self.style.WARNING(f"Skipping duplicate: Aadhaar {data['aadhaar_no']} already exists (Row {index+2})"))
                            # We count this as skipped, but maybe not an error?
                            # For summary, let's just proceed without incrementing success_count if we want strict 'imported' count.
                            # But usually user considers skipping duplicates as 'processed'.
                            continue
                            
                        # Create registration entry
                        VocNewRegistration.objects.create(**data)
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        self.stdout.write(self.style.NOTICE(f'Processed {success_count} rows...'))
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Row {index + 2}: {str(e)}"
                    errors.append(error_msg)
                    
                    if skip_errors:
                        self.stdout.write(self.style.WARNING(error_msg))
                    else:
                        self.stdout.write(self.style.ERROR(error_msg))
                        raise
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n' + '='*60))
            if dry_run:
                self.stdout.write(self.style.NOTICE('DRY RUN - No data was saved to database'))
            self.stdout.write(self.style.SUCCESS(f'Successfully processed: {success_count} rows'))
            if error_count > 0:
                self.stdout.write(self.style.WARNING(f'Errors: {error_count} rows'))
                if errors:
                    self.stdout.write(self.style.WARNING('\nError details:'))
                    for error in errors[:10]:  # Show first 10 errors
                        self.stdout.write(self.style.WARNING(f'  - {error}'))
                    if len(errors) > 10:
                        self.stdout.write(self.style.WARNING(f'  ... and {len(errors) - 10} more errors'))
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {excel_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading Excel file: {str(e)}'))
            raise


# ============================================================================
# HELPER FUNCTION FOR EASY USE FROM DJANGO SHELL
# ============================================================================

def run_import(excel_file, sheet=0, skip_errors=True, dry_run=False):
    """
    Convenient helper function to run the import from Django shell.
    
    Usage from Django shell:
        >>> from scripts.voc_new_registration.import_voc_registrations import run_import
        >>> run_import('path/to/file.xlsx')
        >>> run_import('path/to/file.xlsx', dry_run=True)  # Test without saving
        >>> run_import('path/to/file.xlsx', sheet='Sheet2', skip_errors=True)
    
    Args:
        excel_file (str): Path to the Excel file
        sheet (int|str): Sheet index or name (default: 0)
        skip_errors (bool): Skip rows with errors (default: True)
        dry_run (bool): Test without saving to database (default: False)
    
    Returns:
        dict: Summary with 'success' and 'errors' counts
    """
    cmd = Command()
    
    # Create a simple output handler since we're not in a management command context
    class SimpleOutput:
        def write(self, msg):
            print(msg)
        
        def style(self):
            return self
        
        SUCCESS = NOTICE = WARNING = ERROR = lambda self, x: x
    
    cmd.stdout = SimpleOutput()
    
    try:
        cmd.handle(
            excel_file=excel_file,
            sheet=sheet,
            skip_errors=skip_errors,
            dry_run=dry_run
        )
        return {'status': 'completed'}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


# ============================================================================
# STANDALONE SCRIPT EXECUTION
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Import VOC registration data from Excel file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic import
  python import_voc_registrations.py data/registrations.xlsx
  
  # With options
  python import_voc_registrations.py data/registrations.xlsx --sheet 0 --skip-errors --dry-run
  
  # Import specific sheet
  python import_voc_registrations.py data/registrations.xlsx --sheet "Sheet2" --skip-errors
        """
    )
    
    parser.add_argument('excel_file', help='Path to the Excel file')
    parser.add_argument('--sheet', default=0, help='Sheet name or index (default: 0)')
    parser.add_argument('--skip-errors', action='store_true', help='Skip rows with errors')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without saving')
    
    args = parser.parse_args()
    
    # Convert sheet to int if it's a digit
    sheet = int(args.sheet) if str(args.sheet).isdigit() else args.sheet
    
    # Run the import
    cmd = Command()
    cmd.handle(
        excel_file=args.excel_file,
        sheet=sheet,
        skip_errors=args.skip_errors,
        dry_run=args.dry_run
    )
