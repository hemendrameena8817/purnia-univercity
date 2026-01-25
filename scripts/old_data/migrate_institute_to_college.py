"""
Migrate Institute to College Script
===================================

Migrates data from StagingInstituteMaster table to College table.

HOW TO RUN:
-----------
poetry run python manage.py shell

Then:
>>> from scripts.old_data.migrate_institute_to_college import migrate
>>> migrate()

OR run directly:
poetry run python scripts/old_data/migrate_institute_to_college.py
"""

import os
import sys
import django

# Setup Django if running standalone
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
    django.setup()


def migrate():
    from staging.models import StagingInstituteMaster
    from colleges.models import College
    from university.models import University
    
    print("="*60)
    print("MIGRATING INSTITUTE MASTER TO COLLEGE")
    print("="*60)
    
    # Get the default university (or create one if doesn't exist)
    university = University.objects.first()
    if not university:
        print("⚠️  No university found! Creating default...")
        university = University.objects.create(
            name="Purnea University",
            short_name="PU"
        )
        print(f"   Created: {university.name}")
    else:
        print(f"   Using university: {university.name}")
    
    # Get all staging records that haven't been migrated
    staging_records = StagingInstituteMaster.objects.filter(is_migrated=False)
    total = staging_records.count()
    print(f"\n📊 Found {total} records to migrate")
    
    if total == 0:
        print("✅ No records to migrate!")
        return
    
    migrated = 0
    skipped = 0
    errors = []
    
    for record in staging_records:
        try:
            # Check if college with this code already exists
            if record.institute_code:
                existing = College.objects.filter(college_code=record.institute_code).first()
                if existing:
                    # Update existing record
                    existing.name = record.institute_name or existing.name
                    existing.address = record.institute_address or existing.address
                    existing.contact_no = record.contact_number or existing.contact_no
                    existing.website = record.website_address or existing.website
                    
                    existing.save()
                    
                    # Mark as migrated
                    record.is_migrated = True
                    record.migration_notes = f"Updated existing College: {existing.uid}"
                    record.save()
                    skipped += 1
                    continue
            
            # Create new College record
            college = College.objects.create(
                name=record.institute_name,
                college_code=record.institute_code,
                address=record.institute_address,
                contact_no=record.contact_number,
                website=record.website_address if record.website_address else None,
                principal=record.admin_name,
                university=university,
                is_active=record.record_status == '1' if record.record_status else True,
                json_data={
                    'legacy_institute_id': record.institute_id,
                    'institute_type': record.institute_type,
                    'location': record.location,
                    'logo_url': record.logo_url,
                    'image_url': record.image_url,
                    'enrollment_process': record.enrollment_process,
                    'admin_user_name': record.admin_user_name,
                    'affiliated_year': record.affiliated_year,
                    'created_on': record.created_on,
                    'updated_on': record.updated_on,
                }
            )
            
            # Mark staging record as migrated
            record.is_migrated = True
            record.migration_notes = f"Created College: {college.uid}"
            record.save()
            
            migrated += 1
            
        except Exception as e:
            errors.append(f"{record.institute_code}: {str(e)}")
            record.migration_notes = f"Error: {str(e)}"
            record.save()
    
    print(f"\n✅ Migration completed!")
    print(f"   New colleges created: {migrated}")
    print(f"   Existing colleges updated: {skipped}")
    print(f"   Errors: {len(errors)}")
    
    if errors:
        print("\n⚠️  Errors:")
        for e in errors[:5]:
            print(f"   - {e}")
    
    print(f"\n📊 Total colleges now: {College.objects.count()}")


if __name__ == '__main__':
    migrate()
