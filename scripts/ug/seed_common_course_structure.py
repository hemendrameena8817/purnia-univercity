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

from ug.models import CommonCourseStructure

def seed_common_course_structure():
    data = [
        # Semester-I (verified from database)
        {"semester": "Semester-I", "course_name": "Major Course 1", "course_type": "MJC-1", "ltp": "6-1-0", "credit": 6, "marks": 100, "code":"1001"},
        {"semester": "Semester-I", "course_name": "Minor Course 1", "course_type": "MIC-1", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"1002"},
        {"semester": "Semester-I", "course_name": "Skill Enhancement Course", "course_type": "SEC-1", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"1003"},
        {"semester": "Semester-I", "course_name": "Value Added Course", "course_type": "VAC-1", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"1004"},
        {"semester": "Semester-I", "course_name": "Multidisciplinary Course 1", "course_type": "MDC-1", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"1005"},
        {"semester": "Semester-I", "course_name": "MIL", "course_type": "AEC-1", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"1006"},
        
        # Semester-II (verified from database)
        {"semester": "Semester-II", "course_name": "Major Course 2", "course_type": "MJC-2", "ltp": "6-1-0", "credit": 6, "marks": 100, "code":"2001"},
        {"semester": "Semester-II", "course_name": "Minor Course 2", "course_type": "MIC-2", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"2002"},
        {"semester": "Semester-II", "course_name": "Skill Enhancement Course", "course_type": "SEC-2", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"2003"},
        {"semester": "Semester-II", "course_name": "Value Added Course", "course_type": "VAC-2", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"2004"},
        {"semester": "Semester-II", "course_name": "Multidisciplinary Course 2", "course_type": "MDC-2", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"2005"},
        {"semester": "Semester-II", "course_name": "Environmental Science", "course_type": "AEC-2", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"2006"},

        # Semester-III (verified from database)
        {"semester": "Semester-III", "course_name": "Major Course 3", "course_type": "MJC-3", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"3001"},
        {"semester": "Semester-III", "course_name": "Major Course 4", "course_type": "MJC-4", "ltp": "3-1-0", "credit": 4, "marks": 100, "code":"3002"},
        {"semester": "Semester-III", "course_name": "Minor Course 3", "course_type": "MIC-3", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"3003"},
        {"semester": "Semester-III", "course_name": "Skill Enhancement Course", "course_type": "SEC-3", "ltp": "1-0-3", "credit": 3, "marks": 100, "code":"3004"},
        {"semester": "Semester-III", "course_name": "Multidisciplinary Course 3", "course_type": "MDC-3", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"3005"},
        {"semester": "Semester-III", "course_name": "Ability Enhancing course (Course on Disaster Risk Management)", "course_type": "AEC-3", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"3006"},

        # Semester-IV (verified from database)
        {"semester": "Semester-IV", "course_name": "Major Course 5", "course_type": "MJC-5", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"4001"},
        {"semester": "Semester-IV", "course_name": "Major Course 6", "course_type": "MJC-6", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"4002"},
        {"semester": "Semester-IV", "course_name": "Major Course 7", "course_type": "MJC-7", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"4003"},
        {"semester": "Semester-IV", "course_name": "Minor Course 4", "course_type": "MIC-4", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"4004"},
        {"semester": "Semester-IV", "course_name": "Ability enhancing course (Course on NCC/ NSS/ NGO's /Social Service/ Scout & Guide / Sports)", "course_type": "AEC-4", "ltp": "2-1-0", "credit": 2, "marks": 100, "code":"4005"},

        # Semester-V (verified from database)
        {"semester": "Semester-V", "course_name": "Major Course 8", "course_type": "MJC-8", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"5001"},
        {"semester": "Semester-V", "course_name": "Major Course 9", "course_type": "MJC-9", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"5002"},
        {"semester": "Semester-V", "course_name": "Minor Course 5", "course_type": "MIC-5", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"5003"},
        {"semester": "Semester-V", "course_name": "Minor Course 6", "course_type": "MIC-6", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"5004"},
        {"semester": "Semester-V", "course_name": "Internship", "course_type": "INT-1", "ltp": "-", "credit": 4, "marks": 100, "code":"5005"},

        # Semester-VI (verified from database)
        {"semester": "Semester-VI", "course_name": "Major Course 10", "course_type": "MJC-10", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"6001"},
        {"semester": "Semester-VI", "course_name": "Major Course 11", "course_type": "MJC-11", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"6002"},
        {"semester": "Semester-VI", "course_name": "Major Course 12", "course_type": "MJC-12", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"6003"},
        {"semester": "Semester-VI", "course_name": "Minor Course 7", "course_type": "MIC-7", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"6004"},
        {"semester": "Semester-VI", "course_name": "Minor Course 8", "course_type": "MIC-8", "ltp": "4-1-0", "credit": 3, "marks": 100, "code":"6005"},

        # Semester-VII (verified from database)
        {"semester": "Semester-VII", "course_name": "Major Course 13", "course_type": "MJC-13", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"7001"},
        {"semester": "Semester-VII", "course_name": "Major Course 14", "course_type": "MJC-14", "ltp": "5-1-0", "credit": 5, "marks": 100, "code":"7002"},
        {"semester": "Semester-VII", "course_name": "Major Course 15", "course_type": "MJC-15", "ltp": "6-1-0", "credit": 6, "marks": 100, "code":"7003"},
        {"semester": "Semester-VII", "course_name": "Minor Course 9", "course_type": "MIC-9", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"7004"},

        # Semester-VIII (verified from database)
        {"semester": "Semester-VIII", "course_name": "Major Course 16", "course_type": "MJC-16", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"8001"},
        {"semester": "Semester-VIII", "course_name": "Minor Course 10", "course_type": "MIC-10", "ltp": "4-1-0", "credit": 4, "marks": 100, "code":"8002"},
        {"semester": "Semester-VIII", "course_name": "Research Project/Dissertation", "course_type": "RP-1", "ltp": "-", "credit": 12, "marks": 100, "code":"8003"},
    ]

    print("Seeding CommonCourseStructure data...")
    for item in data:
        obj, created = CommonCourseStructure.objects.get_or_create(
            semester=item["semester"],
            course_type=item["course_type"],
            defaults={
                "course_name": item["course_name"],
                "ltp": item["ltp"],
                "credit": item["credit"],
                "marks": item["marks"],
                "code": item["code"]
            }
        )
        if created:
            print(f"✅ Created: {item['semester']} - {item['course_type']} (code: {item['code']})")
        else:
            # Update if already exists to ensure data matches database
            obj.course_name = item["course_name"]
            obj.ltp = item["ltp"]
            obj.credit = item["credit"]
            obj.marks = item["marks"]
            obj.code = item["code"]
            obj.save()
            print(f"📌 Updated: {item['semester']} - {item['course_type']} (code: {item['code']})")

    print("Done!")

if __name__ == "__main__":
    seed_common_course_structure()
