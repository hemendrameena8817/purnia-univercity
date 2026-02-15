
import os
import sys
import django
from django.db.models import Q, F

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug.models import UGStudentProfile, UGDepartment

def sync_mic_mdc_fix():
    print("Fixing Invalid Live Profiles (Major==MIC or Major==MDC) from Local Data...")
    
    # 1. Load Live Departments map (Code -> Dept Object)
    print("Loading LIVE departments...")
    try:
        live_depts = UGDepartment.objects.using('live').filter(is_publish=True)
        live_dept_map = {d.code.upper(): d for d in live_depts}
        print(f"Loaded {len(live_dept_map)} live departments.")
    except Exception as e:
        print(f"Error connecting to LIVE DB: {e}")
        return

    # 2. Find Broken Profiles in LIVE
    print("Finding broken profiles in LIVE (Major==MIC or Major==MDC)...")
    
    # 'major_course' is the correct field name
    broken_live_profiles = UGStudentProfile.objects.using('live').filter(
        Q(major_course=F('minor_course')) | Q(major_course=F('mdc_course'))
    ).select_related('user', 'major_course', 'minor_course', 'mdc_course')
    
    total_broken = broken_live_profiles.count()
    print(f"Found {total_broken} broken profiles in LIVE.")
    
    if total_broken == 0:
        print("No broken profiles found. Exiting.")
        return

    count = 0
    updated = 0
    skipped = 0
    missing_local = 0
    
    # Process in chunks
    for live_prof in broken_live_profiles.iterator(chunk_size=2000):
        count += 1
        if count % 100 == 0:
            print(f"Processed {count}/{total_broken}...")
            
        username = live_prof.user.username
        
        # 3. Fetch Correct Data from LOCAL (default)
        try:
            local_prof = UGStudentProfile.objects.using('default').select_related(
                'mdc_course', 'minor_course'
            ).get(user__username=username)
        except UGStudentProfile.DoesNotExist:
            print(f"  [WARN] User {username} not found in LOCAL DB.")
            missing_local += 1
            continue
            
        needs_save = False
        log_msg = []
        
        # Check Major vs MIC issue
        if live_prof.major_course_id and live_prof.minor_course_id and (live_prof.major_course_id == live_prof.minor_course_id):
            # Major == MIC in Live. Fix from Local.
            if local_prof.minor_course:
                local_code = local_prof.minor_course.code.upper()
                live_mic = live_dept_map.get(local_code)
                
                if live_mic:
                    if live_prof.minor_course != live_mic:
                        live_prof.minor_course = live_mic
                        needs_save = True
                        log_msg.append(f"Fixed MIC ({local_code})")
        
        # Check Major vs MDC issue
        if live_prof.major_course_id and live_prof.mdc_course_id and (live_prof.major_course_id == live_prof.mdc_course_id):
            # Major == MDC in Live. Fix from Local.
            if local_prof.mdc_course:
                local_code = local_prof.mdc_course.code.upper()
                live_mdc = live_dept_map.get(local_code)
                
                if live_mdc:
                    if live_prof.mdc_course != live_mdc:
                        live_prof.mdc_course = live_mdc
                        needs_save = True
                        log_msg.append(f"Fixed MDC ({local_code})")
        
        if needs_save:
            live_prof.save(using='live')
            updated += 1
            print(f"  [UPDATE] {username}: {', '.join(log_msg)}")
        else:
            skipped += 1

    print("-" * 30)
    print(f"Total Broken Scanned: {count}")
    print(f"Fixed/Updated in Live: {updated}")
    print(f"Skipped (Local matched live or no fix available): {skipped}")
    print(f"Missing in Local DB: {missing_local}")

if __name__ == "__main__":
    sync_mic_mdc_fix()
