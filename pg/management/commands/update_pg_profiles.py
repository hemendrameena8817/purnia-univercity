from django.core.management.base import BaseCommand
from pg.models import PGStudentProfile
from accounts.models import UserAccount
from django.db import transaction
# python manage.py update_pg_profiles --database=live --dry-run
class Command(BaseCommand):
    help = 'Updates PG Student Profile details (Name, Mobile) from linked User Account'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the update without saving changes',
        )
        parser.add_argument(
            '--database',
            default='default',
            help='Specifies the database to use. Default is "default".',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        db_alias = options['database']
        
        self.stdout.write(self.style.SUCCESS(f'Starting PG Student Profile Update on database "{db_alias}"...'))
        
        # Use iterator to fetch efficiently
        # chunk_size is used by iterator since Django 2.0+
        profiles = PGStudentProfile.objects.using(db_alias).select_related('user').all().iterator(chunk_size=1000)
        
        # We can't get count() easily with iterator combined with complex filters efficiently sometimes,
        # but here we can just count first if we want, or skip it to save time.
        # Let's count first separately for progress bar.
        total_profiles = PGStudentProfile.objects.using(db_alias).count()
        self.stdout.write(f"Found approximately {total_profiles} profiles to check.")

        profiles_to_update = []
        updated_count = 0
        processed_count = 0
        
        # Fields to update
        update_fields = ['first_name', 'last_name', 'mobile_no']

        for profile in profiles:
            processed_count += 1
            if processed_count % 100 == 0:
                 self.stdout.write(f"Processed {processed_count}/{total_profiles}...", ending='\r')
                 self.stdout.flush()

            try:
                user = profile.user
            except UserAccount.DoesNotExist:
                continue

            needs_save = False
            changes = []

            # 1. First Name
            if user.first_name and profile.first_name != user.first_name:
                changes.append(f"First: '{profile.first_name}'->'{user.first_name}'")
                profile.first_name = user.first_name
                needs_save = True
            
            # 2. Last Name
            if user.last_name and profile.last_name != user.last_name:
                changes.append(f"Last: '{profile.last_name}'->'{user.last_name}'")
                profile.last_name = user.last_name
                needs_save = True

            # 3. Mobile Number
            if user.phone and profile.mobile_no != user.phone:
                changes.append(f"Mobile: '{profile.mobile_no}'->'{user.phone}'")
                profile.mobile_no = user.phone
                needs_save = True

            if needs_save:
                updated_count += 1
                profiles_to_update.append(profile)
                if dry_run:
                     self.stdout.write(self.style.WARNING(f"\n[DRY RUN] {user.username}: {', '.join(changes)}"))
        
        self.stdout.write(f"\nFinished processing. Found {len(profiles_to_update)} profiles needing updates.")

        if profiles_to_update and not dry_run:
            self.stdout.write("Saving changes with bulk_update...")
            # bulk_update in batches of 1000
            PGStudentProfile.objects.using(db_alias).bulk_update(profiles_to_update, update_fields, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f"Successfully bulk updated {len(profiles_to_update)} profiles."))
        elif dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. Would have updated {len(profiles_to_update)} profiles."))
        else:
            self.stdout.write(self.style.SUCCESS("No updates needed."))
