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
from ug.models import SemesterRegistration, StudentCourseAssessment
from accounts.permissions import CanManageMarks
from ug.models import UGDepartment
from colleges.models import College
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

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


class UGDepartmentListView(APIView):
    """
    GET /api/ug/cia/departments/

    Returns all published departments to be shown in the UI dropdown.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, CanManageMarks]

    def get(self, request):

        departments = UGDepartment.objects.filter(is_publish=True).order_by('name')
        data = [{'uid': str(d.uid), 'code': d.code, 'name': d.name} for d in departments]

        return Response({
            'count': len(data),
            'departments': data
        })


class CIAStudentListView(APIView):
    """
    GET /api/ug/cia/students/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ── Validate required params ──────────────────────────────────────────
        sem = request.GET.get('sem')
        session = request.GET.get('session')
        course_type_filter = request.GET.get('course_type', '').upper().strip()
        department_uid = request.GET.get('department_uid', '').strip()
        search_term = request.GET.get('search', '').strip()
        label_filter = request.GET.get('label', '').strip()
        entry_status = request.GET.get('entry_status', 'all').lower().strip()

        exam_type = request.GET.get('exam_type', '').upper().strip()

        errors = {}
        if not sem or not sem.isdigit():
            errors['sem'] = 'Required. Must be a number (e.g. 3).'
        if not session:
            errors['session'] = 'Required (e.g. 2025-26).'
        if not course_type_filter or course_type_filter not in COURSE_TYPE_PREFIXES:
            errors['course_type'] = f'Required. Must be one of: {", ".join(COURSE_TYPE_PREFIXES)}'
        # if exam_type not in ('REGULAR', 'BACK'):
        #     errors['exam_type'] = 'Must be REGULAR or BACK.'
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        sem = int(sem)
        SEM_TEXT_MAP = {
            1: '1ST', 2: '2ND', 3: '3RD', 4: '4TH',
            5: '5TH', 6: '6TH', 7: '7TH', 8: '8TH',
        }
        semester_text = SEM_TEXT_MAP.get(sem, str(sem))

        # ── Determine college scope ───────────────────────────────────────────
        college = None
        if request.user.user_type == 'university_admin':
            college_code = request.GET.get('college_code', '').strip()
            if college_code:
                college = College.objects.filter(college_code=college_code).first()
                if not college:
                    return Response({'error': 'College not found.'}, status=404)
        else:
            # College User - use college mapped directly to UserAccount
            college = getattr(request.user, 'college', None)
            if not college:
                return Response({'error': 'No college associated with your account.'}, status=403)

        # ── Fetch Assessments directly ────────────────────────────────────────
        prefix = COURSE_TYPE_PREFIXES[course_type_filter]
        
        # We always check for both Theory and Practical to pair them
        labels_to_fetch = ['CIA-Theory', 'CIA-Practical']
        
        # Build optimized query matching the index [college_code, session, semester, course_type]
        # and ensuring alignment with student's UserAccount college mapping
        filter_kwargs = {
            'session': session,
            'semester': semester_text,
            'label__in': labels_to_fetch,
            'course_type__startswith': prefix,
            'student__user__college': college  # Map via UserAccount as requested
        }
        
        if college:
            filter_kwargs['college_code'] = college.college_code

        qs = StudentCourseAssessment.objects.filter(**filter_kwargs).select_related(
            'student', 'student__user', 'student__college', 'student__major_course', 'department'
        )

        # Department filtering: Only for MJC, MIC, MDC (Major/Minor)
        if course_type_filter in ('MJC', 'MIC', 'MDC'):
            if department_uid:
                qs = qs.filter(department__uid=department_uid)
        elif course_type_filter in ('AEC', 'SEC'):
            if department_uid:
                qs = qs.filter(
                    student__major_course__uid=department_uid,
                )

        if search_term:
            qs = qs.filter(
                Q(student__roll_no__icontains=search_term) |
                Q(student__registration_no__icontains=search_term)
            )
        
        # ── Grouping by Student & Paper ──────────────
        # We fetch all to group faithfully, as pagination must be on the result rows.
        all_assessments = list(qs.order_by('student__registration_no', 'paper_code', 'label'))
        
        grouped_map = {}
        for a in all_assessments:
            key = (a.student_id, (a.paper_code or "").upper().strip())
            if key not in grouped_map:
                s = a.student
                grouped_map[key] = {
                    'student_name': f"{s.first_name or ''} {s.last_name or ''}".strip(),
                    'registration_no': s.registration_no,
                    'roll_no': s.roll_no,
                    'paper_code': a.paper_code,
                    'course_name': a.course_name,
                    'course_type': a.course_type,
                    'course_code': a.course_code,
                    'department': a.department.name if a.department else None,
                    'cia_theory': None,
                    'cia_practical': None
                }
            
            comp_data = {
                'assessment_uid': str(a.uid),
                'ind_max_marks': a.ind_max_marks,
                'ind_marks_obtained': str(a.ind_marks_obtained) if a.ind_marks_obtained is not None else None,
                'ind_is_absent': a.ind_is_absent,
                'is_cia_filled': a.is_cia_filled,
                'cia_filled_on': a.cia_filled_on.isoformat() if a.cia_filled_on else None,
                'is_carried_forward': (a.exam_type == 'BACK' and a.created_at == a.updated_at) # Simplistic check or use custom flag
            }
            if a.label == 'CIA-Theory':
                grouped_map[key]['cia_theory'] = comp_data
            else:
                grouped_map[key]['cia_practical'] = comp_data

        # ── Final Pairing & Filtering ─────────────────────────────────────────
        final_rows = []
        is_history = request.GET.get('history', 'false').lower() == 'true'

        for row in grouped_map.values():
            theory = row.get('cia_theory')
            pract = row.get('cia_practical')
            
            has_filled = False
            has_pending = False
            
            if theory:
                if theory['is_cia_filled']: has_filled = True
                else: has_pending = True
            else:
                row['cia_theory'] = "N/A"
                
            if pract:
                if pract['is_cia_filled']: has_filled = True
                else: has_pending = True
            else:
                row['cia_practical'] = "N/A"
            
            # Apply Filter based on history param
            if is_history:
                # History mode: Show rows that have at least one component filled
                if has_filled:
                    final_rows.append(row)
            else:
                # Pending mode (default): Show rows that have at least one component pending
                if has_pending:
                    final_rows.append(row)

        final_rows.sort(
            key=lambda row: (
                str(row.get('roll_no') or '').strip().lower(),
            )
        )

        # ── Pagination ────────────────────────────────────────────────────────
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 100)
        
        try:
            page_size = int(page_size)
            if page_size > 100: page_size = 100
        except ValueError:
            page_size = 100
            
        paginator = Paginator(final_rows, page_size)
        
        try:
            paginated_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            paginated_page = paginator.page(1)

        return Response({
            'college': college.name if college else 'All',
            'sem': sem,
            'session': session,
            'course_type': course_type_filter,
            'exam_type': exam_type,
            'search': search_term,
            'history_mode': is_history,
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': paginated_page.number,
            'students': paginated_page.object_list,
        })


class CIAMarksSaveView(APIView):
    """
    PATCH /api/ug/cia/marks/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):

        marks_data = request.data.get('marks', [])
        if not marks_data or not isinstance(marks_data, list):
            return Response(
                {'error': "'marks' must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Scope: determine which college this user belongs to ───────────
        college = None
        if request.user.user_type != 'university_admin':
            college = getattr(request.user, 'college', None)
            if not college:
                return Response({'error': 'No college associated with your account.'}, status=status.HTTP_403_FORBIDDEN)

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
            # Handle empty string as None
            if isinstance(ind_marks, str) and ind_marks.strip() == "":
                ind_marks = None
                
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
        # Use indexed college_code for optimization
        qs = StudentCourseAssessment.objects.filter(uid__in=uids).select_related('student__user')

        if college:
            qs = qs.filter(college_code=college.college_code)

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
            
            # Update CIA fill status
            from django.utils import timezone
            assessment.is_cia_filled = True
            assessment.cia_filled_on = timezone.now()
            
            to_update.append(assessment)

        if validation_errors:
            return Response({'errors': validation_errors}, status=status.HTTP_400_BAD_REQUEST)

        StudentCourseAssessment.objects.bulk_update(
            to_update,
            ['ind_marks_obtained', 'ind_is_absent', 'is_cia_filled', 'cia_filled_on']
        )

        return Response({
            'message': f'CIA marks saved for {len(to_update)} assessment(s).',
            'updated_count': len(to_update),
        }, status=status.HTTP_200_OK)
