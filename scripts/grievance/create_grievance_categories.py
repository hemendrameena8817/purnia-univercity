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

from grievance.models import GrievanceCategory, GrievanceSubCategory


class Command(BaseCommand):
    help = 'Creates common grievance categories with student-friendly names'

    def handle(self, *args, **options):
        """Create or update grievance categories"""
        
        # Define categories with student-friendly names and descriptions
        categories = [
            {
                'name': 'Academic Document Corrections',
                'code': 'academic_document_corrections',
                'description': 'Issues related to correction of academic documents like marksheets, certificates, and transcripts.',
                'display_order': 1,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
                'subcategories': [
                    {'name': 'Marksheet Correction', 'code': 'marksheet_correction', 'description': 'Name spelling errors, incorrect subject marks, missing subjects, incorrect semester details', 'display_order': 1, 'price': 150.00},
                    {'name': 'Provisional Certificate Correction', 'code': 'provisional_cert_correction', 'description': 'Name/father name correction, date of birth correction, course name correction', 'display_order': 2, 'price': 120.00},
                    {'name': 'Degree Certificate Correction', 'code': 'degree_cert_correction', 'description': 'Name spelling correction, course/specialization error, passing year correction', 'display_order': 3, 'price': 200.00},
                    {'name': 'Transcript Issues', 'code': 'transcript_issues', 'description': 'Incorrect grades in transcript, missing semester transcript', 'display_order': 4, 'price': 100.00},
                    {'name': 'Name/Personal Detail Correction in Academic Documents', 'code': 'personal_detail_correction', 'description': 'Correction of personal details in all academic documents', 'display_order': 5, 'price': 80.00},
                    {'name': 'Document Verification Request', 'code': 'document_verification', 'description': 'Request for verification of academic documents', 'display_order': 6, 'price': 50.00},
                    {'name': 'Certificates: Pending and Correction', 'code': 'certificates_pending_correction', 'description': 'Pending certificate issuance, correction in issued certificates', 'display_order': 7, 'price': 100.00},
                ]
            },
            {
                'name': 'Registration',
                'code': 'registration',
                'description': 'Issues related to student registration, profile updates, and registration cards.',
                'display_order': 2,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
                'subcategories': [
                    {'name': 'Name Updates', 'code': 'name_updates', 'description': 'Update name in university records', 'display_order': 1, 'price': 100.00},
                    {'name': 'Re-issue Registration Card', 'code': 'reissue_registration_card', 'description': 'Request for new registration card due to loss/damage', 'display_order': 2, 'price': 50.00},
                    {'name': 'Profile Update', 'code': 'profile_update', 'description': 'Update personal profile information', 'display_order': 3, 'price': 30.00},
                ]
            },
            {
                'name': 'Pre-examination',
                'code': 'pre_examination',
                'description': 'Issues related to examination preparation, admit cards, and exam form submission.',
                'display_order': 3,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
                'subcategories': [
                    {'name': 'Admit Card Correction', 'code': 'admit_card_correction', 'description': 'Name mismatch, incorrect subject codes, missing photograph, incorrect exam center', 'display_order': 1, 'price': 100.00},
                    {'name': 'Admit Card Not Generated', 'code': 'admit_card_not_generated', 'description': 'Admit card not generated despite form submission', 'display_order': 2, 'price': 150.00},
                    {'name': 'Examination Form Filling Issues', 'code': 'exam_form_issues', 'description': 'Unable to submit exam form, incorrect course selection, payment not updated', 'display_order': 3, 'price': 80.00},
                    {'name': 'Semester Registration Issues', 'code': 'semester_registration_issues', 'description': 'Registration not completed, incorrect semester registration', 'display_order': 4, 'price': 120.00},
                    {'name': 'Examination Fee Payment Issues', 'code': 'exam_fee_payment_issues', 'description': 'Payment failures, double payment, refund requests', 'display_order': 5, 'price': 50.00},
                    {'name': 'Examination Center Allocation Problems', 'code': 'exam_center_allocation', 'description': 'Issues with exam center assignment', 'display_order': 6, 'price': 100.00},
                    {'name': 'Exam Schedule/Time Table Issues', 'code': 'exam_schedule_issues', 'description': 'Problems with exam dates, time conflicts', 'display_order': 7, 'price': 30.00},
                    {'name': 'Exam Attendance Discrepancy', 'code': 'exam_attendance_discrepancy', 'description': 'Attendance not marked correctly', 'display_order': 8, 'price': 200.00},
                    {'name': 'Practical Examination Issues', 'code': 'practical_exam_issues', 'description': 'Missing practical marks, practical exam not scheduled', 'display_order': 9, 'price': 150.00},
                    {'name': 'Backlog/Supplementary Exam Issues', 'code': 'backlog_supplementary_exam', 'description': 'Issues with backlog and supplementary examinations', 'display_order': 10, 'price': 100.00},
                ]
            },
            {
                'name': 'Post Examination',
                'code': 'post_examination',
                'description': 'Issues related to results, marksheet issuance, and post-examination processes.',
                'display_order': 4,
                'is_assigned_to_college': False,
                'is_assigned_to_university': True,
                'subcategories': [
                    {'name': 'Result', 'code': 'result_issues', 'description': 'Result not declared, result errors', 'display_order': 1, 'price': 100.00},
                    {'name': 'Marksheets', 'code': 'marksheet_issues', 'description': 'Marksheet not received, errors in marksheet', 'display_order': 2, 'price': 150.00},
                    {'name': 'Duplicate Marksheet Request', 'code': 'duplicate_marksheet', 'description': 'Lost marksheet, damaged marksheet replacement', 'display_order': 3, 'price': 200.00},
                ]
            },
            {
                'name': 'Payment & Fee Refund',
                'code': 'payment_fee_refund',
                'description': 'Issues related to online payments, fee refunds, and payment processing.',
                'display_order': 5,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
                'subcategories': [
                    {'name': 'Fee Payment Failure', 'code': 'fee_payment_failure', 'description': 'Online payment failures', 'display_order': 1, 'price': 50.00},
                    {'name': 'Double Payment Issue', 'code': 'double_payment', 'description': 'Amount deducted twice', 'display_order': 2, 'price': 30.00},
                    {'name': 'Fee Refund Request', 'code': 'fee_refund_request', 'description': 'Request for fee refund', 'display_order': 3, 'price': 80.00},
                    {'name': 'Hostel Fee Refund', 'code': 'hostel_fee_refund', 'description': 'Hostel fee refund issues', 'display_order': 4, 'price': 100.00},
                    {'name': 'Exam Fee Refund', 'code': 'exam_fee_refund', 'description': 'Examination fee refund issues', 'display_order': 5, 'price': 60.00},
                ]
            },
            {
                'name': 'Syllabus & Academic Classes',
                'code': 'syllabus_academic_classes',
                'description': 'Issues related to syllabus, class schedules, and academic activities.',
                'display_order': 6,
                'is_assigned_to_college': True,
                'is_assigned_to_university': False,
                'subcategories': [
                    {'name': 'Incorrect Syllabus Information', 'code': 'incorrect_syllabus', 'description': 'Wrong syllabus provided', 'display_order': 1, 'price': 50.00},
                    {'name': 'Missing Subject in Syllabus', 'code': 'missing_subject', 'description': 'Subjects missing from syllabus', 'display_order': 2, 'price': 40.00},
                    {'name': 'Class Schedule Issues', 'code': 'class_schedule_issues', 'description': 'Problems with class timings', 'display_order': 3, 'price': 60.00},
                    {'name': 'Academic Calendar Confusion', 'code': 'academic_calendar', 'description': 'Issues with academic calendar dates', 'display_order': 4, 'price': 30.00},
                ]
            },
        ]

        created_count = 0
        updated_count = 0
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Creating Grievance Categories...\n'))
        
        active_codes = []
        for category_data in categories:
            active_codes.append(category_data['code'])
            
            # Extract subcategories data if present
            subcategories_data = category_data.pop('subcategories', [])
            
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
                        f'⚠️ Updated: {category.name} ({category.code})'
                    )
                )
            
            # Create subcategories for this category
            if subcategories_data:
                self.stdout.write(f'   📋 Creating subcategories for {category.name}...')
                for subcat_data in subcategories_data:
                    subcat_data['category'] = category  # Set the foreign key
                    subcategory, sub_created = GrievanceSubCategory.objects.get_or_create(
                        category=category,
                        code=subcat_data['code'],
                        defaults=subcat_data
                    )
                    
                    if sub_created:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'     ✅ Created Subcategory: {subcategory.name}'
                            )
                        )
                    else:
                        # Update existing subcategory
                        for key, value in subcat_data.items():
                            if key != 'category':  # Don't overwrite the foreign key
                                setattr(subcategory, key, value)
                        subcategory.save()
                        self.stdout.write(
                            self.style.WARNING(
                                f'     ⚠️ Updated Subcategory: {subcategory.name}'
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
