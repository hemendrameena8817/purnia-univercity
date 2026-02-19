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
        parser.add_argument(
            '--sync-from-local',
            action='store_true',
            help='Update live profiles from local (default) database based on registration_no',
        )

    def handle(self, *args, **options):

        dry_run = options['dry_run']
        db_alias = options['database']
        sync_from_local = options['sync_from_local']
        
        if sync_from_local:
            if db_alias == 'default':
                self.stdout.write(self.style.ERROR("You must specify --database=live (or other target) when using --sync-from-local. Source is always 'default'."))
                return
            self.sync_profiles_from_local(db_alias, dry_run)
            return
        
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
        users_to_update = []
        updated_profile_count = 0
        updated_user_count = 0
        processed_count = 0
        
        # Fields to update
        profile_update_fields = ['first_name', 'last_name', 'mobile_no', 'college']
        user_update_fields = ['first_name', 'last_name', 'phone', 'college', 'current_profile']

        for profile in profiles:
            processed_count += 1
            if processed_count % 100 == 0:
                 self.stdout.write(f"Processed {processed_count}/{total_profiles}...", ending='\r')
                 self.stdout.flush()

            try:
                user = profile.user
            except UserAccount.DoesNotExist:
                continue

            profile_needs_save = False
            user_needs_save = False
            changes = []

            # --- Synchronize Names ---

            # 1. First Name
            u_first = user.first_name.strip() if user.first_name else ""
            p_first = profile.first_name.strip() if profile.first_name else ""

            if u_first and not p_first:
                # User has name, Profile missing -> Update Profile
                changes.append(f"Profile First: ''->'{u_first}'")
                profile.first_name = u_first
                profile_needs_save = True
            elif p_first and not u_first:
                # Profile has name, User missing -> Update User
                changes.append(f"User First: ''->'{p_first}'")
                user.first_name = p_first
                user_needs_save = True
            elif u_first and p_first and u_first != p_first:
                # Conflict -> Update Profile (User is source of truth)
                changes.append(f"Profile First: '{p_first}'->'{u_first}'")
                profile.first_name = u_first
                profile_needs_save = True

            # 2. Last Name
            u_last = user.last_name.strip() if user.last_name else ""
            p_last = profile.last_name.strip() if profile.last_name else ""

            if u_last and not p_last:
                changes.append(f"Profile Last: ''->'{u_last}'")
                profile.last_name = u_last
                profile_needs_save = True
            elif p_last and not u_last:
                changes.append(f"User Last: ''->'{p_last}'")
                user.last_name = p_last
                user_needs_save = True
            elif u_last and p_last and u_last != p_last:
                changes.append(f"Profile Last: '{p_last}'->'{u_last}'")
                profile.last_name = u_last
                profile_needs_save = True

            # --- Synchronize Mobile/Phone ---

            # 3. Mobile Number
            u_phone = user.phone.strip() if user.phone and user.phone != 'None' else ""
            p_mobile = profile.mobile_no.strip() if profile.mobile_no and profile.mobile_no != 'None' else ""

            if u_phone and not p_mobile:
                 changes.append(f"Profile Mobile: ''->'{u_phone}'")
                 profile.mobile_no = u_phone
                 profile_needs_save = True
            elif p_mobile and not u_phone:
                 changes.append(f"User Phone: ''->'{p_mobile}'")
                 user.phone = p_mobile
                 user_needs_save = True
            elif u_phone and p_mobile and u_phone != p_mobile:
                 changes.append(f"Profile Mobile: '{p_mobile}'->'{u_phone}'")
                 profile.mobile_no = u_phone
                 profile_needs_save = True

            # --- Synchronize College ---
            u_college = user.college
            p_college = profile.college

            if u_college and not p_college:
                changes.append(f"Profile College: None->'{u_college}'")
                profile.college = u_college
                profile_needs_save = True
            elif p_college and not u_college:
                changes.append(f"User College: None->'{p_college}'")
                user.college = p_college
                user_needs_save = True
            elif u_college and p_college and u_college != p_college:
                 # Conflict -> Create new linkage to match user
                 changes.append(f"Profile College: '{p_college}'->'{u_college}' (User Priority)")
                 profile.college = u_college
                 profile_needs_save = True
            
            # --- Synchronize Current Profile ---
            if user.current_profile != 'pg':
                changes.append(f"User Current Profile: '{user.current_profile}'->'pg'")
                user.current_profile = 'pg'
                user_needs_save = True

            if profile_needs_save:
                updated_profile_count += 1
                profiles_to_update.append(profile)
            
            if user_needs_save:
                updated_user_count += 1
                users_to_update.append(user)

            if (profile_needs_save or user_needs_save) and dry_run:
                 self.stdout.write(self.style.WARNING(f"\n[DRY RUN] {user.username}: {', '.join(changes)}"))
        
        self.stdout.write(f"\nFinished processing. Found {len(profiles_to_update)} profiles and {len(users_to_update)} users needing updates.")

        if not dry_run:
            if profiles_to_update:
                self.stdout.write("Saving profile changes with bulk_update...")
                PGStudentProfile.objects.using(db_alias).bulk_update(profiles_to_update, profile_update_fields, batch_size=1000)
                self.stdout.write(self.style.SUCCESS(f"Successfully bulk updated {len(profiles_to_update)} profiles."))
            
            if users_to_update:
                self.stdout.write("Saving user changes with bulk_update...")
                UserAccount.objects.using(db_alias).bulk_update(users_to_update, user_update_fields, batch_size=1000)
                self.stdout.write(self.style.SUCCESS(f"Successfully bulk updated {len(users_to_update)} users."))

        elif dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. Would have updated {len(profiles_to_update)} profiles and {len(users_to_update)} users."))
        else:
            self.stdout.write(self.style.SUCCESS("No updates needed."))

    def sync_profiles_from_local(self, target_db, dry_run):
        """
        Syncs existing profiles in target_db using data from default db.
        Assumes registration_no is the unique key.
        """
        self.stdout.write(self.style.SUCCESS(f"Starting Cross-DB Sync (Local -> {target_db})..."))

        # Fetch all target profiles
        target_profiles = PGStudentProfile.objects.using(target_db).all()
        total_target = target_profiles.count()
        self.stdout.write(f"Found {total_target} profiles in target DB ({target_db}).")

        # Prepare list of fields to sync (exclude system fields AND all FK/relation fields)
        # FK fields are excluded because local IDs may not exist in live's related tables
        exclude_fields = ['id', 'uid', 'user', 'created_at', 'updated_at']
        fields_to_sync = [
            f.name for f in PGStudentProfile._meta.fields 
            if f.name not in exclude_fields and not f.is_relation
        ]
        
        profiles_to_update = []
        processed_count = 0
        updated_count = 0

        # Pre-fetch local profiles into a dictionary for faster lookup
        # Warning: If local DB is huge, this might consume memory. 
        # But for 2500 profiles it's fine.
        self.stdout.write("Loading local profiles...")
        local_profiles_map = {
            p.registration_no: p 
            for p in PGStudentProfile.objects.using('default').all()
        }
        self.stdout.write(f"Loaded {len(local_profiles_map)} local profiles.")

        for target_profile in target_profiles:
            processed_count += 1
            if processed_count % 100 == 0:
                 self.stdout.write(f"Processed {processed_count}/{total_target}...", ending='\r')

            local_profile = local_profiles_map.get(target_profile.registration_no)
            
            if not local_profile:
                # No matching local profile, skip
                continue

            needs_save = False
            changes = []

            for field_name in fields_to_sync:
                # Only plain scalar fields (FK fields excluded above)
                local_val = getattr(local_profile, field_name)
                target_val = getattr(target_profile, field_name)

                if local_val != target_val:
                    changes.append(f"{field_name}: '{target_val}'->'{local_val}'")
                    setattr(target_profile, field_name, local_val)
                    needs_save = True
            
            if needs_save:
                updated_count += 1
                profiles_to_update.append(target_profile)
                if dry_run:
                    self.stdout.write(self.style.WARNING(f"\n[DRY RUN] {target_profile.registration_no}: {', '.join(changes)}"))

        self.stdout.write(f"\nFinished processing. Found {len(profiles_to_update)} profiles needing updates.")

        if not dry_run:
             if profiles_to_update:
                self.stdout.write("Saving changes...")
                # We ccan't use bulk_update easily with all fields without specifying them explicitl.
                # And bulk_update with 30+ fields might be heavy.
                # But it's better than N updates.
                PGStudentProfile.objects.using(target_db).bulk_update(profiles_to_update, fields_to_sync, batch_size=500)
                self.stdout.write(self.style.SUCCESS(f"Successfully updated {len(profiles_to_update)} profiles."))
        elif dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. Would have updated {len(profiles_to_update)} profiles."))
        else:
            self.stdout.write(self.style.SUCCESS("No updates needed."))
