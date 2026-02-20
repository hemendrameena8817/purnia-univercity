"""
Script to run ESE Entry Generation.
"""
import os
import sys
import django
import argparse
from pathlib import Path

# Setup Project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

from pg.services.generate_ese_entries import generate_ese_entries

def main():
    parser = argparse.ArgumentParser(description="Generate ESE Assessment Entries for CIA Passed Students")
    
    parser.add_argument('--batch', type=str, help='Batch Code (e.g. 2023-25)')
    parser.add_argument('--semester', type=str, required=True, help='Semester (e.g. 1ST, 3RD)')
    parser.add_argument('--session', type=str, required=True, help='Session (e.g. 2024-25)')
    parser.add_argument('--dry-run', action='store_true', help='Dry Run Mode')
    parser.add_argument('--include-all-batches', action='store_true', help='Include all batches in session')
    
    args = parser.parse_args()
    
    generate_ese_entries(
        batch=args.batch,
        semester=args.semester,
        session=args.session,
        dry_run=args.dry_run,
        include_all_batches=args.include_all_batches
    )

if __name__ == "__main__":
    main()
