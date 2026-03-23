from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pgoldresult.models import PGOldStudentProfile, College
from import_export import resources
import csv
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PGOldStudentProfileResource(resources.ModelResource):
    class Meta:
        model = PGOldStudentProfile
        fields = (
            'uid', 'registration_no', 'roll_no', 'student_name', 'student_name_hindi',
            'fathers_name', 'mothers_name', 'gender', 'dob',
            'college__college_code', 'college__name',
            'course_code', 'discipline_code', 'batch_code', 'current_semester',
            'pg_faculty', 'pg_department', 'pg_degree', 'pg_program',
            'final_result', 'gpa', 'cgpa', 'total_percentage',
            'source_user_id', 'is_active', 'created_at', 'updated_at'
        )
        import_id_fields = ('registration_no', 'roll_no')
        skip_unchanged = True
        report_skipped = True

class Command(BaseCommand):
    help = 'Import PGOldStudentProfile data with proper relationship handling'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Input file path')
        parser.add_argument('--format', type=str, default='csv', 
                          choices=['csv', 'xlsx', 'json'],
                          help='Import format (csv, xlsx, json)')
        parser.add_argument('--dry-run', action='store_true',
                          help='Run without actually importing')
        parser.add_argument('--update-existing', action='store_true',
                          help='Update existing records')
        parser.add_argument('--create-users', action='store_true',
                          help='Create user accounts for profiles')

    def handle(self, *args, **options):
        file_path = options['file']
        format_type = options['format']
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        create_users = options['create_users']
        
        resource = PGOldStudentProfileResource()
        
        try:
            if format_type == 'csv':
                # Use import_export's built-in CSV handling
                dataset = resource.import_from_file(file_path)
            
            elif format_type == 'xlsx':
                dataset = resource.import_from_file(file_path)
            
            elif format_type == 'json':
                # Convert JSON to CSV format for import_export
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    if json_data:
                        # Create temporary CSV file
                        import tempfile
                        import os
                        
                        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
                        writer = csv.DictWriter(temp_file, fieldnames=json_data[0].keys())
                        writer.writeheader()
                        writer.writerows(json_data)
                        temp_file.close()
                        
                        dataset = resource.import_from_file(temp_file.name)
                        os.unlink(temp_file.name)
                    else:
                        dataset = None
            
            if dataset is None:
                self.stdout.write(
                    self.style.ERROR('No data to import')
                )
                return
            
            # Import process
            if dry_run:
                result = resource.import_data(dataset, dry_run=True)
                self.stdout.write(
                    self.style.SUCCESS(f'DRY RUN: {result.totals["new"]} new, {result.totals["update"]} updated, {result.totals["skip"]} skipped, {result.totals["error"]} errors')
                )
            else:
                result = resource.import_data(dataset, dry_run=False)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Imported: {result.totals["new"]} new, {result.totals["update"]} updated, {result.totals["skip"]} skipped, {result.totals["error"]} errors')
                )
                
                if result.has_errors():
                    self.stdout.write(
                        self.style.ERROR('Import errors occurred:')
                    )
                    for error in result.row_errors():
                        self.stdout.write(
                            self.style.ERROR(f'Row {error[0]}: {error[1]}')
                        )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Import failed: {str(e)}')
            )
            logger.error(f'Import failed: {str(e)}')
