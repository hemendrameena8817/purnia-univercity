from django.core.management.base import BaseCommand
from pgoldresult.models import PGOldStudentProfile
from accounts.models import UserAccount

class Command(BaseCommand):
    help = 'Link existing student profiles to user accounts or create new ones'

    def add_arguments(self, parser):
        parser.add_argument('--create-missing', action='store_true',
                          help='Create user accounts for profiles without users')

    def handle(self, *args, **options):
        create_missing = options['create_missing']
        
        profiles_without_users = PGOldStudentProfile.objects.filter(user__isnull=True)
        total_profiles = profiles_without_users.count()
        
        self.stdout.write(f"Found {total_profiles} profiles without user accounts")
        
        linked_count = 0
        created_count = 0
        
        for profile in profiles_without_users:
            # Try to find existing user by registration_no
            user = UserAccount.objects.filter(username=profile.registration_no).first()
            
            if user:
                profile.user = user
                profile.save()
                linked_count += 1
                self.stdout.write(f"Linked profile {profile.registration_no} to existing user")
            elif create_missing:
                try:
                    # Create new user account
                    new_user = UserAccount.objects.create_user(
                        username=profile.registration_no,
                        email=f"{profile.registration_no}@student.local",
                        first_name=profile.student_name.split()[0] if profile.student_name else '',
                        last_name=' '.join(profile.student_name.split()[1:]) if profile.student_name and len(profile.student_name.split()) > 1 else ''
                    )
                    profile.user = new_user
                    profile.save()
                    created_count += 1
                    self.stdout.write(f"Created user for profile {profile.registration_no}")
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Could not create user for {profile.registration_no}: {e}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed! Linked: {linked_count}, Created: {created_count}"
            )
        )
