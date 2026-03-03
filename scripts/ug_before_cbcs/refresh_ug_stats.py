# python manage.py refresh_ug_stats

from django.core.management.base import BaseCommand
from ug_before_cbcs.utils.stats import calculate_and_save_ug_before_cbcs_stats
import time

class Command(BaseCommand):
    help = 'Recalculates and saves statistical overview of UG Before CBCS data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting UG Before CBCS statistics recalculation...'))
        start_time = time.time()
        
        try:
            stats_obj = calculate_and_save_ug_before_cbcs_stats()
            duration = round(time.time() - start_time, 2)
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully updated statistics in {duration} seconds!'
            ))
            self.stdout.write(f'New Statistics UUID: {stats_obj.uid}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
