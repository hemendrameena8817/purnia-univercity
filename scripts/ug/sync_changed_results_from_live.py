"""
Sync UGSemResultCurrent from LIVE → LOCAL DB.

Match key: college_reg_no + semester_code + exam_type + status + session_code + paper_code

STEP 1: Verify match by comparing 10 unchanged rows.
STEP 2: Sync is_changed=True rows.

Usage:
    poetry run python scripts/ug/sync_changed_results_from_live.py
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from staging.models import UGSemResultCurrent

LIVE_DB = 'live'
LOCAL_DB = 'default'

# Composite key fields for matching
MATCH_FIELDS = ['college_reg_no', 'semester_code', 'exam_type', 'status', 'session_code', 'paper_code']

# Fields to compare / sync
COMPARE_FIELDS = [
    'user_id', 'college_roll_no', 'college_reg_no',
    'student_name', 'fathers_name', 'mothers_name',
    'semester_code', 'batch_code', 'session_code',
    'course_code', 'discipline_code', 'paper_code',
    'subject_code', 'subject_name', 'faculty',
    'status', 'exam_type_his', 'exam_type',
    'maximum_mark', 'pass_mark', 'mark_secured',
    'subject_total_mark', 'grace_given', 'final_mark',
    'subject_total_mark_grace',
    'subject_ca', 'subject_ng', 'subject_ce', 'subject_gp',
    'total_gp', 'total_ca', 'total_ce',
    'subject_result', 'final_result', 'final_status',
    'grand_total_mark', 'total_secured_mark', 'total_per',
    'institute_code', 'gpa', 'cgpa',
    'numrical_let_grad', 'let_grad_sub', 'let_grad', 'dsc_grad',
    'is_grace', 'gpa_grace', 'record_status',
    'final_merit', 'final_sheet_status', 'student_name_hindi',
]


def make_key(obj):
    """Build composite match key from an object (model instance or dict)."""
    if isinstance(obj, dict):
        return tuple(str(obj.get(f) or '').strip() for f in MATCH_FIELDS)
    return tuple(str(getattr(obj, f, '') or '').strip() for f in MATCH_FIELDS)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: VERIFY COMPOSITE KEY MATCH
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("STEP 1: VERIFY COMPOSITE KEY MATCH")
print(f"Key: {' + '.join(MATCH_FIELDS)}")
print("=" * 70)

print("\n📡 Fetching 10 unchanged rows from LIVE DB...")
live_unchanged = list(
    UGSemResultCurrent.objects.using(LIVE_DB)
    .filter(is_changed=False)
    .order_by('id')[:10]
)

if not live_unchanged:
    print("❌ No unchanged rows found on LIVE DB.")
    sys.exit(1)

print(f"   Got {len(live_unchanged)} rows from LIVE\n")

all_match = True
verified = 0

for live_row in live_unchanged:
    key = make_key(live_row)
    lookup = dict(zip(MATCH_FIELDS, key))
    # Remove empty values from lookup to avoid matching empty strings
    lookup = {k: v for k, v in lookup.items() if v}

    local_row = UGSemResultCurrent.objects.using(LOCAL_DB).filter(**lookup).first()

    key_str = f"reg={live_row.college_reg_no}, sem={live_row.semester_code}, " \
              f"exam={live_row.exam_type}, paper={live_row.paper_code}"

    if not local_row:
        print(f"   ⚠️  NOT FOUND locally: {key_str}")
        all_match = False
        continue

    # Compare all fields
    mismatches = []
    for field in COMPARE_FIELDS:
        lv = str(getattr(live_row, field, '') or '').strip()
        lc = str(getattr(local_row, field, '') or '').strip()
        if lv != lc:
            mismatches.append(f"      {field}: LIVE='{lv}' vs LOCAL='{lc}'")

    if mismatches:
        print(f"   ❌ MISMATCH: {key_str}")
        for m in mismatches[:5]:
            print(m)
        if len(mismatches) > 5:
            print(f"      ... and {len(mismatches) - 5} more")
        all_match = False
    else:
        verified += 1
        print(f"   ✅ MATCH: {key_str} → all {len(COMPARE_FIELDS)} fields match")

print(f"\n{'─' * 70}")
print(f"Verified: {verified}/{len(live_unchanged)} rows match perfectly")

if not all_match:
    print("\n⚠️  NOT ALL ROWS MATCH. Check the mismatches above.")
    response = input("\nContinue to sync anyway? (y/n): ").strip().lower()
    if response != 'y':
        print("Stopped.")
        sys.exit(1)
else:
    print("\n✅ COMPOSITE KEY VERIFIED! All rows match.")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: SYNC CHANGED ROWS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 2: SYNC CHANGED ROWS (is_changed=True)")
print("=" * 70)

changed_count = UGSemResultCurrent.objects.using(LIVE_DB).filter(is_changed=True).count()
print(f"\n📡 Found {changed_count} changed rows on LIVE DB")

if changed_count == 0:
    print("✅ Nothing to sync!")
    sys.exit(0)

TEST_MODE = False
TEST_LIMIT = 10

if TEST_MODE:
    print(f"⚠️  TEST MODE: Only first {TEST_LIMIT} rows")

start = time.time()

live_changed = UGSemResultCurrent.objects.using(LIVE_DB).filter(is_changed=True).order_by('id')
if TEST_MODE:
    live_changed = live_changed[:TEST_LIMIT]

updated = 0
created = 0
skipped = 0
not_found = 0
errors = 0

for live_row in live_changed:
    try:
        key = make_key(live_row)
        lookup = dict(zip(MATCH_FIELDS, key))
        lookup = {k: v for k, v in lookup.items() if v}

        local_row = UGSemResultCurrent.objects.using(LOCAL_DB).filter(**lookup).first()

        key_str = f"reg={live_row.college_reg_no}, sem={live_row.semester_code}, paper={live_row.paper_code}"

        if local_row:
            changed_fields = []
            for field in COMPARE_FIELDS:
                lv = getattr(live_row, field, None)
                lc = getattr(local_row, field, None)
                if str(lv or '').strip() != str(lc or '').strip():
                    setattr(local_row, field, lv)
                    changed_fields.append(field)

            if changed_fields:
                local_row.is_changed = True
                local_row.save(using=LOCAL_DB)
                updated += 1
                print(f"   ✏️  Updated: {key_str} → changed: {', '.join(changed_fields[:3])}"
                      f"{'...' if len(changed_fields) > 3 else ''}")
            else:
                skipped += 1
        else:
            # Create new row
            new_data = {}
            for field in COMPARE_FIELDS:
                new_data[field] = getattr(live_row, field, None)
            new_data['is_changed'] = True
            new_data['source_id'] = str(live_row.id)

            new_obj = UGSemResultCurrent(**new_data)
            new_obj.save(using=LOCAL_DB)
            created += 1
            print(f"   🆕 Created: {key_str}")

    except Exception as e:
        print(f"   ❌ Error: {key_str} → {e}")
        errors += 1

elapsed = time.time() - start

print(f"\n{'=' * 70}")
print(f"✅ Updated:   {updated}")
print(f"🆕 Created:   {created}")
print(f"⏭  Skipped:   {skipped} (no changes)")
print(f"❌ Errors:    {errors}")
print(f"⏱  Time:      {elapsed:.1f}s")
print(f"{'=' * 70}")

if TEST_MODE and changed_count > TEST_LIMIT:
    print(f"\n⚠️  {changed_count - TEST_LIMIT} more rows remain. Set TEST_MODE = False for full sync.")
