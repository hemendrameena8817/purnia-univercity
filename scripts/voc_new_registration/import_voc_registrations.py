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

Excel columns REQUIRED: STUDENT NAME, AADHAAR NUMBER, COURSE (must exist in database),
BATCH (must exist in database), COLLEGE CODE (must match database college_code)

Optional columns: FATHER'S NAME, MOTHER'S NAME, GENDER, CASTE, DOB, MOBILE NO, EMAIL, 
SESSION, STUDENT NAME IN HINDI, MIGRATION SUBMITTED, LAST ATTENDED UNIVERSITY
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
from voc_new_registration.models import (
    NewRegistration,
    NewRegistrationCourse,
    NewRegistrationBatch,
    NewRegistrationSession
)


class Command(BaseCommand):
# ... (add_arguments stays same)

    def validate_row(self, row_data, index, column_mapping):
        """Validate a single row and return list of validation errors."""
        errors = []
        row_num = index + 2  # Excel row number (header is row 1)
        
        # Extract data
        data = {}
        for excel_col, model_field in column_mapping.items():
            if excel_col in row_data:
                value = row_data.get(excel_col)
                if pd.isna(value):
                    value = None
                elif isinstance(value, str):
                    value = value.strip()
                data[model_field] = value
        
        # Validate required fields
        if not data.get('student_name'):
            errors.append(f"Row {row_num}: Student name is required")
        
        if not data.get('aadhaar_no'):
            errors.append(f"Row {row_num}: Aadhaar number is required")
        else:
            # Validate Aadhaar format
            aadhaar = str(data['aadhaar_no']).strip()
            if isinstance(data['aadhaar_no'], (int, float)):
                aadhaar = str(int(data['aadhaar_no']))
            
            if len(aadhaar) != 12 or not aadhaar.isdigit():
                errors.append(f"Row {row_num}: Invalid Aadhaar number '{aadhaar}' (must be 12 digits)")
            
            # Check for duplicate Aadhaar in database
            if NewRegistration.objects.filter(aadhaar_no=aadhaar).exists():
                errors.append(f"Row {row_num}: Aadhaar '{aadhaar}' already exists in database")
        
        # Validate gender
        if data.get('gender'):
            gender_str = str(data['gender']).upper()
            if gender_str not in ['M', 'MALE', 'F', 'FEMALE', 'O', 'OTHER']:
                errors.append(f"Row {row_num}: Invalid gender '{data['gender']}' (must be M/Male, F/Female, or O/Other)")
        
        # Validate caste
        if data.get('caste'):
            caste_val = str(data['caste']).upper().strip()
            # Map common variations
            if caste_val in ['UNRESERVED', 'UR', 'GENERAL']:
                caste_val = 'GEN'
            
            valid_castes = ['GEN', 'OBC', 'SC', 'ST', 'EWS', 'EBC', 'RBC', 'FDC']
            if caste_val not in valid_castes:
                errors.append(f"Row {row_num}: Invalid caste '{data['caste']}' (must be one of: {', '.join(valid_castes)})")
        
        # Validate mobile number
        if data.get('mobile_no'):
            mobile = str(data['mobile_no']).strip()
            if isinstance(data['mobile_no'], (int, float)):
                mobile = str(int(data['mobile_no']))
            
            if len(mobile) != 10 or not mobile.isdigit():
                errors.append(f"Row {row_num}: Invalid mobile number '{mobile}' (must be 10 digits)")
        
        # Validate email format
        if data.get('email'):
            email = str(data['email']).strip().lower()
            if '@' not in email or '.' not in email.split('@')[1]:
                errors.append(f"Row {row_num}: Invalid email format '{email}'")
        
        # Validate DOB
        if data.get('dob'):
            dob_val = data['dob']
            if isinstance(dob_val, str) and dob_val.isdigit():
                errors.append(f"Row {row_num}: Invalid DOB '{dob_val}' (appears to be a number, not a date)")
        
        # Validate required course field
        if not data.get('course'):
            errors.append(f"Row {row_num}: Course is required")
        else:
            course_name = str(data['course']).strip()
            if course_name.upper() in ['NULL', 'NAN', 'NONE', '']:
                errors.append(f"Row {row_num}: Course is required (cannot be empty)")
            else:
                course_obj = NewRegistrationCourse.objects.filter(
                    Q(code__iexact=course_name) | Q(name__iexact=course_name)
                ).first()
                if not course_obj:
                    errors.append(f"Row {row_num}: Course '{course_name}' not found in database")
        
        # Validate required batch field
        if not data.get('batch'):
            errors.append(f"Row {row_num}: Batch is required")
        else:
            batch_name = str(data['batch']).strip()
            if batch_name.upper() in ['NULL', 'NAN', 'NONE', '']:
                errors.append(f"Row {row_num}: Batch is required (cannot be empty)")
            else:
                batch_obj = NewRegistrationBatch.objects.filter(name__iexact=batch_name).first()
                if not batch_obj:
                    errors.append(f"Row {row_num}: Batch '{batch_name}' not found in database")
        
        # Validate required college code field
        if not data.get('college_code'):
            errors.append(f"Row {row_num}: College code is required")
        else:
            college_code = str(data['college_code']).strip()
            if college_code.upper() in ['NULL', 'NAN', 'NONE', '']:
                errors.append(f"Row {row_num}: College code is required (cannot be empty)")
            else:
                college_obj = College.objects.filter(college_code__iexact=college_code).first()
                if not college_obj:
                    errors.append(f"Row {row_num}: College with code '{college_code}' not found in database")
        
        return errors

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
                'COLLEGE CODE': 'college_code',
                'BATCH': 'batch',
                'SESSION': 'session',
            }
            
            # ============================================================
            # PHASE 1: VALIDATION - Validate entire sheet first
            # ============================================================
            self.stdout.write(self.style.NOTICE('\n' + '='*60))
            self.stdout.write(self.style.NOTICE('PHASE 1: VALIDATING ENTIRE EXCEL SHEET'))
            self.stdout.write(self.style.NOTICE('='*60))
            
            all_validation_errors = []
            aadhaar_duplicates_in_sheet = {}
            
            for index, row in df.iterrows():
                row_data = {str(k).upper().strip(): v for k, v in row.items()}
                
                # Validate row
                row_errors = self.validate_row(row_data, index, column_mapping)
                all_validation_errors.extend(row_errors)
                
                # Check for duplicate Aadhaar within the Excel sheet itself
                aadhaar_col = row_data.get('AADHAAR NUMBER')
                if aadhaar_col and not pd.isna(aadhaar_col):
                    aadhaar = str(int(aadhaar_col)) if isinstance(aadhaar_col, (int, float)) else str(aadhaar_col).strip()
                    if aadhaar in aadhaar_duplicates_in_sheet:
                        aadhaar_duplicates_in_sheet[aadhaar].append(index + 2)
                    else:
                        aadhaar_duplicates_in_sheet[aadhaar] = [index + 2]
            
            # Check for duplicates within sheet
            for aadhaar, rows in aadhaar_duplicates_in_sheet.items():
                if len(rows) > 1:
                    all_validation_errors.append(
                        f"Duplicate Aadhaar '{aadhaar}' found in Excel sheet at rows: {', '.join(map(str, rows))}"
                    )
            
            # If validation errors found, reject the import
            if all_validation_errors:
                self.stdout.write(self.style.ERROR('\n' + '='*60))
                self.stdout.write(self.style.ERROR('VALIDATION FAILED - IMPORT REJECTED'))
                self.stdout.write(self.style.ERROR('='*60))
                self.stdout.write(self.style.ERROR(f'\nFound {len(all_validation_errors)} validation error(s):\n'))
                
                for error in all_validation_errors[:50]:  # Show first 50 errors
                    self.stdout.write(self.style.ERROR(f'  ❌ {error}'))
                
                if len(all_validation_errors) > 50:
                    self.stdout.write(self.style.ERROR(f'\n  ... and {len(all_validation_errors) - 50} more errors'))
                
                self.stdout.write(self.style.ERROR('\n' + '='*60))
                self.stdout.write(self.style.ERROR('Please fix all errors in the Excel file and try again.'))
                self.stdout.write(self.style.ERROR('='*60))
                return
            
            self.stdout.write(self.style.SUCCESS('\n✅ Validation passed! All rows are valid.'))
            self.stdout.write(self.style.NOTICE('='*60))
            
            # ============================================================
            # PHASE 2: IMPORT - Process all rows
            # ============================================================
            self.stdout.write(self.style.NOTICE('\nPHASE 2: IMPORTING DATA'))
            self.stdout.write(self.style.NOTICE('='*60))
            
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved to database\n'))
            
            success_count = 0
            
            for index, row in df.iterrows():
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
                
                # Handle Batch Lookup (required field - validated in Phase 1)
                batch_name = data.pop('batch', None)
                if batch_name:
                    batch_name = str(batch_name).strip()
                    if batch_name.upper() not in ['NULL', 'NAN', 'NONE', '']:
                        batch_obj = NewRegistrationBatch.objects.filter(name__iexact=batch_name).first()
                        data['batch'] = batch_obj
                    else:
                        data['batch'] = None
                else:
                    data['batch'] = None

                # Handle Session Lookup
                session_name = data.pop('session', None)
                data['session'] = None
                
                if session_name:
                    session_name = str(session_name).strip()
                    if session_name.upper() not in ['NULL', 'NAN', 'NONE', '']:
                        session_obj = NewRegistrationSession.objects.filter(name__iexact=session_name).first()
                        if session_obj:
                            data['session'] = session_obj
                        else:
                            # Create if not exists
                            session_obj = NewRegistrationSession.objects.create(name=session_name)
                            data['session'] = session_obj
                            self.stdout.write(self.style.NOTICE(f"Note: Created new Session '{session_name}' for row {index+2}"))

                # Handle Course Lookup (required field - validated in Phase 1)
                course_name = data.pop('course', None)
                if course_name:
                    course_name = str(course_name).strip()
                    if course_name.upper() not in ['NULL', 'NAN', 'NONE', '']:
                        # Try to find course by code or name
                        course_obj = NewRegistrationCourse.objects.filter(code__iexact=course_name).first()
                        if not course_obj:
                            course_obj = NewRegistrationCourse.objects.filter(name__iexact=course_name).first()
                        data['course'] = course_obj
                    else:
                        data['course'] = None
                else:
                    data['course'] = None

                # Handle College Lookup by College Code (required field - validated in Phase 1)
                college_code = data.pop('college_code', None)
                if college_code:
                    c_code = str(college_code).strip()
                    if c_code.upper() not in ['NULL', 'NAN', 'NONE', '']:
                        college_obj = College.objects.filter(college_code__iexact=c_code).first()
                        data['college'] = college_obj
                    else:
                        data['college'] = None
                else:
                    data['college'] = None
                
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
                    
                # All validation is done in Phase 1, so we can safely create records
                if not dry_run:
                    # Create registration entry
                    NewRegistration.objects.create(**data)
                
                success_count += 1
                
                if success_count % 10 == 0:
                    self.stdout.write(self.style.NOTICE(f'Processed {success_count} rows...'))
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n' + '='*60))
            self.stdout.write(self.style.SUCCESS('IMPORT COMPLETED SUCCESSFULLY'))
            self.stdout.write(self.style.SUCCESS('='*60))
            if dry_run:
                self.stdout.write(self.style.NOTICE(f'\n✓ DRY RUN - Validated and processed {success_count} rows (no data saved)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully imported {success_count} student registration(s) into database'))
            self.stdout.write(self.style.SUCCESS('='*60))
            
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
