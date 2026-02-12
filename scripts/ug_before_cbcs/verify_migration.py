import os
import sys
import django

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from staging.models import UGResultCurrent
from ug_before_cbcs.models import (
    UGBeforeCBCSStudentProfile,
    UGBeforeCBCSExamRegistration,
    UGBeforeCBCSStudentAssessment,
    UGBeforeCBCSExamResult
)

def verify_migration():
    """
    Verify the migration status by comparing staging data with migrated data
    """
    print("=" * 80)
    print("UG BEFORE CBCS MIGRATION VERIFICATION")
    print("=" * 80)
    
    # 1. Count staging records
    staging_total = UGResultCurrent.objects.count()
    staging_students = UGResultCurrent.objects.values('college_reg_no').distinct().count()
    
    print(f"\n📊 STAGING DATA (UGResultCurrent):")
    print(f"   - Total Records: {staging_total:,}")
    print(f"   - Unique Students: {staging_students:,}")
    
    # 2. Count migrated data
    profiles = UGBeforeCBCSStudentProfile.objects.count()
    registrations = UGBeforeCBCSExamRegistration.objects.count()
    assessments = UGBeforeCBCSStudentAssessment.objects.count()
    results = UGBeforeCBCSExamResult.objects.count()
    
    print(f"\n📊 MIGRATED DATA (UG Before CBCS):")
    print(f"   - Student Profiles: {profiles:,}")
    print(f"   - Exam Registrations: {registrations:,}")
    print(f"   - Student Assessments: {assessments:,}")
    print(f"   - Exam Results: {results:,}")
    
    # 3. Check for unmigrated students
    staging_reg_nos = set(UGResultCurrent.objects.values_list('college_reg_no', flat=True).distinct())
    migrated_reg_nos = set(UGBeforeCBCSStudentProfile.objects.values_list('registration_no', flat=True))
    
    unmigrated = staging_reg_nos - migrated_reg_nos
    unmigrated = {r for r in unmigrated if r}  # Remove None/empty
    
    print(f"\n🔍 MIGRATION STATUS:")
    print(f"   - Staging Students: {len(staging_reg_nos):,}")
    print(f"   - Migrated Students: {len(migrated_reg_nos):,}")
    print(f"   - Unmigrated Students: {len(unmigrated):,}")
    
    if unmigrated:
        print(f"\n⚠️  Sample Unmigrated Registration Numbers:")
        for reg_no in list(unmigrated)[:10]:
            print(f"      - {reg_no}")
    
    # 4. Data integrity check
    print(f"\n✅ DATA INTEGRITY:")
    
    # Students with profiles but no registrations
    students_no_reg = UGBeforeCBCSStudentProfile.objects.filter(exam_registrations__isnull=True).count()
    print(f"   - Students without exam registrations: {students_no_reg:,}")
    
    # Registrations without assessments
    reg_no_assess = UGBeforeCBCSExamRegistration.objects.filter(assessments__isnull=True).count()
    print(f"   - Registrations without assessments: {reg_no_assess:,}")
    
    # Registrations without results
    reg_no_result = UGBeforeCBCSExamRegistration.objects.filter(result_summary__isnull=True).count()
    print(f"   - Registrations without results: {reg_no_result:,}")
    
    # 5. Summary
    print(f"\n" + "=" * 80)
    if len(unmigrated) == 0 and students_no_reg == 0:
        print("✅ MIGRATION COMPLETE - All data successfully migrated!")
    elif len(unmigrated) > 0:
        print(f"⚠️  MIGRATION IN PROGRESS - {len(unmigrated)} students remaining")
    else:
        print("✅ MIGRATION COMPLETE - Some data integrity issues detected")
    print("=" * 80)

if __name__ == "__main__":
    verify_migration()
