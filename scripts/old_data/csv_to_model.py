"""
Generic CSV to Django Model Generator

This script reads a CSV file, extracts column names, and:
1. Generates a Django model class code
2. Generates an admin class code
3. Generates an import script

Usage:
    poetry run python manage.py shell -c "exec(open('scripts/csv_to_model.py').read()); generate_staging_model('old_data/applicant_master.csv', 'ApplicantMaster')"
"""
import csv
import os
import re


def sanitize_field_name(column_name):
    """Convert column name to valid Python/Django field name"""
    # Replace special chars with underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '_', column_name.lower())
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    # If starts with digit, prefix with underscore
    if name and name[0].isdigit():
        name = f'col_{name}'
    return name or 'unknown_field'


def detect_delimiter(csv_path):
    """Detect CSV delimiter (tab or comma)"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if '\t' in first_line:
            return '\t'
        return ','


def get_csv_columns(csv_path):
    """Read CSV and return column names"""
    delimiter = detect_delimiter(csv_path)
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        headers = next(reader)
        return [h.strip() for h in headers]


def generate_model_code(table_name, columns):
    """Generate Django model code from column names"""
    class_name = f"Staging{table_name}"
    
    model_code = f'''import uuid
from django.db import models


class {class_name}(models.Model):
    """
    Staging table for {table_name} CSV data.
    All fields are nullable strings to accept raw CSV data.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
'''
    
    for col in columns:
        field_name = sanitize_field_name(col)
        # Use TextField for potentially long fields, CharField for others
        if any(word in field_name for word in ['address', 'description', 'details', 'notes', 'content']):
            model_code += f"    {field_name} = models.TextField(null=True, blank=True, help_text='{col}')\n"
        else:
            model_code += f"    {field_name} = models.CharField(max_length=500, null=True, blank=True, help_text='{col}')\n"
    
    model_code += '''
    # Meta fields
    is_migrated = models.BooleanField(default=False, help_text="Has this record been migrated?")
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Staging - ''' + table_name + ''''
        verbose_name_plural = 'Staging - ''' + table_name + ''''
        
    def __str__(self):
        return f"{self.uid}"
'''
    
    return model_code, class_name


def generate_admin_code(class_name, columns):
    """Generate Django admin code"""
    # Pick first 5 meaningful columns for list_display
    display_cols = [sanitize_field_name(c) for c in columns[:5]]
    display_cols.append('is_migrated')
    display_cols.append('imported_at')
    
    admin_code = f'''
@admin.register({class_name})
class {class_name}Admin(admin.ModelAdmin):
    list_display = {tuple(display_cols)}
    list_filter = ('is_migrated',)
    search_fields = {tuple(display_cols[:3])}
    readonly_fields = ('uid', 'imported_at')
    list_editable = ('is_migrated',)
'''
    return admin_code


def generate_import_script(csv_path, class_name, columns):
    """Generate import script code"""
    field_mappings = []
    for col in columns:
        field_name = sanitize_field_name(col)
        field_mappings.append(f"                    {field_name}=clean_value(row.get('{col}')),")
    
    delimiter = detect_delimiter(csv_path)
    delimiter_str = "'\\t'" if delimiter == '\t' else "','"
    
    script_code = f'''"""
Import script for {os.path.basename(csv_path)}
Run from Django shell:
    exec(open('scripts/import_{class_name.lower()}.py').read())
"""
import csv
import os
from staging.models import {class_name}

CSV_PATH = '{csv_path}'

def clean_value(value):
    if value in ('\\\\N', '', 'NULL', 'null', None):
        return None
    return str(value).strip() if value else None

def import_data():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {{CSV_PATH}}")
        return
    
    existing = {class_name}.objects.count()
    print(f"Existing records: {{existing}}")
    
    imported = 0
    errors = []
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter={delimiter_str})
        for row in reader:
            try:
                {class_name}.objects.create(
{chr(10).join(field_mappings)}
                )
                imported += 1
                if imported % 1000 == 0:
                    print(f"Imported {{imported}} records...")
            except Exception as e:
                errors.append(f"Row {{imported + 1}}: {{str(e)}}")
    
    print(f"\\n✅ Import completed!")
    print(f"   Imported: {{imported}} records")
    print(f"   Errors: {{len(errors)}}")
    if errors[:5]:
        print("   First errors:", errors[:5])
    print(f"   Total in table: {{{class_name}.objects.count()}}")

if __name__ == '__main__':
    import_data()
'''
    return script_code


def generate_staging_model(csv_path, table_name):
    """Main function to generate all files for a CSV"""
    print(f"\n📂 Reading CSV: {csv_path}")
    
    columns = get_csv_columns(csv_path)
    print(f"   Found {len(columns)} columns")
    
    # Generate model code
    model_code, class_name = generate_model_code(table_name, columns)
    
    # Generate admin code
    admin_code = generate_admin_code(class_name, columns)
    
    # Generate import script
    import_script = generate_import_script(csv_path, class_name, columns)
    
    print(f"\n{'='*60}")
    print("MODEL CODE (add to staging/models.py):")
    print('='*60)
    print(model_code)
    
    print(f"\n{'='*60}")
    print("ADMIN CODE (add to staging/admin.py):")
    print('='*60)
    print(admin_code)
    
    # Save import script
    script_path = f"scripts/import_{class_name.lower()}.py"
    with open(script_path, 'w') as f:
        f.write(import_script)
    print(f"\n✅ Import script saved to: {script_path}")
    
    print(f"\n📋 Next steps:")
    print(f"   1. Add model code to staging/models.py")
    print(f"   2. Add admin code to staging/admin.py")
    print(f"   3. Run: poetry run python manage.py makemigrations staging")
    print(f"   4. Run: poetry run python manage.py migrate staging")
    print(f"   5. Run import: poetry run python manage.py shell -c \"exec(open('{script_path}').read()); import_data()\"")
    
    return model_code, admin_code, class_name


# Run for applicant_master.csv
if __name__ == '__main__':
    generate_staging_model('old_data/applicant_master.csv', 'ApplicantMaster')
