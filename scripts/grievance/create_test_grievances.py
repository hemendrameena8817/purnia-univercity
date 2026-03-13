"""
Create Test Grievances Script
============================

Creates test grievances for local testing and development.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.grievance.create_test_grievances import run_create_test_grievances
>>> run_create_test_grievances()

OR run directly:
poetry run python scripts/grievance/create_test_grievances.py
"""

import sys
import os
from django.core.management.base import BaseCommand
from django.utils import timezone

# Setup Django if running standalone
if __name__ == '__main__':
    import django
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
    django.setup()

from grievance.models import Grievance, GrievanceCategory, GrievanceSubCategory
from accounts.models import UserAccount
from colleges.models import College


class Command(BaseCommand):
    help = 'Create test grievances for local testing'

    def handle(self, *args, **options):
        """Create test grievances"""
        
        # Get test data
        user = UserAccount.objects.filter(username='student').first()
        if not user:
            self.stdout.write(self.style.ERROR('Student user not found. Please create one first.'))
            return
        
        category = GrievanceCategory.objects.first()
        if not category:
            self.stdout.write(self.style.ERROR('No grievance categories found. Please run create_grievance_categories first.'))
            return
        
        subcategory = GrievanceSubCategory.objects.first()
        college = College.objects.first()
        
        if not college:
            self.stdout.write(self.style.ERROR('No college found. Please create a college first.'))
            return
        
        # Test grievances data
        test_grievances = [
            {
                'subject': 'Name Spelling Error in Marksheet',
                'description': 'My name is spelled incorrectly as "Jonh" instead of "John" in the marksheet.',
                'payment_amount': 150.00,
            },
            {
                'subject': 'Missing Subject in Transcript',
                'description': 'Mathematics subject is missing from my semester transcript.',
                'payment_amount': 100.00,
            },
            {
                'subject': 'Exam Fee Payment Failed',
                'description': 'Payment was deducted but exam form was not submitted.',
                'payment_amount': 50.00,
            },
            {
                'subject': 'Hostel Room Allotment Issue',
                'description': 'Room not allotted despite timely payment of hostel fees.',
                'payment_amount': 80.00,
            },
            {
                'subject': 'Library Card Not Working',
                'description': 'Library card barcode not scanning properly.',
                'payment_amount': 30.00,
            },
        ]
        
        created_count = 0
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Creating Test Grievances...\n'))
        
        for grievance_data in test_grievances:
            try:
                grievance = Grievance.objects.create(
                    user=user,
                    category=category,
                    subcategory=subcategory,
                    assigned_to_college=college,
                    subject=grievance_data['subject'],
                    description=grievance_data['description'],
                    contact_person_name=f"{user.first_name} {user.last_name}" if user.first_name else user.username,
                    contact_person_phone_number="9876543210",
                    payment_amount=grievance_data['payment_amount'],
                    is_payment_completed=True,  # Generate grievance number
                    status="open",
                    submitted_at=timezone.now()
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created: {grievance.grievance_number} - {grievance.subject}')
                )
                created_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to create grievance: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✨ Done! Created {created_count} test grievances')
        )


def run_create_test_grievances():
    """Run the command programmatically"""
    command = Command()
    command.handle()


if __name__ == '__main__':
    run_create_test_grievances()
