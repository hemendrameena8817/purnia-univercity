"""
Find college_reg_no values from student_ug table that don't exist 
in the registered_applicant_master table.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import debug settings to configure Django
from scripts import debug_settings

from staging.models import UGSemResultCurrent, RegisteredApplicantMaster
from django.db.models import Q

def find_missing_college_reg_nos():
    """Find college registration numbers not in registered_applicant_master."""
    print("=" * 80)
    print("FINDING MISSING COLLEGE REGISTRATION NUMBERS")
    print("=" * 80)
    print("\nSearching for college_reg_no values in UGSemResultCurrent that are not")
    print("found in RegisteredApplicantMaster...\n")
    
    # Get all unique college_reg_no from UGSemResultCurrent
    unique_reg_nos = UGSemResultCurrent.objects.filter(
        college_reg_no__isnull=False
    ).values_list('college_reg_no', flat=True).distinct()
    
    unique_reg_nos = set(unique_reg_nos)
    unique_reg_nos.discard('')
    unique_reg_nos.discard(None)
    
    total_students = len(unique_reg_nos)
    print(f"Total unique college_reg_no in UGSemResultCurrent: {total_students}")
    
    # Get all college_reg_no from registered_applicant_master
    applicant_lookup = {}
    for applicant in RegisteredApplicantMaster.objects.filter(college_reg_no__in=unique_reg_nos):
        applicant_lookup[applicant.college_reg_no] = applicant
    
    print(f"Found in RegisteredApplicantMaster: {len(applicant_lookup)}")
    
    # Find missing ones
    missing_reg_nos = []
    
    print("\nChecking each registration number...\n")
    
    for reg_no in unique_reg_nos:
        if reg_no not in applicant_lookup:
            # Get a sample result record for this reg_no
            result_record = UGSemResultCurrent.objects.filter(college_reg_no=reg_no).first()
            missing_reg_nos.append({
                'college_reg_no': reg_no,
                'student_name': result_record.student_name if result_record else 'N/A',
                'programme': result_record.programme if result_record else 'N/A',
                'session': result_record.session if result_record else 'N/A'
            })
    
    # Print results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ Found in RegisteredApplicantMaster: {len(applicant_lookup)}")
    print(f"❌ NOT found in RegisteredApplicantMaster: {len(missing_reg_nos)}")
    print("=" * 80)
    
    if missing_reg_nos:
        print("\nMISSING COLLEGE REGISTRATION NUMBERS:")
        print("-" * 80)
        print(f"{'Reg No':<20} {'Student Name':<30} {'Programme':<25} {'Session':<10}")
        print("-" * 80)
        
        for record in missing_reg_nos:
            print(f"{record['college_reg_no']:<20} {record['student_name']:<30} {record['programme']:<25} {record['session']:<10}")
        
        # Save to file
        output_file = 'missing_college_reg_nos.txt'
        with open(output_file, 'w') as f:
            f.write("MISSING COLLEGE REGISTRATION NUMBERS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total missing: {len(missing_reg_nos)}\n\n")
            f.write(f"{'Reg No':<20} {'Student Name':<30} {'Programme':<25} {'Session':<10}\n")
            f.write("-" * 80 + "\n")
            
            for record in missing_reg_nos:
                f.write(f"{record['college_reg_no']:<20} {record['student_name']:<30} {record['programme']:<25} {record['session']:<10}\n")
        
        print(f"\n✓ Results saved to: {output_file}")
    else:
        print("\n✓ All college_reg_no values exist in RegisteredApplicantMaster!")
    
    print("=" * 80)
    
    return missing_reg_nos

if __name__ == '__main__':
    find_missing_college_reg_nos()
