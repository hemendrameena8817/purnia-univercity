"""
Management command to create common grievance categories with student-friendly names.
Usage: python manage.py create_grievance_categories
"""

from django.core.management.base import BaseCommand
from grievance.models import GrievanceCategory


class Command(BaseCommand):
    help = 'Creates common grievance categories with student-friendly names'

    def handle(self, *args, **options):
        """Create or update grievance categories"""
        
        # Define categories with student-friendly names and descriptions
        categories = [
            {
                'name': 'Marksheet & Certificate Issues',
                'code': 'marksheet_certificate',
                'description': 'Issues related to marksheet corrections, name changes, certificate issuance, duplicate certificates, migration certificates, etc.',
                'icon': '📜',
                'color': '#3B82F6',
                'display_order': 1,
                'default_priority': 'high',  # Important documents
            },
            {
                'name': 'Exam Related Issues',
                'code': 'examination',
                'description': 'Issues with exam schedules, admit cards, exam center problems, answer sheet evaluation, re-evaluation, grace marks, etc.',
                'icon': '📝',
                'color': '#EF4444',
                'display_order': 2,
                'default_priority': 'urgent',  # Time-sensitive
            },
            {
                'name': 'Fee & Payment Issues',
                'code': 'fee_payment',
                'description': 'Fee payment problems, refund issues, scholarship queries, fee receipt not received, wrong fee charged, etc.',
                'icon': '💰',
                'color': '#10B981',
                'display_order': 3,
                'default_priority': 'high',  # Financial matters
            },
            {
                'name': 'Admission & Registration',
                'code': 'admission_registration',
                'description': 'Admission process issues, registration problems, course enrollment, subject selection, branch change requests, etc.',
                'icon': '📋',
                'color': '#8B5CF6',
                'display_order': 4,
                'default_priority': 'high',  # Critical for students
            },
            {
                'name': 'Attendance & Leave',
                'code': 'attendance_leave',
                'description': 'Attendance marking errors, leave approval issues, medical leave, attendance shortage problems, etc.',
                'icon': '✅',
                'color': '#F59E0B',
                'display_order': 5,
                'default_priority': 'medium',  # Regular issue
            },
            {
                'name': 'Library Issues',
                'code': 'library',
                'description': 'Library card issues, book availability, fine disputes, book return problems, library access issues, etc.',
                'icon': '📚',
                'color': '#06B6D4',
                'display_order': 6,
                'default_priority': 'low',  # Non-urgent
            },
            {
                'name': 'Hostel & Accommodation',
                'code': 'hostel',
                'description': 'Hostel room allotment, room change requests, hostel facilities, mess food quality, hostel fees, etc.',
                'icon': '🏠',
                'color': '#EC4899',
                'display_order': 7,
                'default_priority': 'medium',  # Living conditions
            },
            {
                'name': 'Infrastructure & Facilities',
                'code': 'infrastructure',
                'description': 'Classroom facilities, lab equipment issues, washroom problems, drinking water, electricity, internet/WiFi issues, etc.',
                'icon': '🏢',
                'color': '#14B8A6',
                'display_order': 8,
                'default_priority': 'medium',  # Facility issues
            },
            {
                'name': 'Faculty & Teaching',
                'code': 'faculty_teaching',
                'description': 'Issues with teaching quality, faculty behavior, class cancellations, syllabus coverage, practical sessions, etc.',
                'icon': '👨‍🏫',
                'color': '#6366F1',
                'display_order': 9,
                'default_priority': 'high',  # Academic quality
            },
            {
                'name': 'ID Card & Documents',
                'code': 'id_documents',
                'description': 'Student ID card issues, bonafide certificate, character certificate, NOC, recommendation letters, etc.',
                'icon': '🆔',
                'color': '#A855F7',
                'display_order': 10,
                'default_priority': 'medium',  # Document requests
            },
            {
                'name': 'Scholarship & Financial Aid',
                'code': 'scholarship',
                'description': 'Scholarship application issues, scholarship disbursement delays, financial aid queries, loan certificate, etc.',
                'icon': '🎓',
                'color': '#22C55E',
                'display_order': 11,
                'default_priority': 'high',  # Financial support
            },
            {
                'name': 'Placement & Training',
                'code': 'placement_training',
                'description': 'Placement cell issues, internship problems, training program queries, campus recruitment, etc.',
                'icon': '💼',
                'color': '#F97316',
                'display_order': 12,
                'default_priority': 'medium',  # Career related
            },
            {
                'name': 'Ragging & Harassment',
                'code': 'ragging_harassment',
                'description': 'Ragging complaints, harassment issues, bullying, discrimination, safety concerns, etc. (Urgent)',
                'icon': '⚠️',
                'color': '#DC2626',
                'display_order': 13,
                'default_priority': 'urgent',  # CRITICAL - Safety issue
            },
            {
                'name': 'Sports & Extra-curricular',
                'code': 'sports_extracurricular',
                'description': 'Sports facilities, sports equipment, cultural activities, club activities, event participation, etc.',
                'icon': '⚽',
                'color': '#84CC16',
                'display_order': 14,
                'default_priority': 'low',  # Extra-curricular
            },
            {
                'name': 'Transport & Commute',
                'code': 'transport',
                'description': 'College bus issues, bus pass problems, parking issues, transport schedule, route changes, etc.',
                'icon': '🚌',
                'color': '#0EA5E9',
                'display_order': 15,
                'default_priority': 'medium',  # Daily commute
            },
            {
                'name': 'Medical & Health',
                'code': 'medical_health',
                'description': 'Medical room facilities, health issues, medical emergency, first aid, health insurance, etc.',
                'icon': '🏥',
                'color': '#EF4444',
                'display_order': 16,
                'default_priority': 'urgent',  # Health emergency
            },
            {
                'name': 'Administrative Issues',
                'code': 'administrative',
                'description': 'General administrative problems, office staff behavior, document processing delays, etc.',
                'icon': '📁',
                'color': '#64748B',
                'display_order': 17,
                'default_priority': 'medium',  # Admin issues
            },
            {
                'name': 'Online Portal & Website',
                'code': 'online_portal',
                'description': 'Student portal login issues, website problems, online form submission, password reset, etc.',
                'icon': '💻',
                'color': '#7C3AED',
                'display_order': 18,
                'default_priority': 'medium',  # Technical issues
            },
            {
                'name': 'Other Issues',
                'code': 'other',
                'description': 'Any other issues not covered in the above categories',
                'icon': '❓',
                'color': '#9CA3AF',
                'display_order': 99,
                'default_priority': 'medium',  # General issues
            },
        ]

        created_count = 0
        updated_count = 0
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Creating Grievance Categories...\n'))
        
        for category_data in categories:
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
                # Update existing category
                for key, value in category_data.items():
                    setattr(category, key, value)
                category.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'🔄 Updated: {category.name} ({category.code})'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✨ Done! Created: {created_count}, Updated: {updated_count}\n'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'📊 Total Categories: {GrievanceCategory.objects.count()}\n'
            )
        )
