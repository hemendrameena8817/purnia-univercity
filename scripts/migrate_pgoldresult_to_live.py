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

BATCH_SIZE = 1000   # rows per bulk_create batch


# ─── Helper ───────────────────────────────────────────────────────────────────

def get_existing_uids(model, db):
    """Return a set of uid strings already present in the target DB."""
    return set(str(u) for u in model.objects.using(db).values_list('uid', flat=True))


# ─── Step 1: Migrate PGOldStudentProfile ─────────────────────────────────────

def migrate_profiles():
    print("\n" + "="*70)
    print("STEP 1 — Migrating PGOldStudentProfile  (local → live)")
    print("="*70)

    local_profiles = list(PGOldStudentProfile.objects.using(SOURCE_DB).all())
    print(f"   📊 Local records  : {len(local_profiles):,}")

    existing_uids  = get_existing_uids(PGOldStudentProfile, TARGET_DB)
    print(f"   📊 Already on live: {len(existing_uids):,}")

    to_insert = [
        p for p in local_profiles if str(p.uid) not in existing_uids
    ]
    print(f"   📦 New to insert  : {len(to_insert):,}")

    if not to_insert:
        print("   ✅ Nothing to migrate for profiles.")
        return

    # Re-create objects without PKs so live DB auto-assigns its own IDs.
    new_objects = []
    for p in to_insert:
        new_objects.append(PGOldStudentProfile(
            uid               = p.uid,           # keep UUID for dedup
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
            # FK fields (college, user) set to None — adjust if needed on live
            college           = None,
            user              = None,
        ))

    inserted = 0
    with transaction.atomic(using=TARGET_DB):
        for i in range(0, len(new_objects), BATCH_SIZE):
            batch = new_objects[i:i + BATCH_SIZE]
            PGOldStudentProfile.objects.using(TARGET_DB).bulk_create(
                batch, batch_size=BATCH_SIZE, ignore_conflicts=True
            )
            inserted += len(batch)
            print(f"      ↳ Inserted batch {i // BATCH_SIZE + 1}  ({inserted:,} so far)")

    print(f"   ✅ Profiles migrated: {inserted:,}")


# ─── Step 2: Migrate PGOldResult ──────────────────────────────────────────────

def migrate_results():
    print("\n" + "="*70)
    print("STEP 2 — Migrating PGOldResult  (local → live)")
    print("="*70)

    total_local = PGOldResult.objects.using(SOURCE_DB).count()
    print(f"   📊 Local records  : {total_local:,}")

    existing_uids = get_existing_uids(PGOldResult, TARGET_DB)
    print(f"   📊 Already on live: {len(existing_uids):,}")

    # Build a uid → live profile-id map for FK linking
    live_profile_map = {
        str(uid): pk
        for uid, pk in PGOldStudentProfile.objects.using(TARGET_DB).values_list('uid', 'id')
    }

    inserted = 0
    skipped  = 0
    offset   = 0

    while True:
        local_batch = list(
            PGOldResult.objects.using(SOURCE_DB)
            .select_related('student_profile')
            .all()[offset: offset + BATCH_SIZE]
        )
        if not local_batch:
            break

        new_objects = []
        for r in local_batch:
            if str(r.uid) in existing_uids:
                skipped += 1
                continue

            # Resolve live FK for student_profile
            live_profile_id = None
            if r.student_profile_id:
                # Get the UUID of the local profile
                try:
                    local_prof_uid = str(
                        PGOldStudentProfile.objects.using(SOURCE_DB)
                        .filter(id=r.student_profile_id)
                        .values_list('uid', flat=True)
                        .first()
                    )
                    live_profile_id = live_profile_map.get(local_prof_uid)
                except Exception:
                    pass

            new_objects.append(PGOldResult(
                uid                 = r.uid,
                student_profile_id  = live_profile_id,
                source_id           = r.source_id,
                user_id             = r.user_id,
                college_roll_no     = r.college_roll_no,
                college_reg_no      = r.college_reg_no,
                student_name        = r.student_name,
                fathers_name        = r.fathers_name,
                mothers_name        = r.mothers_name,
                semester_code       = r.semester_code,
                batch_code          = r.batch_code,
                session_code        = r.session_code,
                course_code         = r.course_code,
                discipline_code     = r.discipline_code,
                paper_code          = r.paper_code,
                subject_code        = r.subject_code,
                subject_name        = r.subject_name,
                faculty             = r.faculty,
                status              = r.status,
                exam_type_his       = r.exam_type_his,
                exam_type           = r.exam_type,
                maximum_mark        = r.maximum_mark,
                pass_mark           = r.pass_mark,
                mark_secured        = r.mark_secured,
                subject_total_mark  = r.subject_total_mark,
                subject_ca          = r.subject_ca,
                subject_ng          = r.subject_ng,
                subject_ce          = r.subject_ce,
                subject_gp          = r.subject_gp,
                total_ca            = r.total_ca,
                total_ce            = r.total_ce,
                subject_result      = r.subject_result,
                final_result        = r.final_result,
                grand_total_mark    = r.grand_total_mark,
                total_secured_mark  = r.total_secured_mark,
                total_per           = r.total_per,
                institute_code      = r.institute_code,
                gpa                 = r.gpa,
                cgpa                = r.cgpa,
                numrical_let_grad   = r.numrical_let_grad,
                let_grad_sub        = r.let_grad_sub,
                let_grad            = r.let_grad,
                dsc_grad            = r.dsc_grad,
                agreegate           = r.agreegate,
                grade               = r.grade,
                record_status       = r.record_status,
                final_sheet_status  = r.final_sheet_status,
                student_name_hindi  = r.student_name_hindi,
                max_total_mark      = r.max_total_mark,
                pg_faculty          = r.pg_faculty,
                pg_department       = r.pg_department,
                pg_degree           = r.pg_degree,
                pg_program          = r.pg_program,
                college             = None,      # FK to College — adjust if needed
                copied_from_staging = r.copied_from_staging,
            ))

        if new_objects:
            with transaction.atomic(using=TARGET_DB):
                PGOldResult.objects.using(TARGET_DB).bulk_create(
                    new_objects, batch_size=BATCH_SIZE, ignore_conflicts=True
                )
            inserted += len(new_objects)

        offset += BATCH_SIZE
        print(f"   ↳ Processed {offset:,} | Inserted so far: {inserted:,} | Skipped: {skipped:,}")

    print(f"\n   ✅ PGOldResult migration done — Inserted: {inserted:,}  Skipped (already on live): {skipped:,}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def migrate():
    print("\n" + "=" * 70)
    print(" PGOldResult Local → Live Migration")
    print(f" SOURCE : {SOURCE_DB}  (local)")
    print(f" TARGET : {TARGET_DB}  (live)")
    print("=" * 70)

    start = time.time()

    migrate_profiles()
    migrate_results()

    elapsed = time.time() - start
    print(f"\n🎉 ALL DONE in {elapsed:.1f}s")


if __name__ == '__main__':
    migrate()
