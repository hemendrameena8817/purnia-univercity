from ug.models import StudentCourseAssessment
from django.db.models import Count

print('Current course_type distribution:')
types = StudentCourseAssessment.objects.values('course_type').annotate(count=Count('id')).order_by('-count')
for t in types:
    ct = t['course_type'] or 'None'
    print(f'  {ct:10s}: {t["count"]:,}')

total_mjc_mic_mdc = StudentCourseAssessment.objects.filter(course_type__in=['MJC', 'MIC', 'MDC']).count()
total_gen = StudentCourseAssessment.objects.filter(course_type='GEN').count()
print(f'\nTotal MJC/MIC/MDC records: {total_mjc_mic_mdc:,}')
print(f'Total GEN records (not yet updated): {total_gen:,}')
print(f'Progress: {(total_mjc_mic_mdc/2335061)*100:.1f}% complete')
