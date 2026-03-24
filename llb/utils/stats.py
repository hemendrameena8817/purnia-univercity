from django.db.models import Count, F, Q
from ..models import (
    LLBStudentProfile, 
    LLBExam, 
    LLBStudentCourseAssessment, 
    LLBStatistics,
    LLBCourse,
    LLBBatch,
    LLBSession
)

def get_semester_stats(semester):
    """
    Calculates statistics for a specific semester (1ST, 2ND, 3RD, 4TH, 5TH, 6TH).
    """
    semester = semester.upper()
    
    # Get students with assessments in this semester
    students = LLBStudentProfile.objects.filter(
        course_assessments__semester=semester
    ).distinct().count()
    
    # Get total assessments in this semester
    assessments = LLBStudentCourseAssessment.objects.filter(
        semester=semester
    ).count()
    
    # Get pass/fail statistics
    pass_stats = LLBStudentCourseAssessment.objects.filter(
        semester=semester
    ).aggregate(
        total_assessments=Count('uid'),
        passed=Count('uid', filter=Q(ind_is_pass=True)),
        failed=Count('uid', filter=Q(ind_is_pass=False)),
        absent=Count('uid', filter=Q(ind_is_absent=True))
    )
    
    # Calculate pass percentage (excluding absent)
    total_taken = pass_stats['total_assessments'] - pass_stats['absent']
    pass_percentage = 0
    if total_taken > 0:
        pass_percentage = (pass_stats['passed'] / total_taken) * 100
    
    return {
        "students": students,
        "assessments": pass_stats['total_assessments'],
        "passed": pass_stats['passed'],
        "failed": pass_stats['failed'],
        "absent": pass_stats['absent'],
        "pass_percentage": round(pass_percentage, 2)
    }

def get_batch_stats():
    """
    Calculates batch-wise statistics for LLB.
    """
    batch_data = LLBStudentCourseAssessment.objects.filter(
        batch__isnull=False
    ).values(
        batch_name=F('batch__name'),
        assessment_semester=F('semester')
    ).annotate(
        student_count=Count('student', distinct=True),
        assessment_count=Count('uid'),
        passed=Count('uid', filter=Q(ind_is_pass=True)),
        failed=Count('uid', filter=Q(ind_is_pass=False)),
        absent=Count('uid', filter=Q(ind_is_absent=True))
    ).order_by('-batch_name', 'assessment_semester')

    batch_summary = {}
    for item in batch_data:
        batch_name = item['batch_name'] or "Unknown"
        if batch_name not in batch_summary:
            batch_summary[batch_name] = {
                "batch": batch_name,
                "semesters": {},
                "total_students": 0,
                "total_assessments": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_absent": 0
            }
        
        semester = item['assessment_semester'] or "Unknown"
        batch_summary[batch_name]["semesters"][semester] = {
            "students": item['student_count'],
            "assessments": item['assessment_count'],
            "passed": item['passed'],
            "failed": item['failed'],
            "absent": item['absent']
        }
        
        # Update totals
        batch_summary[batch_name]["total_students"] = max(
            batch_summary[batch_name]["total_students"], 
            item['student_count']
        )
        batch_summary[batch_name]["total_assessments"] += item['assessment_count']
        batch_summary[batch_name]["total_passed"] += item['passed']
        batch_summary[batch_name]["total_failed"] += item['failed']
        batch_summary[batch_name]["total_absent"] += item['absent']

    # Calculate pass percentages for each batch
    for batch_data in batch_summary.values():
        total_taken = batch_data["total_assessments"] - batch_data["total_absent"]
        batch_data["pass_percentage"] = 0
        if total_taken > 0:
            batch_data["pass_percentage"] = round((batch_data["total_passed"] / total_taken) * 100, 2)

    return list(batch_summary.values())

def get_course_stats():
    """
    Calculates course-wise statistics for LLB.
    """
    course_data = LLBStudentCourseAssessment.objects.filter(
        course__isnull=False
    ).values(
        course_name=F('course__name'),
        assessment_semester=F('semester')
    ).annotate(
        student_count=Count('student', distinct=True),
        assessment_count=Count('uid'),
        passed=Count('uid', filter=Q(ind_is_pass=True)),
        failed=Count('uid', filter=Q(ind_is_pass=False)),
        absent=Count('uid', filter=Q(ind_is_absent=True))
    ).order_by('course_name', 'assessment_semester')

    course_summary = {}
    for item in course_data:
        course_name = item['course_name'] or "Unknown"
        if course_name not in course_summary:
            course_summary[course_name] = {
                "course": course_name,
                "semesters": {},
                "total_students": 0,
                "total_assessments": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_absent": 0
            }
        
        semester = item['assessment_semester'] or "Unknown"
        course_summary[course_name]["semesters"][semester] = {
            "students": item['student_count'],
            "assessments": item['assessment_count'],
            "passed": item['passed'],
            "failed": item['failed'],
            "absent": item['absent']
        }
        
        # Update totals
        course_summary[course_name]["total_students"] = max(
            course_summary[course_name]["total_students"], 
            item['student_count']
        )
        course_summary[course_name]["total_assessments"] += item['assessment_count']
        course_summary[course_name]["total_passed"] += item['passed']
        course_summary[course_name]["total_failed"] += item['failed']
        course_summary[course_name]["total_absent"] += item['absent']

    # Calculate pass percentages for each course
    for course_data in course_summary.values():
        total_taken = course_data["total_assessments"] - course_data["total_absent"]
        course_data["pass_percentage"] = 0
        if total_taken > 0:
            course_data["pass_percentage"] = round((course_data["total_passed"] / total_taken) * 100, 2)

    return list(course_summary.values())

def get_exam_stats():
    """
    Calculates exam-wise statistics.
    """
    exam_data = LLBStudentCourseAssessment.objects.filter(
        exam__isnull=False
    ).values(
        exam_name=F('exam__name'),
        exam_month_year=F('exam__exam_month_year'),
        exam_semester=F('exam__semester')
    ).annotate(
        student_count=Count('student', distinct=True),
        assessment_count=Count('uid'),
        passed=Count('uid', filter=Q(ind_is_pass=True)),
        failed=Count('uid', filter=Q(ind_is_pass=False)),
        absent=Count('uid', filter=Q(ind_is_absent=True))
    ).order_by('-exam_month_year', 'exam_semester')

    exam_summary = {}
    for item in exam_data:
        exam_key = f"{item['exam_name']} ({item['exam_month_year']})"
        if exam_key not in exam_summary:
            exam_summary[exam_key] = {
                "exam": exam_key,
                "exam_month_year": item['exam_month_year'],
                "semesters": {},
                "total_students": 0,
                "total_assessments": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_absent": 0
            }
        
        semester = item['exam_semester'] or "Unknown"
        exam_summary[exam_key]["semesters"][semester] = {
            "students": item['student_count'],
            "assessments": item['assessment_count'],
            "passed": item['passed'],
            "failed": item['failed'],
            "absent": item['absent']
        }
        
        # Update totals
        exam_summary[exam_key]["total_students"] = max(
            exam_summary[exam_key]["total_students"], 
            item['student_count']
        )
        exam_summary[exam_key]["total_assessments"] += item['assessment_count']
        exam_summary[exam_key]["total_passed"] += item['passed']
        exam_summary[exam_key]["total_failed"] += item['failed']
        exam_summary[exam_key]["total_absent"] += item['absent']

    # Calculate pass percentages for each exam
    for exam_data in exam_summary.values():
        total_taken = exam_data["total_assessments"] - exam_data["total_absent"]
        exam_data["pass_percentage"] = 0
        if total_taken > 0:
            exam_data["pass_percentage"] = round((exam_data["total_passed"] / total_taken) * 100, 2)

    return list(exam_summary.values())

def calculate_and_save_llb_stats():
    """
    Recalculates all LLB statistics and saves them to the LLBStatistics model.
    """
    # Get all unique semesters
    semesters = list(LLBStudentCourseAssessment.objects.exclude(
        semester__isnull=True
    ).exclude(
        semester=''
    ).values_list('semester', flat=True).distinct().order_by('semester'))
    
    semester_stats = {}
    for semester in semesters:
        semester_stats[semester.lower()] = get_semester_stats(semester)

    # Compile final data
    data = {
        "semester_stats": semester_stats,
        "batch_wise": get_batch_stats(),
        "course_wise": get_course_stats(),
        "exam_wise": get_exam_stats(),
        "global": {
            "total_students": LLBStudentProfile.objects.count(),
            "total_courses": LLBCourse.objects.count(),
            "total_batches": LLBBatch.objects.count(),
            "total_sessions": LLBSession.objects.count(),
            "total_exams": LLBExam.objects.count(),
            "total_assessments": LLBStudentCourseAssessment.objects.count(),
            "total_passed": LLBStudentCourseAssessment.objects.filter(ind_is_pass=True).count(),
            "total_failed": LLBStudentCourseAssessment.objects.filter(ind_is_pass=False).count(),
            "total_absent": LLBStudentCourseAssessment.objects.filter(ind_is_absent=True).count()
        }
    }

    # Calculate global pass percentage
    total_assessments = data["global"]["total_assessments"]
    total_absent = data["global"]["total_absent"]
    total_taken = total_assessments - total_absent
    if total_taken > 0:
        data["global"]["pass_percentage"] = round((data["global"]["total_passed"] / total_taken) * 100, 2)
    else:
        data["global"]["pass_percentage"] = 0

    # Save to cache model
    stats_obj = LLBStatistics.objects.create(data=data)
    data["last_updated"] = stats_obj.last_updated.isoformat()
    stats_obj.data = data
    stats_obj.save()

    # Keep only the latest 5 entries 
    old_ids = list(LLBStatistics.objects.order_by('-last_updated').values_list('pk', flat=True)[5:])
    if old_ids:
        LLBStatistics.objects.filter(pk__in=old_ids).delete()
    
    return stats_obj
