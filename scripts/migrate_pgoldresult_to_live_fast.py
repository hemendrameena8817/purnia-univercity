import os
import sys
import django
import time

# ── Django Setup ─────────────────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from django.db import transaction
from pgoldresult.models import PGOldResult, PGOldStudentProfile

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
#   SOURCE  = 'default'  → your local database
#   TARGET  = 'live'     → the live database (DB_NAME1 / DB_HOST1 in .env)
# ─────────────────────────────────────────────────────────────────────────────
SOURCE_DB = 'default'
TARGET_DB = 'live'

BATCH_SIZE = 10000   # Increased batch size for better performance
PROGRESS_INTERVAL = 5000  # Show progress every N records


# ─── Helper ─────────────────────────────────────────────────────────────────--

def get_existing_uids_optimized(model, db):
    """Return a set of uid strings already present in the target DB - optimized."""
    print(f"   🔍 Loading existing UIDs from {model.__name__}...")
    return set(str(u) for u in model.objects.using(db).values_list('uid', flat=True))


def create_profile_batch(profiles, college_cache, user_cache):
    """Create profile objects with optimized FK resolution."""
    new_objects = []
    for p in profiles:
        # Resolve college FK
        college = None
        if hasattr(p, 'college_id') and p.college_id:
            college = college_cache.get(p.college_id)
        
        # Resolve user FK  
        user = None
        if hasattr(p, 'user_id') and p.user_id:
            user = user_cache.get(p.user_id)
            
        new_objects.append(PGOldStudentProfile(
            uid               = p.uid,
            registration_no   = p.registration_no,
            roll_no           = p.roll_no,
            first_name        = p.first_name,
            hindi_name        = p.hindi_name,
            fathers_name      = p.fathers_name,
            mothers_name      = p.mothers_name,
            gender            = p.gender,
            dob               = p.dob,
            course_code       = p.course_code,
            discipline_code   = p.discipline_code,
            pg_faculty        = p.pg_faculty,
            pg_department     = p.pg_department,
            pg_degree         = p.pg_degree,
            pg_program        = p.pg_program,
            batch_code        = p.batch_code,
            current_semester  = p.current_semester,
            final_result      = p.final_result,
            gpa               = p.gpa,
            cgpa              = p.cgpa,
            total_percentage  = p.total_percentage,
            source_user_id    = p.source_user_id,
            address           = p.address,
            admission_date    = p.admission_date,
            date_of_birth     = p.date_of_birth,
            caste             = p.caste,
            enrollment_date   = p.enrollment_date,
            religion          = p.religion,
            nationality       = p.nationality,
            medium_of_student = p.medium_of_student,
            is_active         = p.is_active,
            college           = college,
            user              = user,
        ))
    return new_objects


# ─── Step 1: Migrate PGOldStudentProfile ─────────────────────────────────────

def migrate_profiles():
    print("\n" + "="*70)
    print("STEP 1 — Migrating PGOldStudentProfile  (local → live)")
    print("="*70)

    # Load all profiles at once with FK data
    print("   📊 Loading local profiles...")
    local_profiles = list(PGOldStudentProfile.objects.using(SOURCE_DB)
                          .select_related('college', 'user')
                          .all())
    print(f"   📊 Local records  : {len(local_profiles):,}")

    existing_uids = get_existing_uids_optimized(PGOldStudentProfile, TARGET_DB)
    print(f"   📊 Already on live: {len(existing_uids):,}")

    to_insert = [p for p in local_profiles if str(p.uid) not in existing_uids]
    print(f"   📦 New to insert  : {len(to_insert):,}")

    if not to_insert:
        print("   ✅ Nothing to migrate for profiles.")
        return

    # Pre-load FK objects for performance
    print("   🔄 Pre-loading foreign key objects...")
    college_cache = {}
    user_cache = {}
    
    # Cache colleges
    from colleges.models import College
    for college in College.objects.using(TARGET_DB).all():
        college_cache[college.id] = college
    
    # Cache users
    from accounts.models import UserAccount
    for user in UserAccount.objects.using(TARGET_DB).all():
        user_cache[user.id] = user

    # Process in large batches
    inserted = 0
    with transaction.atomic(using=TARGET_DB):
        for i in range(0, len(to_insert), BATCH_SIZE):
            batch = to_insert[i:i + BATCH_SIZE]
            new_objects = create_profile_batch(batch, college_cache, user_cache)
            
            PGOldStudentProfile.objects.using(TARGET_DB).bulk_create(
                new_objects, batch_size=min(1000, len(new_objects)), ignore_conflicts=True
            )
            inserted += len(new_objects)
            
            if (i + BATCH_SIZE) % PROGRESS_INTERVAL == 0 or i + BATCH_SIZE >= len(to_insert):
                print(f"      ↳ Inserted {inserted:,}/{len(to_insert):,} profiles ({(inserted/len(to_insert)*100):.1f}%)")

    print(f"   ✅ Profiles migrated: {inserted:,}")
    return inserted


# ─── Step 2: Migrate PGOldResult ──────────────────────────────────────────────

def migrate_results():
    print("\n" + "="*70)
    print("STEP 2 — Migrating PGOldResult  (local → live)")
    print("="*70)

    total_local = PGOldResult.objects.using(SOURCE_DB).count()
    print(f"   📊 Local records  : {total_local:,}")

    existing_uids = get_existing_uids_optimized(PGOldResult, TARGET_DB)
    print(f"   📊 Already on live: {len(existing_uids):,}")

    # Build profile UID → PK map for FK linking
    print("   🔗 Building profile mapping...")
    live_profile_map = {
        str(uid): pk for uid, pk in PGOldStudentProfile.objects.using(TARGET_DB)
        .values_list('uid', 'id')
    }
    print(f"   📊 Live profiles mapped: {len(live_profile_map):,}")

    # Pre-build local profile UID map
    print("   🔗 Building local profile mapping...")
    local_profile_uid_map = {
        str(uid): pk for uid, pk in PGOldStudentProfile.objects.using(SOURCE_DB)
        .values_list('uid', 'id')
    }

    inserted = 0
    skipped = 0
    processed = 0

    # Process results in optimized batches
    with transaction.atomic(using=TARGET_DB):
        batch_objects = []
        
        for result in PGOldResult.objects.using(SOURCE_DB).iterator(chunk_size=BATCH_SIZE):
            processed += 1
            
            if str(result.uid) in existing_uids:
                skipped += 1
                continue

            # Resolve live FK for student_profile
            live_profile_id = None
            if result.student_profile_id:
                local_prof_uid = local_profile_uid_map.get(str(result.student_profile_id))
                if local_prof_uid:
                    live_profile_id = live_profile_map.get(local_prof_uid)

            batch_objects.append(PGOldResult(
                uid                 = result.uid,
                student_profile_id  = live_profile_id,
                source_id           = result.source_id,
                user_id             = result.user_id,
                college_roll_no     = result.college_roll_no,
                college_reg_no      = result.college_reg_no,
                student_name        = result.student_name,
                fathers_name        = result.fathers_name,
                mothers_name        = result.mothers_name,
                semester_code       = result.semester_code,
                batch_code          = result.batch_code,
                session_code        = result.session_code,
                course_code         = result.course_code,
                discipline_code     = result.discipline_code,
                paper_code          = result.paper_code,
                subject_code        = result.subject_code,
                subject_name        = result.subject_name,
                faculty             = result.faculty,
                status              = result.status,
                exam_type_his       = result.exam_type_his,
                exam_type           = result.exam_type,
                maximum_mark        = result.maximum_mark,
                pass_mark           = result.pass_mark,
                mark_secured        = result.mark_secured,
                subject_total_mark  = result.subject_total_mark,
                subject_ca          = result.subject_ca,
                subject_ng          = result.subject_ng,
                subject_ce          = result.subject_ce,
                subject_gp          = result.subject_gp,
                total_ca            = result.total_ca,
                total_ce            = result.total_ce,
                subject_result      = result.subject_result,
                final_result        = result.final_result,
                grand_total_mark    = result.grand_total_mark,
                total_secured_mark  = result.total_secured_mark,
                total_per           = result.total_per,
                institute_code      = result.institute_code,
                gpa                 = result.gpa,
                cgpa                = result.cgpa,
                numrical_let_grad   = result.numrical_let_grad,
                let_grad_sub        = result.let_grad_sub,
                let_grad            = result.let_grad,
                dsc_grad            = result.dsc_grad,
                agreegate           = result.agreegate,
                grade               = result.grade,
                record_status       = result.record_status,
                final_sheet_status  = result.final_sheet_status,
                student_name_hindi  = result.student_name_hindi,
                max_total_mark      = result.max_total_mark,
                pg_faculty          = result.pg_faculty,
                pg_department       = result.pg_department,
                pg_degree           = result.pg_degree,
                pg_program          = result.pg_program,
                college             = None,
                copied_from_staging = result.copied_from_staging,
            ))

            # Bulk insert when batch is full
            if len(batch_objects) >= BATCH_SIZE:
                PGOldResult.objects.using(TARGET_DB).bulk_create(
                    batch_objects, batch_size=1000, ignore_conflicts=True
                )
                inserted += len(batch_objects)
                batch_objects = []
                
                if processed % PROGRESS_INTERVAL == 0:
                    progress = (processed / total_local) * 100
                    print(f"   ↳ Processed {processed:,}/{total_local:,} ({progress:.1f}%) | Inserted: {inserted:,} | Skipped: {skipped:,}")

        # Insert remaining records
        if batch_objects:
            PGOldResult.objects.using(TARGET_DB).bulk_create(
                batch_objects, batch_size=1000, ignore_conflicts=True
            )
            inserted += len(batch_objects)

    print(f"\n   ✅ PGOldResult migration done — Inserted: {inserted:,}  Skipped: {skipped:,}")
    return inserted


# ─── Main ─────────────────────────────────────────────────────────────────────

def migrate():
    print("\n" + "=" * 70)
    print(" PGOldResult Local → Live Migration (FAST VERSION)")
    print(f" SOURCE : {SOURCE_DB}  (local)")
    print(f" TARGET : {TARGET_DB}  (live)")
    print(f" BATCH SIZE : {BATCH_SIZE:,}")
    print("=" * 70)

    start = time.time()

    profile_count = migrate_profiles()
    result_count = migrate_results()

    elapsed = time.time() - start
    print(f"\n🎉 ALL DONE in {elapsed:.1f}s")
    print(f"   Profiles: {profile_count:,}")
    print(f"   Results: {result_count:,}")
    print(f"   Speed: {(profile_count + result_count) / elapsed:.0f} records/second")


if __name__ == '__main__':
    migrate()
