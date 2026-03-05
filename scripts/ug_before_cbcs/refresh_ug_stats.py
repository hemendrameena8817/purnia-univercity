# Usage: poetry run python scripts/ug_before_cbcs/refresh_ug_stats.py

import os
import sys
import django
import time

# Django setup
# Get the absolute path of the project root (2 levels up from this script)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from ug_before_cbcs.utils.stats import calculate_and_save_ug_before_cbcs_stats

def refresh_stats():
    print('Starting UG Before CBCS statistics recalculation...')
    start_time = time.time()
    
    try:
        stats_obj = calculate_and_save_ug_before_cbcs_stats()
        duration = round(time.time() - start_time, 2)
        
        print(f'Successfully updated statistics in {duration} seconds!')
        print(f'New Statistics UUID: {stats_obj.uid}')
        
    except Exception as e:
        print(f'An error occurred: {str(e)}')

if __name__ == "__main__":
    refresh_stats()

