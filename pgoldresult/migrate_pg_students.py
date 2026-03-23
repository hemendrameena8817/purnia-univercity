#!/usr/bin/env python
"""
Data Migration Script: Transfer PG student data from PGOldResult to PGOldStudentProfile
Run this script to create student profiles from existing PGOldResult data
"""

import os
import sys
import django

# Setup Django - Fix the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis.settings')
django.setup()

from pgoldresult.models import PGOldResult, PGOldStudentProfile
from colleges.models import College


def transfer_pg_students():
    """
    Transfer unique students from PGOldResult to PGOldStudentProfile
    """
    print("🚀 Starting PG Student Data Transfer...")
    
    # Get unique students from PGOldResult
    unique_students = PGOldResult.objects.values(
        'college_reg_no',
        'college_roll_no',
        'student_name',
        'student_name_hindi',
        'fathers_name',
        'mothers_name',
        'course_code',
        'discipline_code',
        'batch_code',
        'final_result',
        'gpa',
        'cgpa',
        'total_per',
        'pg_faculty',
        'pg_department',
        'pg_degree',
        'pg_program',
        'user_id'
    ).distinct()
    
    print(f"📊 Found {unique_students.count()} unique students")
    
    created_count = 0
    updated_count = 0
    error_count = 0
    
    for student_data in unique_students:
        try:
            # Get college if available
            college = None
            # You can add college lookup logic here based on your data
            
            # Create or update student profile
            profile, created = PGOldStudentProfile.objects.update_or_create(
                registration_no=student_data['college_reg_no'] or f"TEMP_{student_data['college_roll_no']}",
                defaults={
                    'roll_no': student_data['college_roll_no'],
                    'student_name': student_data['student_name'] or 'Unknown',
                    'student_name_hindi': student_data['student_name_hindi'],
                    'fathers_name': student_data['fathers_name'],
                    'mothers_name': student_data['mothers_name'],
                    'college': college,
                    'course_code': student_data['course_code'],
                    'discipline_code': student_data['discipline_code'],
                    'batch_code': student_data['batch_code'],
                    'final_result': student_data['final_result'],
                    'gpa': student_data['gpa'],
                    'cgpa': student_data['cgpa'],
                    'total_percentage': student_data['total_per'],
                    'pg_faculty': student_data['pg_faculty'],
                    'pg_department': student_data['pg_department'],
                    'pg_degree': student_data['pg_degree'],
                    'pg_program': student_data['pg_program'],
                    'source_user_id': student_data['user_id'],
                }
            )
            
            if created:
                created_count += 1
                print(f"✅ Created profile: {profile.registration_no} - {profile.student_name}")
            else:
                updated_count += 1
                print(f"🔄 Updated profile: {profile.registration_no} - {profile.student_name}")
                
        except Exception as e:
            error_count += 1
            print(f"❌ Error processing student {student_data.get('college_reg_no', 'Unknown')}: {str(e)}")
    
    print(f"\n📈 Transfer Summary:")
    print(f"  ✅ Created: {created_count} profiles")
    print(f"  🔄 Updated: {updated_count} profiles")
    print(f"  ❌ Errors: {error_count} profiles")
    print(f"  📊 Total processed: {unique_students.count()}")


def link_results_to_profiles():
    """
    Link PGOldResult records to PGOldStudentProfile
    """
    print("\n🔗 Linking Results to Student Profiles...")
    
    results = PGOldResult.objects.filter(student_profile__isnull=True)
    print(f"📊 Found {results.count()} results to link")
    
    linked_count = 0
    error_count = 0
    
    for result in results:
        try:
            # Find student profile by registration number or roll number
            profile = None
            
            if result.college_reg_no:
                profile = PGOldStudentProfile.objects.filter(
                    registration_no=result.college_reg_no
                ).first()
            
            if not profile and result.college_roll_no:
                profile = PGOldStudentProfile.objects.filter(
                    roll_no=result.college_roll_no
                ).first()
            
            if profile:
                result.student_profile = profile
                result.save()
                linked_count += 1
                print(f"✅ Linked result {result.id} to profile {profile.registration_no}")
            else:
                print(f"⚠️  No profile found for result {result.id} (Reg: {result.college_reg_no}, Roll: {result.college_roll_no})")
                
        except Exception as e:
            error_count += 1
            print(f"❌ Error linking result {result.id}: {str(e)}")
    
    print(f"\n📈 Linking Summary:")
    print(f"  ✅ Linked: {linked_count} results")
    print(f"  ❌ Errors: {error_count} results")


if __name__ == "__main__":
    print("🎯 PG Student Data Migration Script")
    print("=" * 50)
    
    # Step 1: Transfer student data to profiles
    transfer_pg_students()
    
    # Step 2: Link results to profiles
    link_results_to_profiles()
    
    print("\n🎉 Migration Complete!")
    print("You can now use PGOldStudentProfile for easy student management")
