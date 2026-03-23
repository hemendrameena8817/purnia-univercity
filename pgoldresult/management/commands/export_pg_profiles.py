from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pgoldresult.models import PGOldStudentProfile
from import_export import resources
import csv
import json
from datetime import datetime

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
        export_order = fields

class Command(BaseCommand):
    help = 'Export PGOldStudentProfile data with proper relationships'

    def add_arguments(self, parser):
        parser.add_argument('--format', type=str, default='csv', 
                          choices=['csv', 'xlsx', 'json'],
                          help='Export format (csv, xlsx, json)')
        parser.add_argument('--output', type=str, 
                          help='Output file path')
        parser.add_argument('--batch-code', type=str,
                          help='Filter by batch code')
        parser.add_argument('--college', type=str,
                          help='Filter by college code')

    def handle(self, *args, **options):
        format_type = options['format']
        output_file = options.get('output', f'pg_student_profiles_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{format_type}')
        
        # Filter profiles if specified
        queryset = PGOldStudentProfile.objects.all()
        
        if options['batch_code']:
            queryset = queryset.filter(batch_code=options['batch_code'])
        
        if options['college']:
            queryset = queryset.filter(college__college_code=options['college'])
        
        resource = PGOldStudentProfileResource()
        dataset = resource.export(queryset)
        
        if format_type == 'csv':
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(dataset.headers)
                for row in dataset:
                    writer.writerow(row)
        
        elif format_type == 'json':
            data = []
            for row in dataset:
                data.append(dict(zip(dataset.headers, row)))
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        elif format_type == 'xlsx':
            dataset.save(output_file)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully exported {queryset.count()} profiles to {output_file}')
        )
