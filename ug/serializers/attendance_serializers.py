import re
from rest_framework import serializers
from ..models import UGStudentProfile, StudentCourseAssessment, UGExam
from colleges.models import College

def normalize_course_name(value):
    """Helper to standardize paper names for matching."""
    value = str(value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()

def get_sem_integer(sem_str):
    """Helper to convert 'Semester-I', '1st Semester', '1ST' or '1' to integer 1."""
    if not sem_str: return None
    sem_str = str(sem_str).strip().upper()
    if sem_str.isdigit(): return int(sem_str)
    match = re.match(r'^(\d+)(ST|ND|RD|TH)', sem_str)
    if match: return int(match.group(1))
    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}
    for rom, val in roman_map.items():
        if f"-{rom}" in sem_str or f" {rom}" in sem_str or f" {rom} " in sem_str or sem_str.endswith(rom) or sem_str == rom:
            return val
    numbers = re.findall(r'\d+', sem_str)
    if numbers: return int(numbers[0])
    return None

class UGAttendanceStudentSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for each student's ESE assessment entry
    returned in the attendance list API (GET /student-attendance/list/).
    """
    assessment_uid  = serializers.UUIDField(source='uid', read_only=True)
    name            = serializers.SerializerMethodField()
    roll_no         = serializers.SerializerMethodField()
    registration_no = serializers.SerializerMethodField()
    photo_url       = serializers.SerializerMethodField()
    student_uid     = serializers.UUIDField(source='student.uid', read_only=True)
    is_absent       = serializers.BooleanField(source='ind_is_absent', read_only=True)
    department      = serializers.SerializerMethodField()
    category        = serializers.CharField(source='course_type', read_only=True)
    exam_details    = serializers.SerializerMethodField()

    class Meta:
        model  = StudentCourseAssessment
        fields = [
            'id',
            'assessment_uid',
            'student_uid',
            'name',
            'roll_no',
            'registration_no',
            'photo_url',
            'course_code',
            'course_name',
            'department',
            'category',
            'is_absent',
            'exam_details',
        ]

    def get_exam_details(self, obj):
        """
        Populate Subject Date and Time by matching the student's assessment 
        with today's active exam schedules.
        """
        schedules = self.context.get('todays_schedules', [])
        student = obj.student
        
        # 1. Normalize Assessment details for matching
        raw_name = (obj.course_name or "").strip()
        course_name_norm = normalize_course_name(raw_name)
        category = (obj.course_type or "").strip().upper()
        base_cat = category.split('-')[0].strip()
        
        # 2. Get Student's registered semester for this assessment
        # Prefer numeric comparison to handle '1st Semester' vs 'Semester-I'
        student_sem = None
        reg = obj.exam_registrations.last()
        if reg:
            student_sem = reg.sem
        if not student_sem and obj.semester:
            student_sem = get_sem_integer(obj.semester)
        
        # 3. Resolve Current Department mapping for matching
        curr_dept_id = None
        if student:
            if base_cat == 'MJC': curr_dept_id = student.major_course_id
            elif base_cat == 'MIC': curr_dept_id = student.minor_course_id
            elif base_cat == 'MDC': curr_dept_id = student.mdc_course_id

        matched_sched = None
        
        # --- PHASE 1: SYSTEMATIC LOOKUP (Synced with Admit Card Algorithm) ---
        for s in schedules:
            # SEMESTER VALIDATION: Ensure schedule semester (from UGExam) matches assessment semester
            sched_sem_str = s.exam.semester if s.exam else ""
            if student_sem and get_sem_integer(sched_sem_str) != student_sem:
                 continue

            # CASE: AEC/VAC/SEC (Special Priority Pool Logic)
            if base_cat in ['AEC', 'VAC', 'SEC']:
                if s.exam_type == base_cat:
                    # Priority A: Check if MJC Specifically mapped
                    is_mjc_pool = any(m.id == student.major_course_id for m in s.mjc.all()) if student and student.major_course_id else False
                    # Priority B: Common Pool (Both NULL)
                    is_common_pool = not s.department.all() and not s.mjc.all()
                    
                    if is_mjc_pool or is_common_pool:
                        # Success if paper name matches or schedule's generic slot
                        if s.exam_subject:
                            if normalize_course_name(s.exam_subject.course_name) == course_name_norm:
                                matched_sched = s
                                break
                        elif is_mjc_pool: # Accept generic category slot only for MJC specifically mapped sittings
                            matched_sched = s
                            break

            # CASE: MJC/MIC/MDC (Standard Subject Pool)
            else:
                if s.exam_type == base_cat and curr_dept_id:
                    if any(m.id == curr_dept_id for m in s.mjc.all()) or any(d.id == curr_dept_id for d in s.department.all()):
                        matched_sched = s
                        break

        # --- PHASE 2: BROAD FALLBACK (By exact paper name match) ---
        if not matched_sched:
            for s in schedules:
                if student_sem and get_sem_integer(s.exam.semester if s.exam else "") != student_sem:
                    continue
                if s.exam_subject and normalize_course_name(s.exam_subject.course_name) == course_name_norm:
                    matched_sched = s
                    break

        # --- PHASE 3: APPLY UNIVERSITY HARDCODED OVERRIDES ---
        exam_time_val = "-"
        exam_date_val = "-"
        
        if matched_sched:
            exam_time_val = f"{matched_sched.exam_time} to {matched_sched.sitting}" if \
                           matched_sched.exam_time and matched_sched.sitting else \
                           (matched_sched.exam_time or matched_sched.sitting or "TBD")
            exam_date_val = str(matched_sched.exam_date)

        # AEC MIL - URDU / MAITHILI / BENGALI
        if base_cat == 'AEC' and course_name_norm in ['mil urdu', 'mil maithili', 'mil bengali']:
            exam_date_val = "2026-04-09"
            exam_time_val = "02:00 PM to 05:00 PM"

        # VAC FIT INDIA
        if base_cat == 'VAC' and course_name_norm == 'fit india':
            exam_date_val = "2026-04-10"
            exam_time_val = "10:00 AM to 01:00 PM"

        # VAC ART OF BEING HAPPY
        if base_cat == 'VAC' and course_name_norm == 'art of being happy':
            exam_date_val = "2026-04-11"
            exam_time_val = "02:00 PM to 05:00 PM"

        # SEC BASIC IT TOOLS
        if base_cat == 'SEC' and course_name_norm == 'basic it tools':
            exam_date_val = "2026-04-13"
            exam_time_val = "10:00 AM to 01:00 PM"

        # SEC DIGITAL MARKETING
        if base_cat == 'SEC' and course_name_norm == 'digital marketing':
            exam_date_val = "2026-04-15"
            exam_time_val = "10:00 AM to 01:00 PM"

        # SEC PUBLIC SPEAKING
        if base_cat == 'SEC' and course_name_norm == 'public speaking english language and leadership':
            exam_date_val = "2026-04-15"
            exam_time_val = "02:00 PM to 05:00 PM"

        # AEC MIL - ENGLISH COMMUNICATION
        if base_cat == 'AEC' and course_name_norm == 'mil english communication':
            exam_date_val = "2026-04-08"
            exam_time_val = "10:00 AM to 01:00 PM"

        return {
            "exam_date": exam_date_val,
            "exam_time": exam_time_val
        }

    def get_department(self, obj):
        c_type = (obj.course_type or "").upper().strip()
        
        # 1. CBCS Student selections
        if c_type == 'MJC':
            return obj.student.major_course.name if obj.student and obj.student.major_course else "N/A"
        elif c_type == 'MIC':
            return obj.student.minor_course.name if obj.student and obj.student.minor_course else "N/A"
        elif c_type == 'MDC':
            return obj.student.mdc_course.name if obj.student and obj.student.mdc_course else "N/A"
        
        # 3. SEC, AEC: Usually teaching department
        elif c_type in ['SEC', 'AEC', 'VAC']:
            return obj.department.name if obj.department else "N/A"
            
        # 4. Fallback
        if obj.department:
            return obj.department.name
        return obj.student.major_course.name if obj.student and obj.student.major_course else "N/A"

    def get_name(self, obj):
        if not obj.student:
            return '-'
        return f"{obj.student.first_name} {obj.student.last_name or ''}".strip()

    def get_roll_no(self, obj):
        return obj.student.roll_no or 'N/A' if obj.student else 'N/A'

    def get_registration_no(self, obj):
        return obj.student.registration_no or 'N/A' if obj.student else 'N/A'

    def get_photo_url(self, obj):
        if obj.student and obj.student.profile_image:
            try:
                return obj.student.profile_image.url
            except Exception:
                return None
        return None


class UGAttendanceMarkSerializer(serializers.Serializer):
    """
    Write serializer for the attendance mark API (POST /student-attendance/mark/).
    """
    assessment_uid = serializers.UUIDField()
    is_absent      = serializers.BooleanField()

    def validate_assessment_uid(self, value):
        if not StudentCourseAssessment.objects.filter(uid=value).exists():
            raise serializers.ValidationError("Assessment not found.")
        return value


class UGExamDropSerializer(serializers.ModelSerializer):
     class Meta:
        model = UGExam
        fields = ['uid', 'name', 'semester', 'session', 'exam_month_year']
        read_only_fields = ['uid']
