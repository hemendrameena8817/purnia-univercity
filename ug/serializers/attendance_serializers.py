from rest_framework import serializers
from ..models import UGStudentProfile, StudentCourseAssessment, UGExam
from colleges.models import College

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
        schedules = self.context.get('todays_schedules', [])
        student = obj.student
        
        course_name = (obj.course_name or "").strip()
        category = (obj.course_type or "").strip().upper()
        base_cat = category.split('-')[0].strip()
        
        matched_sched = None
        
        # 1. Identify relevant department for standard subjects
        curr_dept_id = None
        if student:
            if base_cat == 'MJC': curr_dept_id = student.major_course_id
            elif base_cat == 'MIC': curr_dept_id = student.minor_course_id
            elif base_cat == 'MDC': curr_dept_id = student.mdc_course_id

        # --- SYSTEMATIC LOOKUP (Synced with Admit Card Logic) ---
        if base_cat in ['AEC', 'VAC', 'SEC']:
            # Priority A: Check if there's a schedule for this category specifically mapped to student's MJC
            if student and student.major_course_id:
                for s in schedules:
                    if s.exam_type == base_cat and any(m.id == student.major_course_id for m in s.mjc.all()):
                        # We still verify subject name if schedule has one
                        if s.exam_subject:
                            if s.exam_subject.course_name.strip().lower() == course_name.lower():
                                matched_sched = s
                                break
                        else:
                            matched_sched = s
                            break

            # Priority B: Common Paper Pool (Both Department and MJC NULL)
            if not matched_sched:
                for s in schedules:
                    if s.exam_type == base_cat and not s.department.all() and not s.mjc.all():
                        if s.exam_subject:
                            if s.exam_subject.course_name.strip().lower() == course_name.lower():
                                matched_sched = s
                                break
                        else:
                            matched_sched = s
                            break
        else:
            # MJC, MIC, MDC logic
            if curr_dept_id:
                for s in schedules:
                    if s.exam_type == base_cat:
                        is_mjc_matched = any(m.id == curr_dept_id for m in s.mjc.all())
                        is_dept_matched = any(d.id == curr_dept_id for d in s.department.all())
                        if is_mjc_matched or is_dept_matched:
                            matched_sched = s
                            break

        # Final check by paper name if nothing found yet (broad fallback)
        if not matched_sched:
            for s in schedules:
                if s.exam_subject and s.exam_subject.course_name.strip().lower() == course_name.lower():
                    matched_sched = s
                    break

        # --- APPLY HARDCODED OVERRIDES (Synced with Admit Card) ---
        exam_time_val = "-"
        exam_date_val = "-"
        
        if matched_sched:
            exam_time_val = f"{matched_sched.exam_time} to {matched_sched.sitting}" if matched_sched.exam_time and matched_sched.sitting else (matched_sched.exam_time or matched_sched.sitting or "TBD")
            exam_date_val = str(matched_sched.exam_date)

        # AEC MIL - URDU / MAITHILI / BENGALI
        if base_cat == 'AEC' and course_name in ['MIL - Urdu', 'MIL - Maithili', 'MIL - Bengali']:
            exam_date_val = "2026-04-09"
            exam_time_val = "02:00 PM to 05:00 PM"

        # VAC FIT INDIA
        if base_cat == 'VAC' and course_name == 'Fit India':
            exam_date_val = "2026-04-10"
            exam_time_val = "10:00 AM to 01:00 PM"

        # VAC ART OF BEING HAPPY
        if base_cat == 'VAC' and course_name == 'Art of Being Happy':
            exam_date_val = "2026-04-11"
            exam_time_val = "02:00 PM to 05:00 PM"

        # SEC BASIC IT TOOLS
        if base_cat == 'SEC' and course_name == 'Basic IT Tools':
            exam_date_val = "2026-04-13"
            exam_time_val = "10:00 AM to 01:00 PM"

        # SEC DIGITAL MARKETING
        if base_cat == 'SEC' and course_name == 'Digital Marketing':
            exam_date_val = "2026-04-15"
            exam_time_val = "10:00 AM to 01:00 PM"

        # SEC PUBLIC SPEAKING
        if base_cat == 'SEC' and course_name == 'Public Speaking English Language and Leadership':
            exam_date_val = "2026-04-15"
            exam_time_val = "02:00 PM to 05:00 PM"

        # AEC MIL - ENGLISH COMMUNICATION
        if base_cat == 'AEC' and course_name == 'MIL- English Communication':
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
