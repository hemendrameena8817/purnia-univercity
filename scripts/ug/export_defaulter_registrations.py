import os
import sys
import django
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings.development')
django.setup()

from ug.models import UGExamResult

def main():
    target_sem = sys.argv[1] if len(sys.argv) > 1 else '1ST'
    
    print(f"Fetching registration numbers for '{target_sem}' semester back-exam eligible students...")

    # Fetch distinct registration numbers of students who failed or were promoted/partly qualified etc.
    reg_numbers = set(UGExamResult.objects.filter(
        semester=target_sem,
        semester_result__in=['FAIL', 'PROMOTED', 'PARTLY_QUALIFIED', 'DISQUALIFIED']
    ).values_list('student__registration_no', flat=True))
    
    # Remove any None or empty values just in case
    reg_numbers = {str(r).strip() for r in reg_numbers if r}
    
    total = len(reg_numbers)
    print(f"Found {total} unique registrations.")
    
    if total > 0:
        output_file = BASE_DIR / f"{target_sem.lower()}_sem_defaulter_registrations.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for reg in sorted(reg_numbers):
                f.write(f"{reg}\n")
                
        print(f"✅ Successfully exported registration numbers to: {output_file}")
    else:
        print("No eligible records found.")

if __name__ == '__main__':
    main()
