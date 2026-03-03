from django.db.models import Count, F
from ..models import (
    UGBeforeCBCSStudentProfile, 
    UGBeforeCBCSExam, 
    UGBeforeCBCSStudentResult, 
    UGBeforeCBCSStatistics
)

def get_course_stats(course_code):
    """
    Calculates statistics for a specific course code (BA, BSC, BCOM).
    """
    course_code = course_code.upper()
    parts = ['PART1', 'PART2', 'PART3']
    part_summary = {}
    
    for part in parts:
        students = UGBeforeCBCSStudentProfile.objects.filter(
            course_code=course_code, 
            results__exam__part=part
        ).distinct().count()
        
        assessments = UGBeforeCBCSStudentResult.objects.filter(
            student__course_code=course_code, 
            exam__part=part
        ).count()
        
        part_summary[part.lower()] = {
            "students": students, 
            "assessments": assessments
        }

    # Batch-wise Statistics
    batch_data = UGBeforeCBCSStudentResult.objects.filter(
        student__course_code=course_code
    ).values(
        batch=F('exam__batch_code'),
        part=F('exam__part')
    ).annotate(
        student_count=Count('student', distinct=True),
        assessment_count=Count('uid')
    ).order_by('-batch', 'part')

    batch_summary = {}
    for item in batch_data:
        b_name = item['batch'] or "Unknown"
        if b_name not in batch_summary:
            batch_summary[b_name] = {
                "batch": b_name,
                "parts": {},
            }
        
        batch_summary[b_name]["parts"][item['part']] = {
            "students": item['student_count'],
            "assessments": item['assessment_count']
        }

    final_batch_list = list(batch_summary.values())
    for b_item in final_batch_list:
        b_item["total_students"] = UGBeforeCBCSStudentProfile.objects.filter(
            course_code=course_code, 
            results__exam__batch_code=b_item["batch"]
        ).distinct().count()

    return {
        "part_summary": part_summary,
        "batch_wise": final_batch_list,
        "total_students": UGBeforeCBCSStudentProfile.objects.filter(course_code=course_code).count()
    }

def calculate_and_save_ug_before_cbcs_stats():
    """
    Recalculates all statistics and saves them to the UGBeforeCBCSStatistics model.
    """
    # Get all unique course codes from student profiles
    courses = list(UGBeforeCBCSStudentProfile.objects.exclude(
        course_code__isnull=True
    ).exclude(
        course_code=''
    ).values_list('course_code', flat=True).distinct())
    
    course_counts = {}
    
    for course in courses:
        course_counts[course.lower()] = get_course_stats(course)

    # 3. Compile final data
    data = {
        "counts": {
            **course_counts,
            "global": {

                "total_students": UGBeforeCBCSStudentProfile.objects.count(),
                "total_exams": UGBeforeCBCSExam.objects.count(),
                "total_result_entries": UGBeforeCBCSStudentResult.objects.count()
            }
        },
        "last_updated": None 
    }

    # Save to cache model
    stats_obj = UGBeforeCBCSStatistics.objects.create(data=data)
    data["last_updated"] = stats_obj.last_updated.isoformat()
    stats_obj.data = data
    stats_obj.save()

    # Keep only the latest 5 entries 
    old_ids = list(UGBeforeCBCSStatistics.objects.order_by('-last_updated').values_list('pk', flat=True)[5:])
    if old_ids:
        UGBeforeCBCSStatistics.objects.filter(pk__in=old_ids).delete()
    
    return stats_obj

