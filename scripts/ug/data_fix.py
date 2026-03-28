from django.db import transaction
from django.db.models import Prefetch

from ug.models import StudentCourseAssessment, UGStudentProfile, CourseStructure


def fix_assessment_data(dry_run=True, limit=None, semester=None, session=None):
    """
    Fix:
    1. department from student profile
    2. course_name from CourseStructure

    Args:
        dry_run (bool): If True → no DB update (preview only)
        limit (int): limit number of records (for testing)
        semester (str): filter by semester (e.g., '1ST', '2ND', '3RD')
        session (str): filter by session (e.g., '2025-26')
    """

    qs = StudentCourseAssessment.objects.select_related('student')
    
    if semester is not None:
        qs = qs.filter(semester=semester)
        print(f"Filtering for semester: {semester}")
    
    if session is not None:
        qs = qs.filter(session=session)
        print(f"Filtering for session: {session}")

    if limit:
        qs = qs[:limit]

    print(f"Total records to process: {qs.count() if not limit else limit}")

    # 🔥 Build CourseStructure map (avoid DB hit inside loop)
    course_map = {}
    course_qs = CourseStructure.objects.all()
    
    # Filter CourseStructure by semester if provided
    # Convert semester string (1ST, 2ND, 3RD) to integer (1, 2, 3) for CourseStructure
    if semester is not None:
        semester_mapping = {
            '1ST': '1', '2ND': '2', '3RD': '3', '4TH': '4',
            '5TH': '5', '6TH': '6', '7TH': '7', '8TH': '8'
        }
        course_semester = semester_mapping.get(semester, semester)
        course_qs = course_qs.filter(semester=course_semester)
        print(f"Loading CourseStructure for semester: {course_semester} (from {semester})")
    
    for c in course_qs.order_by('id'):
        key = (c.course_type, c.department_id)
        # take first occurrence only
        if key not in course_map:
            course_map[key] = c
    
    print(f"Loaded {len(course_map)} CourseStructure mappings")

    updated = 0
    skipped = 0

    with transaction.atomic():
        for obj in qs:
            student = obj.student

            if not student:
                skipped += 1
                continue

            # 🎯 Step 1: determine correct department
            if obj.course_type == "MJC":
                correct_dept = student.major_course
            elif obj.course_type == "MIC":
                correct_dept = student.minor_course
            elif obj.course_type == "MDC":
                correct_dept = student.mdc_course
            else:
                skipped += 1
                continue

            if not correct_dept:
                skipped += 1
                continue

            # 🎯 Step 2: get correct course from CourseStructure
            course = course_map.get((obj.course_type, correct_dept.id))

            new_department = correct_dept
            new_course_name = course.course_name if course else None

            changed = False

            if obj.department_id != correct_dept.id:
                changed = True

            if course and obj.course_name != new_course_name:
                changed = True

            if changed:
                updated += 1

                # 🔍 Preview mode
                if dry_run:
                    print({
                        "student": getattr(student.user, "username", None),
                        "course_type": obj.course_type,
                        "old_department": obj.department_id,
                        "new_department": correct_dept.id,
                        "old_course_name": obj.course_name,
                        "new_course_name": new_course_name,
                    })
                else:
                    obj.department = new_department
                    if course:
                        obj.course_name = new_course_name
                    obj.save(update_fields=['department', 'course_name'])

    print("\n✅ Done")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Dry run: {dry_run}")