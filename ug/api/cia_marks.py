"""
CIA Marks Entry API

Endpoints for colleges to view their students and enter CIA marks.

GET  /api/ug/cia/students/   — list students with their CIA assessment records
PATCH /api/ug/cia/marks/     — save CIA marks for one or multiple assessments

Permissions:
  - College user with can_manage_marks=True
  - OR university_admin (can pass ?college_code= to scope to a specific college)
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import CanManageMarks


# course_type prefixes that map to each filter category
COURSE_TYPE_PREFIXES = {
    'MJC': 'MJC',
    'MIC': 'MIC',
    'MDC': 'MDC',
    'AEC': 'AEC',
    'SEC': 'SEC',
    'VAC': 'VAC',
}

CIA_LABELS = ['CIA-Theory', 'CIA-Practical']


class CIAStudentListView(APIView):
    """
    GET /api/ug/cia/students/

    Required query params:
      - sem         : semester number (e.g. 3)
      - session     : e.g. 2025-26
      - course_type : MJC | MIC | MDC | AEC | SEC | VAC

    Optional query params:
      - department_code : filter by assessment department code (for MJC/MIC/MDC)
      - college_code    : university admin only — scope to a specific college
      - label           : CIA-Theory | CIA-Practical (default: all CIA labels)

    Returns a list of students with their CIA assessment records.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, CanManageMarks]

    def get(self, request):
        from ug.models import SemesterRegistration, StudentCourseAssessment

        # ── Validate required params ──────────────────────────────────────────
        sem = request.GET.get('sem')
        session = request.GET.get('session')
        course_type_filter = request.GET.get('course_type', '').upper().strip()
        department_code = request.GET.get('department_code', '').upper().strip()
        label_filter = request.GET.get('label', '').strip()

        errors = {}
        if not sem or not sem.isdigit():
            errors['sem'] = 'Required. Must be a number (e.g. 3).'
        if not session:
            errors['session'] = 'Required (e.g. 2025-26).'
        if not course_type_filter or course_type_filter not in COURSE_TYPE_PREFIXES:
            errors['course_type'] = f'Required. Must be one of: {", ".join(COURSE_TYPE_PREFIXES)}'
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        sem = int(sem)

        # ── Determine college scope ───────────────────────────────────────────
        college = None
        if request.user.user_type == 'university_admin':
            college_code = request.GET.get('college_code', '').strip()
            if college_code:
                from colleges.models import College
                college = College.objects.filter(college_code=college_code).first()
                if not college:
                    return Response(
                        {'error': f"College '{college_code}' not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
        else:
            # College user — auto-scope to their college
            if not hasattr(request.user, 'college_profile') or not request.user.college_profile:
                return Response(
                    {'error': 'No college profile associated with this user.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            college = request.user.college_profile.college
            if not college:
                return Response(
                    {'error': 'No college linked to your profile.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # ── Get REGISTERED students for this sem/session ──────────────────────
        reg_qs = SemesterRegistration.objects.filter(
            sem=sem,
            session=session,
            status='REGISTERED',
        )
        if college:
            reg_qs = reg_qs.filter(student__college=college)

        student_ids = list(reg_qs.values_list('student_id', flat=True).distinct())

        if not student_ids:
            return Response({
                'college': college.name if college else 'All',
                'sem': sem,
                'session': session,
                'course_type': course_type_filter,
                'count': 0,
                'students': []
            })

        # ── Build semester text for assessment filter ─────────────────────────
        SEM_TEXT_MAP = {
            1: '1ST', 2: '2ND', 3: '3RD', 4: '4TH',
            5: '5TH', 6: '6TH', 7: '7TH', 8: '8TH',
        }
        semester_text = SEM_TEXT_MAP.get(sem, str(sem))

        # ── Fetch CIA assessments filtered by course_type prefix ──────────────
        prefix = COURSE_TYPE_PREFIXES[course_type_filter]

        # CIA labels filter
        if label_filter and label_filter in CIA_LABELS:
            labels_to_fetch = [label_filter]
        else:
            labels_to_fetch = CIA_LABELS

        qs = StudentCourseAssessment.objects.filter(
            student_id__in=student_ids,
            semester=semester_text,
            session=session,
            label__in=labels_to_fetch,
        ).filter(
            course_type__startswith=prefix
        ).select_related(
            'student', 'student__college', 'department'
        ).order_by(
            'student__college__name',
            'student__registration_no',
            'course_type',
            'label',
        )

        # Optional: filter by department code (for MJC/MIC/MDC)
        if department_code and course_type_filter in ('MJC', 'MIC', 'MDC'):
            qs = qs.filter(department__code=department_code)

        # ── Serialize ─────────────────────────────────────────────────────────
        results = []
        for a in qs:
            s = a.student
            results.append({
                'assessment_uid': str(a.uid),
                'registration_no': s.registration_no,
                'student_name': f"{s.first_name or ''} {s.last_name or ''}".strip(),
                'roll_no': s.roll_no,
                'college_name': s.college.name if s.college else None,
                'college_code': s.college.college_code if s.college else None,
                'department': a.department.name if a.department else None,
                'department_code': a.department.code if a.department else None,
                'course_name': a.course_name,
                'course_type': a.course_type,
                'paper_code': a.paper_code,
                'label': a.label,
                'ind_max_marks': a.ind_max_marks,
                'ind_marks_obtained': str(a.ind_marks_obtained) if a.ind_marks_obtained is not None else None,
                'ind_is_absent': a.ind_is_absent,
            })

        return Response({
            'college': college.name if college else 'All',
            'sem': sem,
            'session': session,
            'course_type': course_type_filter,
            'count': len(results),
            'students': results,
        })


class CIAMarksSaveView(APIView):
    """
    PATCH /api/ug/cia/marks/

    Save CIA marks for one or more StudentCourseAssessment records.

    Request body:
    {
        "marks": [
            {
                "assessment_uid": "uuid",
                "ind_marks_obtained": 22,
                "ind_is_absent": false
            },
            ...
        ]
    }
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, CanManageMarks]

    def patch(self, request):
        from ug.models import StudentCourseAssessment

        marks_data = request.data.get('marks', [])
        if not marks_data or not isinstance(marks_data, list):
            return Response(
                {'error': "'marks' must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Scope: determine which student_ids this user can edit ─────────────
        college = None
        if request.user.user_type != 'university_admin':
            if not hasattr(request.user, 'college_profile') or not request.user.college_profile:
                return Response({'error': 'No college profile.'}, status=status.HTTP_403_FORBIDDEN)
            college = request.user.college_profile.college

        # ── Fetch and validate all assessments ────────────────────────────────
        uids = []
        marks_map = {}  # uid_str → entry
        errors = []

        for i, entry in enumerate(marks_data):
            uid = entry.get('assessment_uid')
            if not uid:
                errors.append({'index': i, 'error': 'assessment_uid is required.'})
                continue

            ind_marks = entry.get('ind_marks_obtained')
            is_absent = entry.get('ind_is_absent', False)

            if not is_absent:
                if ind_marks is None:
                    errors.append({'index': i, 'uid': uid, 'error': 'ind_marks_obtained is required when not absent.'})
                    continue
                try:
                    ind_marks = float(ind_marks)
                    if ind_marks < 0:
                        raise ValueError()
                except (ValueError, TypeError):
                    errors.append({'index': i, 'uid': uid, 'error': 'ind_marks_obtained must be a non-negative number.'})
                    continue

            marks_map[uid] = {
                'ind_marks_obtained': ind_marks if not is_absent else None,
                'ind_is_absent': bool(is_absent),
            }
            uids.append(uid)

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        # ── Fetch matching assessments from DB ────────────────────────────────
        qs = StudentCourseAssessment.objects.filter(uid__in=uids).select_related('student__college')

        if college:
            qs = qs.filter(student__college=college)

        found_uids = {str(a.uid): a for a in qs}

        # Check for UIDs not found or not belonging to this college
        missing = [u for u in uids if u not in found_uids]
        if missing:
            return Response(
                {'error': f"{len(missing)} assessment(s) not found or not accessible.", 'missing_uids': missing},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Validate marks against max and bulk update ─────────────────────────
        to_update = []
        validation_errors = []

        for uid_str, assessment in found_uids.items():
            entry = marks_map[uid_str]
            marks = entry['ind_marks_obtained']
            is_absent = entry['ind_is_absent']

            # Validate against max marks
            if marks is not None and assessment.ind_max_marks is not None:
                if marks > assessment.ind_max_marks:
                    validation_errors.append({
                        'uid': uid_str,
                        'error': f"Marks {marks} exceed max marks {assessment.ind_max_marks} for '{assessment.course_name}'."
                    })
                    continue

            assessment.ind_marks_obtained = marks
            assessment.ind_is_absent = is_absent
            to_update.append(assessment)

        if validation_errors:
            return Response({'errors': validation_errors}, status=status.HTTP_400_BAD_REQUEST)

        StudentCourseAssessment.objects.bulk_update(
            to_update,
            ['ind_marks_obtained', 'ind_is_absent']
        )

        return Response({
            'message': f'CIA marks saved for {len(to_update)} assessment(s).',
            'updated_count': len(to_update),
        }, status=status.HTTP_200_OK)
