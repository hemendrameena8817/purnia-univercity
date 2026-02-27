from django.db.models import Count, F
from ..models import (
    UGBeforeCBCSStudentProfile, 
    UGBeforeCBCSExam, 
    UGBeforeCBCSStudentResult, 
    UGBeforeCBCSStatistics
)

def calculate_and_save_ug_before_cbcs_stats():
    """
    Recalculates all statistics and saves them to the UGBeforeCBCSStatistics model.
    """
    # 1. BA Part-wise statistics
    ba_qs_part1 = UGBeforeCBCSStudentProfile.objects.filter(course_code='BA', results__exam__part='PART1')
    ba_part1_students = ba_qs_part1.distinct().count()
    ba_part1_assessments = UGBeforeCBCSStudentResult.objects.filter(student__course_code='BA', exam__part='PART1').count()

    ba_qs_part2 = UGBeforeCBCSStudentProfile.objects.filter(course_code='BA', results__exam__part='PART2')
    ba_part2_students = ba_qs_part2.distinct().count()
    ba_part2_assessments = UGBeforeCBCSStudentResult.objects.filter(student__course_code='BA', exam__part='PART2').count()

    ba_qs_part3 = UGBeforeCBCSStudentProfile.objects.filter(course_code='BA', results__exam__part='PART3')
    ba_part3_students = ba_qs_part3.distinct().count()
    ba_part3_assessments = UGBeforeCBCSStudentResult.objects.filter(student__course_code='BA', exam__part='PART3').count()

    # 2. BA Batch-wise Statistics
    ba_batch_data = UGBeforeCBCSStudentResult.objects.filter(
        student__course_code='BA'
    ).values(
        batch=F('exam__batch_code'),
        part=F('exam__part')
    ).annotate(
        student_count=Count('student', distinct=True),
        assessment_count=Count('uid')
    ).order_by('-batch', 'part')

    batch_summary = {}
    for item in ba_batch_data:
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
            course_code='BA', 
            results__exam__batch_code=b_item["batch"]
        ).distinct().count()

    # 3. Compile final data
    data = {
        "counts": {
            "ba": {
                "part_summary": {
                    "part1": {"students": ba_part1_students, "assessments": ba_part1_assessments},
                    "part2": {"students": ba_part2_students, "assessments": ba_part2_assessments},
                    "part3": {"students": ba_part3_students, "assessments": ba_part3_assessments}
                },
                "batch_wise": final_batch_list,
                "total_students": UGBeforeCBCSStudentProfile.objects.filter(course_code='BA').count()
            },
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
