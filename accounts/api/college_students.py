"""
College Student Management API — DRF Serializer-based implementation

Endpoints:
  GET  /api/accounts/college/students/                 list (paginated, searchable)
  GET  /api/accounts/college/students/<identifier>/    detail (reg_no or roll_no)
  PATCH /api/accounts/college/students/<identifier>/   partial update (multipart/form-data)

Access:
  college_user      — scoped to their own college; needs can_manage_students for PATCH
  university_admin  — can pass ?college_code= to scope; PATCH unrestricted

Profile types (?profile_type=):
  ug             → UGStudentProfile
  pg             → PGStudentProfile
  ug_before_cbcs → UGBeforeCBCSStudentProfile
  mba            → MBAStudentProfile
  mca_sem        → MCAStudentProfile
"""

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from ug.models import UGStudentProfile

PAGE_SIZE = 100


# ─────────────────────────────────────────────────────────────────────────────
# Per-profile ModelSerializers
# (defined lazily via factory to avoid circular imports at module load time)
# ─────────────────────────────────────────────────────────────────────────────

def _make_ug_serializer():
    from ug.models import UGStudentProfile

    class UGStudentProfileSerializer(serializers.ModelSerializer):
        # read-only convenience fields
        college_name = serializers.CharField(source='college.name', read_only=True)
        department_name = serializers.CharField(source='department.name', read_only=True, default=None)
        program_name = serializers.CharField(source='program.name', read_only=True, default=None)
        # Override: DB may store legacy short codes ('M'/'F') — skip choices enforcement
        gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)

        class Meta:
            model = UGStudentProfile
            fields = [
                'id', 'registration_no', 'roll_no',
                'first_name', 'last_name', 'hindi_name',
                'gender', 'date_of_birth', 'caste',
                'mobile_no', 'address',
                'father_name', 'mother_name',
                'aadhar_no', 'apaar_id',
                'admission_date', 'enrollment_date',
                'last_university', 'migration_submitted',
                'status', 'current_semester', 'session',
                'college', 'college_name',
                'department', 'department_name',
                'program', 'program_name',
                'profile_image', 'signature',
                'is_active', 'created_at', 'updated_at',
            ]
            read_only_fields = [
                'id', 'registration_no', 'college', 'college_name',
                'department_name', 'program_name',
                'created_at', 'updated_at',
            ]
            extra_kwargs = {
                'profile_image': {'required': False, 'allow_null': True},
                'signature': {'required': False, 'allow_null': True},
            }

    return UGStudentProfileSerializer


def _make_pg_serializer():
    from pg.models import PGStudentProfile

    class PGStudentProfileSerializer(serializers.ModelSerializer):
        college_name = serializers.CharField(source='college.name', read_only=True)
        department_name = serializers.CharField(source='department.name', read_only=True, default=None)
        program_name = serializers.CharField(source='program.name', read_only=True, default=None)
        gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)

        class Meta:
            model = PGStudentProfile
            fields = [
                'id', 'registration_no', 'roll_no',
                'first_name', 'last_name', 'hindi_name',
                'gender', 'date_of_birth', 'caste',
                'mobile_no', 'address',
                'father_name', 'mother_name',
                'aadhar_no', 'apaar_id',
                'admission_date', 'enrollment_date',
                'religion', 'nationality', 'medium_of_student',
                'last_university', 'migration_submitted',
                'status', 'current_semester', 'session',
                'college', 'college_name',
                'department', 'department_name',
                'program', 'program_name',
                'profile_image', 'signature',
                'is_active', 'created_at', 'updated_at',
            ]
            read_only_fields = [
                'id', 'registration_no', 'college', 'college_name',
                'department_name', 'program_name',
                'created_at', 'updated_at',
            ]
            extra_kwargs = {
                'profile_image': {'required': False, 'allow_null': True},
                'signature': {'required': False, 'allow_null': True},
            }

    return PGStudentProfileSerializer


def _make_ug_before_cbcs_serializer():
    from ug_before_cbcs.models import UGBeforeCBCSStudentProfile

    class UGBeforeCBCSSerializer(serializers.ModelSerializer):
        college_name = serializers.CharField(source='college.name', read_only=True)
        gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)

        class Meta:
            model = UGBeforeCBCSStudentProfile
            fields = [
                'id', 'registration_no', 'roll_no',
                'student_name', 'student_name_hindi',
                'fathers_name', 'mothers_name',
                'gender', 'dob',
                'college', 'college_name',
                'course_code', 'discipline_code',
                'is_active', 'created_at', 'updated_at',
            ]
            read_only_fields = [
                'id', 'registration_no', 'college', 'college_name',
                'created_at', 'updated_at',
            ]

    return UGBeforeCBCSSerializer


def _make_mba_serializer():
    from mba_sem.models import MBAStudentProfile

    class MBAStudentProfileSerializer(serializers.ModelSerializer):
        college_name = serializers.CharField(source='college.name', read_only=True)
        course_name = serializers.CharField(source='course.name', read_only=True, default=None)
        batch_name = serializers.CharField(source='batch.name', read_only=True, default=None)
        gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)

        class Meta:
            model = MBAStudentProfile
            fields = [
                'id', 'registration_no', 'roll_no',
                'first_name', 'last_name', 'hindi_name',
                'gender', 'date_of_birth', 'mobile_no', 'address',
                'father_name', 'mother_name', 'aadhar_no',
                'status', 'current_semester', 'session_str',
                'college', 'college_name',
                'course', 'course_name',
                'batch', 'batch_name',
                'profile_image', 'signature',
                'sem_1_gpa', 'sem_1_credit_earned',
                'sem_2_gpa', 'sem_2_credit_earned',
                'sem_3_gpa', 'sem_3_credit_earned',
                'sem_4_gpa', 'sem_4_credit_earned',
                'is_active', 'created_at', 'updated_at',
            ]
            read_only_fields = [
                'id', 'registration_no', 'college', 'college_name',
                'course_name', 'batch_name', 'created_at', 'updated_at',
            ]
            extra_kwargs = {
                'profile_image': {'required': False, 'allow_null': True},
                'signature': {'required': False, 'allow_null': True},
            }

    return MBAStudentProfileSerializer


def _make_mca_serializer():
    from mca_sem.models import MCAStudentProfile

    class MCAStudentProfileSerializer(serializers.ModelSerializer):
        college_name = serializers.CharField(source='college.name', read_only=True)
        course_name = serializers.CharField(source='course.name', read_only=True, default=None)
        batch_name = serializers.CharField(source='batch.name', read_only=True, default=None)
        gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)

        class Meta:
            model = MCAStudentProfile
            fields = [
                'id', 'registration_no', 'roll_no',
                'first_name', 'last_name', 'hindi_name',
                'gender', 'date_of_birth', 'mobile_no', 'address',
                'father_name', 'mother_name', 'aadhar_no',
                'status', 'current_semester', 'session_str',
                'college', 'college_name',
                'course', 'course_name',
                'batch', 'batch_name',
                'profile_image', 'signature',
                'is_active', 'created_at', 'updated_at',
            ]
            read_only_fields = [
                'id', 'registration_no', 'college', 'college_name',
                'course_name', 'batch_name', 'created_at', 'updated_at',
            ]
            extra_kwargs = {
                'profile_image': {'required': False, 'allow_null': True},
                'signature': {'required': False, 'allow_null': True},
            }

    return MCAStudentProfileSerializer


def _make_btech_serializer():
    from btech.models import BTechStudentProfile

    class BTechStudentProfileSerializer(serializers.ModelSerializer):
        college_name = serializers.CharField(source='college.name', read_only=True)
        course_name = serializers.CharField(source='course.name', read_only=True, default=None)
        branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)
        batch_name = serializers.CharField(source='batch.name', read_only=True, default=None)
        gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)

        class Meta:
            model = BTechStudentProfile
            fields = [
                'id', 'registration_no', 'roll_no',
                'first_name', 'last_name', 'hindi_name',
                'gender', 'date_of_birth', 'mobile_no', 'address',
                'father_name', 'mother_name', 'aadhar_no', 'apaar_id',
                'category', 'admission_date',
                'status', 'current_year', 'session_str',
                'college', 'college_name',
                'course', 'course_name',
                'branch', 'branch_name',
                'batch', 'batch_name',
                'profile_image', 'signature',
                'is_active', 'created_at', 'updated_at',
            ]
            read_only_fields = [
                'id', 'registration_no', 'college', 'college_name',
                'course_name', 'branch_name', 'batch_name',
                'created_at', 'updated_at',
            ]
            extra_kwargs = {
                'profile_image': {'required': False, 'allow_null': True},
                'signature': {'required': False, 'allow_null': True},
            }

    return BTechStudentProfileSerializer


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

PROFILE_REGISTRY = {
    'ug': {
        'get_model': lambda: __import__('ug.models', fromlist=['UGStudentProfile']).UGStudentProfile,
        'make_serializer': _make_ug_serializer,
        'reg_field': 'registration_no',
        'roll_field': 'roll_no',
        'first_name_field': 'first_name',
        'college_field': 'college',
        'first_name_sync': 'first_name',    # generic key whose value goes into user.first_name
        'last_name_sync': 'last_name',
    },
    'pg': {
        'get_model': lambda: __import__('pg.models', fromlist=['PGStudentProfile']).PGStudentProfile,
        'make_serializer': _make_pg_serializer,
        'reg_field': 'registration_no',
        'roll_field': 'roll_no',
        'first_name_field': 'first_name',
        'college_field': 'college',
        'first_name_sync': 'first_name',
        'last_name_sync': 'last_name',
    },
    'ug_before_cbcs': {
        'get_model': lambda: __import__('ug_before_cbcs.models', fromlist=['UGBeforeCBCSStudentProfile']).UGBeforeCBCSStudentProfile,
        'make_serializer': _make_ug_before_cbcs_serializer,
        'reg_field': 'registration_no',
        'roll_field': 'roll_no',
        'first_name_field': 'student_name',
        'college_field': 'college',
        'first_name_sync': 'student_name',
        'last_name_sync': None,
    },
    'mba': {
        'get_model': lambda: __import__('mba_sem.models', fromlist=['MBAStudentProfile']).MBAStudentProfile,
        'make_serializer': _make_mba_serializer,
        'reg_field': 'registration_no',
        'roll_field': 'roll_no',
        'first_name_field': 'first_name',
        'college_field': 'college',
        'first_name_sync': 'first_name',
        'last_name_sync': 'last_name',
    },
    'mca_sem': {
        'get_model': lambda: __import__('mca_sem.models', fromlist=['MCAStudentProfile']).MCAStudentProfile,
        'make_serializer': _make_mca_serializer,
        'reg_field': 'registration_no',
        'roll_field': 'roll_no',
        'first_name_field': 'first_name',
        'college_field': 'college',
        'first_name_sync': 'first_name',
        'last_name_sync': 'last_name',
    },
    'btech': {
        'get_model': lambda: __import__('btech.models', fromlist=['BTechStudentProfile']).BTechStudentProfile,
        'make_serializer': _make_btech_serializer,
        'reg_field': 'registration_no',
        'roll_field': 'roll_no',
        'first_name_field': 'first_name',
        'college_field': 'college',
        'first_name_sync': 'first_name',
        'last_name_sync': 'last_name',
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_college(request):
    """
    college_user     → returns their college (always)
    university_admin → returns None (sees all) or specific college if ?college_code=
    """
    user = request.user
    if user.user_type == 'university_admin':
        code = request.GET.get('college_code', '').strip()
        if code:
            from colleges.models import College
            c = College.objects.filter(college_code=code).first()
            if not c:
                return None, Response({'error': f"College '{code}' not found."}, status=status.HTTP_404_NOT_FOUND)
            return c, None
        return None, None

    cp = getattr(user, 'college_profile', None)
    if not cp or not cp.college:
        return None, Response({'error': 'No college associated with your profile.'}, status=status.HTTP_403_FORBIDDEN)
    print(f"[DEBUG] college_user={user.username}, college_pk={cp.college.pk}, college_code={cp.college.college_code}, college_name={cp.college.name}")
    return cp.college, None


def _find_student(identifier, college=None):
    """
    Search ALL profile tables for a student by reg_no or roll_no.
    If college is given, only search within that college (by college_code).
    Returns (profile, profile_type_key, conf) or (None, None, None).
    """
    from django.db.models import Q

    # First pass: find the student in any table to get their UserAccount.current_profile
    found_user = None
    for key, conf in PROFILE_REGISTRY.items():
        try:
            Model = conf['get_model']()
            qs = Model.objects.select_related('user', 'college')
            if college:
                filter_field = f"{conf['college_field']}__college_code"
                print(f"[DEBUG] _find_student: table={key}, filter={filter_field}={college.college_code}")
                qs = qs.filter(**{filter_field: college.college_code})
            else:
                print(f"[DEBUG] _find_student: table={key}, NO college filter (admin)")
            p = qs.filter(
                Q(**{f"{conf['reg_field']}__iexact": identifier}) |
                Q(**{f"{conf['roll_field']}__iexact": identifier})
            ).first()
            if p:
                print(f"[DEBUG] FOUND in table={key}, profile_pk={p.pk}, student_college_code={p.college.college_code if p.college else 'NO_COLLEGE'}")
                if p.user:
                    found_user = p.user
                return p, key, conf
            else:
                print(f"[DEBUG] NOT found in table={key}")
        except Exception:
            continue

    return None, None, None


# ─────────────────────────────────────────────────────────────────────────────
# List View
# ─────────────────────────────────────────────────────────────────────────────

class CollegeStudentListView(APIView):
    """
    GET /api/accounts/college/students/
    Returns students from ALL profile tables combined.
    college_user     → only their college students
    university_admin → all students (or ?college_code= to filter)

    Optional: ?profile_type=ug  → search only that one table
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type not in ('college_user', 'university_admin'):
            return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        college, err = _get_college(request)
        if err:
            return err

        # Optional: narrow to one profile type
        profile_type_filter = request.GET.get('profile_type', '').strip().lower()
        if profile_type_filter and profile_type_filter not in PROFILE_REGISTRY:
            return Response(
                {'error': f"Unknown profile_type. Valid: {', '.join(PROFILE_REGISTRY)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        search  = request.GET.get('search', '').strip()
        roll_no = request.GET.get('roll_no', '').strip()
        reg_no  = (request.GET.get('reg_no') or request.GET.get('registration_no', '')).strip()
        name    = request.GET.get('name', '').strip()

        try:
            page = max(1, int(request.GET.get('page', 1)))
            page_size = min(500, max(1, int(request.GET.get('page_size', PAGE_SIZE))))
        except (ValueError, TypeError):
            page = 1
            page_size = PAGE_SIZE

        from django.db.models import Q

        # Decide which tables to scan
        if profile_type_filter:
            tables_to_scan = {profile_type_filter: PROFILE_REGISTRY[profile_type_filter]}
        else:
            tables_to_scan = PROFILE_REGISTRY

        # Collect results from all tables
        all_results = []
        counts_by_type = {}

        for ptype, conf in tables_to_scan.items():
            try:
                Model = conf['get_model']()
                qs = Model.objects.select_related('user', 'college')

                # College filter
                if college:
                    qs = qs.filter(**{f"{conf['college_field']}__college_code": college.college_code})

                # Search filters
                if search:
                    qs = qs.filter(
                        Q(**{f"{conf['reg_field']}__icontains": search}) |
                        Q(**{f"{conf['roll_field']}__icontains": search}) |
                        Q(**{f"{conf['first_name_field']}__icontains": search})
                    )
                if roll_no:
                    qs = qs.filter(**{f"{conf['roll_field']}__icontains": roll_no})
                if reg_no:
                    qs = qs.filter(**{f"{conf['reg_field']}__icontains": reg_no})
                if name:
                    qs = qs.filter(**{f"{conf['first_name_field']}__icontains": name})

                qs = qs.order_by(conf['reg_field'])
                count = qs.count()
                counts_by_type[ptype] = count

                # Only serialize records for the current page window
                SerializerClass = conf['make_serializer']()
                for profile in qs[:page_size]:
                    data = SerializerClass(profile, context={'request': request}).data
                    data['profile_type'] = ptype
                    all_results.append(data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error scanning {ptype}: {e}")
                counts_by_type[ptype] = 0
                continue

        total = sum(counts_by_type.values())
        offset = (page - 1) * page_size
        page_results = all_results[offset:offset + page_size]

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'num_pages': (total + page_size - 1) // page_size,
            'college': college.name if college else 'All',
            'counts_by_profile': counts_by_type,
            'results': page_results,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Detail + Update View
# ─────────────────────────────────────────────────────────────────────────────

class CollegeStudentDetailView(APIView):
    """
    GET  /college/students/<identifier>/   → find student, return profile
    PATCH /college/students/<identifier>/  → update student profile

    college_user     → only their own college students
    university_admin → any student
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, identifier):
        if request.user.user_type not in ('college_user', 'university_admin'):
            return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        college, err = _get_college(request)
        if err:
            return err

        profile, ptype, conf = _find_student(identifier, college=college)
        if not profile:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        SerializerClass = conf['make_serializer']()
        return Response({
            **SerializerClass(profile, context={'request': request}).data,
            'profile_type': ptype,
        })

    def patch(self, request, identifier):
        if request.user.user_type not in ('college_user', 'university_admin'):
            return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        if request.user.user_type == 'college_user':
            cp = getattr(request.user, 'college_profile', None)
            if not cp or not cp.can_manage_students:
                return Response({'error': 'No permission to manage students.'}, status=status.HTTP_403_FORBIDDEN)

        college, err = _get_college(request)
        if err:
            return err

        profile, ptype, conf = _find_student(identifier, college=college)
        if not profile:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Prepare payload
        payload = request.data.copy()
        for field in ['profile_image', 'signature']:
            if field in request.FILES:
                payload[field] = request.FILES[field]
            elif field in payload:
                val = payload.get(field)
                if isinstance(val, str):
                    if val.lower().strip() in ('null', 'none', ''):
                        payload[field] = None
                    else:
                        payload.pop(field, None)

        SerializerClass = conf['make_serializer']()
        serializer = SerializerClass(profile, data=payload, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            updated = serializer.save()

            user = updated.user
            if user:
                changed = False
                fn_key = conf.get('first_name_sync')
                if fn_key and hasattr(updated, fn_key):
                    v = getattr(updated, fn_key)
                    if v and str(v) != user.first_name:
                        user.first_name = str(v)
                        changed = True
                ln_key = conf.get('last_name_sync')
                if ln_key and hasattr(updated, ln_key):
                    v = getattr(updated, ln_key)
                    if v and str(v) != user.last_name:
                        user.last_name = str(v)
                        changed = True
                if changed:
                    user.save()

            updated.refresh_from_db()

        return Response({
            'message': f"Student '{identifier}' updated successfully.",
            'profile_type': ptype,
            'student': SerializerClass(updated, context={'request': request}).data,
        })

