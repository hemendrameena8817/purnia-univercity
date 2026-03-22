"""
Management command to populate pg_faculty, pg_department, pg_degree, pg_program fields
in PGOldResult by mapping discipline_code to PGDepartment.

Usage:
    python manage.py populate_pgoldresult_fields --settings=pup_umis_backend.settings.development
    python manage.py populate_pgoldresult_fields --dry-run --settings=pup_umis_backend.settings.development
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from pgoldresult.models import PGOldResult
from pg.models import PGDepartment, PGFaculty, PGDegree, PGProgram


class Command(BaseCommand):
    help = 'Populate pg_faculty, pg_department, pg_degree, pg_program in PGOldResult using discipline_code'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Build department lookup by code
        departments = {}
        for dept in PGDepartment.objects.select_related('faculty').all():
            if dept.code:
                departments[dept.code.lower().strip()] = dept
        
        self.stdout.write(f"Loaded {len(departments)} departments")
        
        # Build program lookup with degree info
        programs = {}
        for prog in PGProgram.objects.select_related('degree', 'department').all():
            if prog.department and prog.department.code:
                dept_code = prog.department.code.lower().strip()
                if dept_code not in programs:
                    programs[dept_code] = []
                programs[dept_code].append(prog)
        
        self.stdout.write(f"Loaded {len(programs)} department-program mappings")
        
        # Get all PGOldResult records with empty pg_faculty
        results_to_update = PGOldResult.objects.filter(pg_faculty__isnull=True) | \
                           PGOldResult.objects.filter(pg_faculty='')
        total = results_to_update.count()
        
        self.stdout.write(f"Found {total} PGOldResult records to process")
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No records need updating'))
            return
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for result in results_to_update.iterator():
            discipline_code = result.discipline_code
            
            if not discipline_code:
                skipped_count += 1
                continue
            
            # Normalize discipline code
            lookup_code = discipline_code.lower().strip()
            
            department = departments.get(lookup_code)
            
            if not department:
                self.stdout.write(self.style.WARNING(
                    f"No department found for discipline_code: {discipline_code} (record id: {result.id})"
                ))
                skipped_count += 1
                continue
            
            # Get faculty name
            faculty_name = department.faculty.name if department.faculty else None
            
            # Get degree and program from department's programs
            degree_name = None
            program_name = None
            
            dept_programs = programs.get(lookup_code, [])
            if dept_programs:
                # Use first program (most likely match)
                program = dept_programs[0]
                degree_name = program.degree.name if program.degree else None
                program_name = program.name
            
            # Update fields
            result.pg_faculty = faculty_name
            result.pg_department = department.name
            result.pg_degree = degree_name
            result.pg_program = program_name
            
            if not dry_run:
                try:
                    result.save(update_fields=['pg_faculty', 'pg_department', 'pg_degree', 'pg_program'])
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        self.stdout.write(f"Updated {updated_count}/{total} records...")
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error updating record {result.id}: {e}"))
                    error_count += 1
            else:
                updated_count += 1
                if updated_count <= 10:  # Show first 10 in dry-run
                    self.stdout.write(
                        f"Would update: {result.college_roll_no} | "
                        f"discipline: {discipline_code} -> "
                        f"dept: {department.name}, "
                        f"faculty: {faculty_name}, "
                        f"degree: {degree_name}, "
                        f"program: {program_name}"
                    )
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"\nDRY RUN Complete: {updated_count} records would be updated, {skipped_count} skipped"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nComplete: {updated_count} records updated, {skipped_count} skipped, {error_count} errors"
            ))
