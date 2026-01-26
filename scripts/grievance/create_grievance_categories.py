"""
Create Grievance Categories Script
===================================

Creates/updates 19 grievance categories with student-friendly names and priorities.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.grievance.create_grievance_categories import run_create_categories
>>> run_create_categories()

OR run directly:
poetry run python scripts/grievance/create_grievance_categories.py
"""

import sys
import os
from django.core.management.base import BaseCommand

# Setup Django if running standalone
if __name__ == '__main__':
    import django
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
    django.setup()

from grievance.models import GrievanceCategory


class Command(BaseCommand):
    help = 'Creates common grievance categories with student-friendly names'

    def handle(self, *args, **options):
        """Create or update grievance categories"""
        
        # Define categories with student-friendly names and descriptions
        categories = [
            {
                'name': 'Admission',
                'code': 'admission',
                'description': 'Issues related to new admissions, entry requirements, seat allotment, and admission process.',
                'display_order': 1,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'Registration & Migration',
                'code': 'registration_migration',
                'description': 'Problems with university registration, enrollment numbers, and migration certificate requests.',
                'display_order': 2,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
            },
            {
                'name': 'Payment & Fee Refunds',
                'code': 'payment_fee_refunds',
                'description': 'Issues with online payments, fee receipts, refund of excess fees, or payment failures.',
                'display_order': 3,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'Scholarship & Financial Aid',
                'code': 'scholarship_financial_aid',
                'description': 'Inquiries and issues regarding scholarships, stipends, and financial assistance programs.',
                'display_order': 4,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'Examination & Admit Cards',
                'code': 'examination_admit_cards',
                'description': 'Issues with exam schedules, admit card generation, exam center issues, or hall tickets.',
                'display_order': 5,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
            },
            {
                'name': 'Results & Marksheet Correction',
                'code': 'results_marksheet_correction',
                'description': 'Correction of errors in marksheets, result delays, re-evaluation, and mark verification.',
                'display_order': 6,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
            },
            {
                'name': 'Certificates: Pending and Correction',
                'code': 'certificates_pending_correction',
                'description': 'Queries regarding pending degree/provisional certificates and correction of personal details in certificates.',
                'display_order': 7,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
            },
            {
                'name': 'Degree & Convocation',
                'code': 'degree_convocation',
                'description': 'Applications for degrees, convocation ceremony details, and degree distribution issues.',
                'display_order': 8,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
            },
            {
                'name': 'Syllabus & Academic Classes',
                'code': 'syllabus_academic_classes',
                'description': 'Issues regarding class schedules, course syllabus, completion of syllabus, and academic calendar.',
                'display_order': 9,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'Faculty & Teaching Staff',
                'code': 'faculty_teaching_staff',
                'description': 'Grievances related to faculty behavior, teaching methodology, or unavailability of teachers.',
                'display_order': 10,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'Hostel & Mess Facilities',
                'code': 'hostel_mess_facilities',
                'description': 'Issues related to hostel room allotment, maintenance, food quality in mess, and hygiene.',
                'display_order': 11,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'Library & Digital Resources',
                'code': 'library_digital_resources',
                'description': 'Inaccessibility of books, digital journals, e-library issues, and library management.',
                'display_order': 12,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'College Infrastructure & Sanitation',
                'code': 'infrastructure_sanitation',
                'description': 'Grievances regarding classroom maintenance, washroom hygiene, drinking water, and campus cleanliness.',
                'display_order': 13,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'Technical Portal & Login Issues',
                'code': 'technical_portal_login',
                'description': 'Technical glitches in the UMIS portal, login errors, password reset, and website maintenance.',
                'display_order': 14,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
            },
            {
                'name': 'Anti-Ragging & Discipline',
                'code': 'anti_ragging_discipline',
                'description': 'Reporting of ragging incidents, bullying, or disciplinary issues. (High Priority)',
                'display_order': 15,
                'is_assigned_to_college': True,
                'is_assigned_to_university': True,
            },
            {
                'name': 'Student Welfare & Sports',
                'code': 'student_welfare_sports',
                'description': 'Issues related to extra-curricular activities, sports facilities, and general student welfare.',
                'display_order': 16,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
            {
                'name': 'General / Others',
                'code': 'general_others',
                'description': 'Any other grievances not falling under the above specified categories.',
                'display_order': 99,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
            },
        ]

        created_count = 0
        updated_count = 0
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Creating Grievance Categories...\n'))
        
        active_codes = []
        for category_data in categories:
            active_codes.append(category_data['code'])
            category, created = GrievanceCategory.objects.get_or_create(
                code=category_data['code'],
                defaults=category_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Created: {category.name} ({category.code})'
                    )
                )
            else:
                # Update existing category and ensure it's active
                category_data['is_active'] = True
                for key, value in category_data.items():
                    setattr(category, key, value)
                category.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'� Updated: {category.name} ({category.code})'
                    )
                )

        # Handle extra categories (remove or deactivate)
        extra_categories = GrievanceCategory.objects.exclude(code__in=active_codes)
        for extra in extra_categories:
            if extra.grievances.exists():
                # If there are grievances, just deactivate it
                extra.is_active = False
                extra.save()
                self.stdout.write(
                    self.style.NOTICE(
                        f'🔕 Deactivated (has dependencies): {extra.name} ({extra.code})'
                    )
                )
            else:
                # If no grievances, we can safely delete it
                extra_name = extra.name
                extra_code = extra.code
                extra.delete()
                self.stdout.write(
                    self.style.NOTICE(
                        f'�️ Removed (no dependencies): {extra_name} ({extra_code})'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✨ Done! Created: {created_count}, Updated: {updated_count}\n'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'📊 Total Active Categories: {GrievanceCategory.objects.filter(is_active=True).count()}\n'
            )
        )


# ============================================================================
# HELPER FUNCTION FOR EASY USE FROM DJANGO SHELL
# ============================================================================

def run_create_categories():
    """
    Convenient helper function to create/update categories from Django shell.
    
    Usage from Django shell:
        >>> from scripts.grievance.create_grievance_categories import run_create_categories
        >>> run_create_categories()
    
    Returns:
        dict: Summary with created and updated counts
    """
    cmd = Command()
    
    # Create a simple output handler
    class SimpleOutput:
        def write(self, msg):
            print(msg)
        
        class style:
            @staticmethod
            def SUCCESS(x):
                return f"✅ {x}"
            
            @staticmethod
            def WARNING(x):
                return f"⚠️  {x}"
            
            @staticmethod
            def ERROR(x):
                return f"❌ {x}"
            
            @staticmethod
            def NOTICE(x):
                return f"ℹ️  {x}"
    
    cmd.stdout = SimpleOutput()
    
    try:
        cmd.handle()
        return {
            'status': 'completed',
            'total': GrievanceCategory.objects.count()
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


# ============================================================================
# STANDALONE SCRIPT EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Creating Grievance Categories")
    print("="*60 + "\n")
    
    cmd = Command()
    cmd.handle()
    
    print("\n" + "="*60)
    print("✅ Script completed successfully!")
    print("="*60 + "\n")
