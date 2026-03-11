"""
- First see what will be deleted (safe preview)
poetry run python scripts/llb/clear_llb_data.py

- Then confirm and execute deletion
poetry run python scripts/llb/clear_llb_data.py --confirm
"""

import os
import sys
import django
from django.db import transaction

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from llb.models import (
    LLBStudentCourseAssessment, LLBStudentExamResult, LLBStudentProfile,
    LLBExam, LLBCourseStructure, CommonCourseStructure, LLBCourse,
    LLBSession, LLBBatch, LLBExamCenterMapping, LLBExamSchedule,
    LLBYearRegistration, LLBExamRegistration
)
from staging.models import StagingLLBResultCurrent

def clear_llb_data(confirm=False):
    if not confirm:
        print('⚠️  This will delete ALL LLB data!')
        print('To proceed, use: --confirm')
        return

    print('🗑️  Clearing LLB data...')

    try:
        with transaction.atomic():
            # Delete in order of dependencies (child to parent)
            deletion_order = [
                ('LLBStudentCourseAssessment', LLBStudentCourseAssessment),
                ('LLBStudentExamResult', LLBStudentExamResult),
                ('LLBYearRegistration', LLBYearRegistration),
                ('LLBExamRegistration', LLBExamRegistration),
                ('LLBExamSchedule', LLBExamSchedule),
                ('LLBExamCenterMapping', LLBExamCenterMapping),
                ('LLBExam', LLBExam),
                ('LLBStudentProfile', LLBStudentProfile),
                ('CommonCourseStructure', CommonCourseStructure),
                ('LLBCourseStructure', LLBCourseStructure),
                ('LLBCourse', LLBCourse),
                ('LLBSession', LLBSession),
                ('LLBBatch', LLBBatch),
            ]

            total_deleted = 0
            for model_name, model_class in deletion_order:
                count = model_class.objects.count()
                if count > 0:
                    model_class.objects.all().delete()
                    print(f'  ✅ Deleted {count:,} {model_name} records')
                    total_deleted += count
                else:
                    print(f'  ⏭️  No {model_name} records found')

            print(f'🎉 Successfully deleted {total_deleted:,} LLB records!')
            
            # Reset staging migration status
            print('\n🔄 Resetting staging migration status...')
            staging_count = StagingLLBResultCurrent.objects.filter(is_migrated=True).count()
            if staging_count > 0:
                StagingLLBResultCurrent.objects.all().update(is_migrated=False, migration_notes='')
                print(f'  ✅ Reset {staging_count:,} staging records to is_migrated=False')
            else:
                print('  ⏭️  No staging records to reset')
            
            print('\n📋 LLB data cleared and staging reset. Ready to start fresh!')

    except Exception as e:
        print(f'❌ Error clearing LLB data: {str(e)}')
        raise

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear all LLB related data to start fresh')
    parser.add_argument('--confirm', action='store_true', help='Confirm deletion of all LLB data')
    
    args = parser.parse_args()
    clear_llb_data(confirm=args.confirm)
