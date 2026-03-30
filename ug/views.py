from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.template.loader import render_to_string
from io import BytesIO
from weasyprint import HTML
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.db.models import Q
from datetime import datetime
import os
import base64
from .permissions import IsExamCenterUser
from .models import UGStudentProfile, UGExam, UGExamCenterMapping, ExamRegistration, StudentCourseAssessment, UGExamSchedule, UGDepartment
from .serializers.attendance_serializers import UGAttendanceStudentSerializer, UGAttendanceMarkSerializer, UGExamDropSerializer
from .utils.admit_card_pdf import generate_ug_admit_card_pdf

from .utils.attendance_sheet_pdf import generate_ug_attendance_sheet_pdf

class UGAdmitCardPDFView(APIView):
    """
    Generates and returns admit card PDF for a single UG student.
    Query params: registration_no (Staff only), exam_uid
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_authenticated:
             return HttpResponse("Access Denied: Please log in.", status=401)

        exam_uid = request.GET.get("exam_uid")
        if not exam_uid:
            return HttpResponse("Exam UID is required", status=400)

        # 1. ID is the Login Username (Registration Number)
        registration_no = request.user.username
        
        # 2. Staff Override via query param
        # reg_no_param = request.GET.get("registration_no")
        # if reg_no_param:
        #     registration_no = reg_no_param

        # 3. Fetch Student
        student = get_object_or_404(UGStudentProfile, registration_no=registration_no)

        exam = get_object_or_404(UGExam, uid=exam_uid)
        pdf_content = generate_ug_admit_card_pdf(student, exam)

        if not pdf_content:
            return HttpResponse("Student is NOT REGISTERED for this examination.", status=404)

        # 2. Determine Disposition (View inline vs Force Download)
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'
        
        safe_reg = student.registration_no.replace("/", "_")
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="admit_card_{safe_reg}.pdf"'
        return response

class UGBulkAdmitCardPDFView(APIView):
    """
    Bulk Admit Card PDF Generator for UG Students.
    Similar to MBA Bulk view.
    Query Params:
        exam_uid (required)
        registration_nos (required, comma separated)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        exam_uid = request.GET.get("exam_uid", "").strip()
        reg_nos = request.GET.get("registration_nos", "").strip()

        if not exam_uid or not reg_nos:
            return Response({"error": "exam_uid and registration_nos are required"}, status=status.HTTP_400_BAD_REQUEST)

        exam = get_object_or_404(UGExam, uid=exam_uid)
        reg_no_list = [r.strip() for r in reg_nos.split(",") if r.strip()]

        if not reg_no_list:
            return Response({"error": "No valid registration numbers provided"}, status=status.HTTP_400_BAD_REQUEST)

        students = UGStudentProfile.objects.filter(registration_no__in=reg_no_list, is_active=True)

        if not students.exists():
            return Response({"error": "No students found for given registration numbers"}, status=status.HTTP_404_NOT_FOUND)

        # Create Directory for saving (Optional, based on MBA logic)
        safe_exam_name = "".join(c if c.isalnum() else "_" for c in str(exam.name))
        save_dir = os.path.join(settings.MEDIA_ROOT, "ug_students", "admit_cards", f"{safe_exam_name}_{str(exam_uid)[:8]}")
        os.makedirs(save_dir, exist_ok=True)

        results = []
        for student in students:
            try:
                pdf_content = generate_ug_admit_card_pdf(student, exam)
                if pdf_content:
                    file_name = f"admit_card_{student.registration_no}.pdf"
                    file_path = os.path.join(save_dir, file_name)
                    with open(file_path, "wb") as f:
                        f.write(pdf_content)
                    
                    relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    results.append({
                        "registration_no": student.registration_no,
                        "status": "success",
                        "url": f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                    })
                else:
                    results.append({"registration_no": student.registration_no, "status": "failed", "error": "PDF generation failed"})
            except Exception as e:
                results.append({"registration_no": student.registration_no, "status": "error", "error": str(e)})



from django.template.loader import render_to_string
from io import BytesIO
from weasyprint import HTML

class UGAdmitCardTestView(View):
    """
    Test view with static data to see the Admit Card PDF design.
    """
    def get(self, request):
        # Prepare Base64 Images for Test
        base_static_path = os.path.join(settings.BASE_DIR, 'ug', 'static', 'ug', 'images')
        logo_path = os.path.join(base_static_path, 'purnea-logo.png')
        university_logo_b64 = ""
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                university_logo_b64 = base64.b64encode(f.read()).decode('utf-8')

        controller_sig_path = os.path.join(base_static_path, 'controller-of-examination-signature.png')
        controller_sig_b64 = ""
        if os.path.exists(controller_sig_path):
            with open(controller_sig_path, 'rb') as f:
                controller_sig_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Static mock data - MIRROR MCA CONTEXT
        data = {
            'exam': {'name': "UG SEMESTER-I EXAMINATION 2024"},
            'student': {
                'roll_no': "210351234001",
                'registration_no': "211511200100",
                'full_name': "SUMIT KUMAR",
                'father_name': "PANKAJ KUMAR",
                'mother_name': "REKHA DEVI",
                'gender': "MALE",
                'college_name': "PURNEA COLLEGE, PURNIA",
            },
            'status': 'REGULAR',
            'center_code': "1203",
            'center_name': "K.B. JHA COLLEGE, KATIHAR (CENTRE)",
            'student_photo': "", # Keep empty for test if no dummy available
            'student_sig': "",
            'university_logo': university_logo_b64,
            'watermark_logo': university_logo_b64,
            'controller_signature': controller_sig_b64,
            'schedules': [
                {'code': 'MJC-1', 'name': 'PROBLEM SOLVING USING C', 'exam_date': '2024-12-10', 'exam_time': '10:00 AM - 01:00 PM', 'sitting': '1ST SITTING'},
                {'code': 'MIC-1', 'name': 'CALCULUS', 'exam_date': '2024-12-15', 'exam_time': '10:00 AM - 01:00 PM', 'sitting': '1ST SITTING'}
            ]
        }
        
        # Render HTML
        html_string = render_to_string('ug/admit_card.html', data)
        
        # Generate PDF
        buffer = BytesIO()
        HTML(string=html_string).write_pdf(target=buffer)
        
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="test_admit_card.pdf"'
        return response

class UGRollSheetPDFView(View):
    """
    Generates and returns Exam Roll Sheet PDF for UG.
    Query params: exam_uid, college_uid
    """
    def get(self, request, exam_uid=None, college_uid=None):
        from colleges.models import College
        from .models import UGExam
        from .utils.roll_sheet_pdf import generate_ug_roll_sheet_pdf

        # Get from slugs (path) or fallback to query params
        exam_uid = exam_uid or request.GET.get("exam_uid")
        college_uid = college_uid or request.GET.get("college_uid")

        if not all([exam_uid, college_uid]):
            return HttpResponse(
                "exam_uid and college_uid are required (either in URL or as query params)",
                status=400,
                content_type="text/plain"
            )

        exam = get_object_or_404(UGExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)
        department_uid = request.GET.get("department_uid")
        format_type = request.GET.get("format", "pdf").lower()
        
        from .utils.roll_sheet_pdf import generate_ug_roll_sheet_pdf, generate_ug_roll_sheet_excel
        
        if format_type == "zip":
            # ...zip logic...
            import zipfile
            pdf_content = generate_ug_roll_sheet_pdf(exam, college, department_uid)
            excel_content = generate_ug_roll_sheet_excel(exam, college, department_uid)
            
            if not pdf_content and not excel_content:
                return HttpResponse("No data found for export", status=404)
            
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                safe_name = "".join(c if c.isalnum() else "_" for c in college.name)
                if pdf_content:
                    zf.writestr(f"Roll_Sheet_{safe_name}.pdf", pdf_content)
                if excel_content:
                    zf.writestr(f"Roll_Sheet_{safe_name}.xlsx", excel_content)
            
            response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
            response["Content-Disposition"] = f'attachment; filename="Roll_Sheet_{safe_name}_Bundle.zip"'
            return response

        if format_type == "excel":
            excel_content = generate_ug_roll_sheet_excel(exam, college, department_uid)
            if not excel_content:
                return HttpResponse("No data found for Excel export", status=404)
            
            response = HttpResponse(excel_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            safe_name = "".join(c if c.isalnum() else "_" for c in college.name)
            response["Content-Disposition"] = f'attachment; filename="Roll_Sheet_{safe_name}.xlsx"'
            return response

        # Default PDF
        pdf_content = generate_ug_roll_sheet_pdf(exam, college, department_uid)
        if not pdf_content:
            return HttpResponse("No data found", status=404)

        download = request.GET.get("download", "false").lower() == "true"
        disposition = "attachment" if download else "inline"
        response = HttpResponse(pdf_content, content_type="application/pdf")
        safe_college_name = "".join(c if c.isalnum() else "_" for c in college.name)
        filename_part = f'; filename="Roll_Sheet_{safe_college_name}.pdf"' if download else ""
        response["Content-Disposition"] = f'{disposition}{filename_part}'
        
        # Dual-download trick: only if not already an excel request
        if format_type == "pdf":
            # Strip format=pdf and append format=excel to trigger the sibling download
            excel_url = f"{request.path}?exam_uid={exam_uid}&college_uid={college_uid}&format=excel"
            if department_uid:
                excel_url += f"&department_uid={department_uid}"
            response["Refresh"] = f"2; url={excel_url}"
            
        return response


class UGAttendanceSheetPDFView(View):
    """
    Generates and returns Exam Attendance Sheet PDF for UG.
    Query params: exam_uid, college_uid, registration_no (optional)
    """
    def get(self, request, exam_uid=None, college_uid=None):
        from colleges.models import College
        from .models import UGExam
        from .utils.attendance_sheet_pdf import generate_ug_attendance_sheet_pdf

        exam_uid = exam_uid or request.GET.get("exam_uid")
        college_uid = college_uid or request.GET.get("college_uid")

        if not all([exam_uid, college_uid]):
            return HttpResponse("exam_uid and college_uid are required", status=400)

        exam = get_object_or_404(UGExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)
        
        registration_no = request.GET.get("registration_no")
        department_uid = request.GET.get("department_uid")

        pdf_content = generate_ug_attendance_sheet_pdf(
            exam, college, department_uid=department_uid, registration_no=registration_no
        )

        if not pdf_content:
            return HttpResponse("No data found for attendance sheet", status=404)

        download = request.GET.get("download", "false").lower() == "true"
        disposition = "attachment" if download else "inline"
        
        response = HttpResponse(pdf_content, content_type="application/pdf")
        safe_college_name = "".join(c if c.isalnum() else "_" for c in college.name)
        filename = f"Attendance_Sheet_{safe_college_name}.pdf"
        if registration_no:
            filename = f"Attendance_Sheet_{registration_no}.pdf"
            
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response


class UGExamListView(APIView):
    """
    List UG Exams (active only) with optional filters: 
    - name (string)
    - semester (string)
    - session (string)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from .base_serializers import UGExamSerializer
        
        exam_uid = request.query_params.get('uid')
        if exam_uid:
            exam = get_object_or_404(UGExam, uid=exam_uid, is_active=True)
            serializer = UGExamSerializer(exam)
            return Response(serializer.data)

        # Only active exams
        queryset = UGExam.objects.filter(is_active=True)

        # Filters
        name = request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        semester = request.query_params.get('semester')
        if semester:
            queryset = queryset.filter(semester__icontains=semester)

        session = request.query_params.get('session')
        if session:
            queryset = queryset.filter(session__icontains=session)

        # Order by most recent
        queryset = queryset.order_by('-created_at')

        serializer = UGExamSerializer(queryset, many=True)
        return Response(serializer.data)


class UGCenterAttachedCollegesView(APIView):
    """
    API View to get colleges attached to the logged-in center user's college for a specific exam.
    Only accessible by college users (exam center).
    Example: GET /api/ug/center/attached-colleges/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsExamCenterUser]

    def get(self, request):
        center_college = request.user.college
        
        # Find mapping where this college is the center
        mapping = UGExamCenterMapping.objects.filter(center=center_college).first()
        if not mapping:
            return Response({
                "colleges": [], 
                "total": 0,
                "center_code": getattr(center_college, 'center_code', None),
                "college_code": center_college.college_code,      
                "center_name": center_college.name
            }, status=status.HTTP_200_OK)
            
        attached_colleges = mapping.attached_colleges.all().order_by('name')
        data = [{"uid": str(c.uid), "name": c.name} for c in attached_colleges]
        
        return Response({
            "colleges": data, 
            "total": len(data), 
            "center_code": getattr(center_college, 'center_code', None),
            "college_code": center_college.college_code,
            "center_name": center_college.name
        }, status=status.HTTP_200_OK)


class UGDispatchMemoView(APIView):
    """
    GET /api/ug/center/dispatch-memo/?exam_date=YYYY-MM-DD&exam_time=shift_time&course_code=course_code&course_name=course_name
    Generates a dispatch memo for a specific exam slot at the logged-in user's center.
    Groups students by their HOME college.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsExamCenterUser]

    def get(self, request):
        now_local = timezone.localtime(timezone.now())
        today = now_local.date()

        # 1. Validate Center College
        center_college = request.user.college

        # 2. Get Query Params
        exam_date_str = request.query_params.get('exam_date')
        exam_time_str = request.query_params.get('exam_time')
        course_code = request.query_params.get('course_code')
        course_name = request.query_params.get('course_name')
        
        # New department filters
        mjc_uid = request.query_params.get('mjc_uid')
        mic_uid = request.query_params.get('mic_uid')
        mdc_uid = request.query_params.get('mdc_uid')
        department_uid = request.query_params.get('department_uid')

        print(f"--- Dispatch Memo Filters ---")
        print(f"Center: {center_college.name}")
        print(f"Date: {exam_date_str}, Shift: {exam_time_str}")
        print(f"Code: {course_code}, Name: {course_name}")
        print(f"MJC: {mjc_uid}, MIC: {mic_uid}, MDC: {mdc_uid}, Dept: {department_uid}")

        exam_date = today
        if exam_date_str:
            try:
                exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Find Matching Schedule
        schedules_qs = UGExamSchedule.objects.filter(exam_date=exam_date)
        if exam_time_str:
            schedules_qs = schedules_qs.filter(exam_time__icontains=exam_time_str)
        
        subject_filter = Q()
        if course_code:
            subject_filter |= Q(exam_subject__course_code__iexact=course_code)
        if course_name:
            subject_filter |= Q(exam_subject__course_name__icontains=course_name)
        
        if subject_filter:
            schedules_qs = schedules_qs.filter(subject_filter)

        schedules = list(schedules_qs.select_related('exam', 'exam_subject'))
        print(f"Matching Schedules Count: {len(schedules)}")

        # 4. Determine which Exam to use
        if schedules:
            exam = schedules[0].exam
        else:
            # If user PROVIDED specific search terms but nothing matched, return 404
            if any([course_code, course_name]):
                return Response({
                    "error": f"No schedule found matching: {course_code or course_name}"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # If NO search terms (Get All Data), fallback to latest active exam
            exam = UGExam.objects.filter(is_active=True).first()
            if not exam:
                return Response({"error": "No active exam found."}, status=status.HTTP_404_NOT_FOUND)

        exam_name_display = exam.name if exam.name else f"UG {exam.semester} Exam"

        # 5. Fetch Attached Colleges for THIS CENTER
        mapping = UGExamCenterMapping.objects.filter(center=center_college).first()
        if not mapping:
            return Response({"error": "No colleges mapped to this center."}, status=status.HTTP_404_NOT_FOUND)
            
        attached_colleges = mapping.attached_colleges.all()
        attached_college_ids = attached_colleges.values_list('id', flat=True)

        # Get all registered students from attached colleges for this exam
        mapped_colleges_count = len(attached_college_ids)
        print(f"\n[DEBUG] Exam Used: {exam}, Attached Colleges: {mapped_colleges_count}")
        
        reg_filters = Q(
            exam=exam,
            student__college_id__in=attached_college_ids,
            status='REGISTERED'
        )
        
        # Test base filter count
        base_count = ExamRegistration.objects.filter(reg_filters).count()
        print(f"[DEBUG] Base Registered Students (Exam + Colleges): {base_count}")
        
        # Removed department-specific filters from student profile (moved to assessments)

        registered_student_ids = ExamRegistration.objects.filter(
            reg_filters
        ).values_list('student_id', flat=True).distinct()
        print(f"[DEBUG] Final Registered Students for Center/Filters: {len(registered_student_ids)}")

        # Print some random students' MJC/MIC/MDC if it's 0 but base isn't 0
        if len(registered_student_ids) == 0 and base_count > 0:
            sample_student = ExamRegistration.objects.filter(exam=exam, student__college_id__in=attached_college_ids, status='REGISTERED').select_related('student', 'student__major_course', 'student__minor_course', 'student__mdc_course').first()
            if sample_student:
                print(f"[DEBUG] Sample Student in DB:")
                print(f"      Major UID: {getattr(sample_student.student.major_course, 'uid', None) if getattr(sample_student.student, 'major_course', None) else None}")
                print(f"      Minor UID: {getattr(sample_student.student.minor_course, 'uid', None) if getattr(sample_student.student, 'minor_course', None) else None}")
                print(f"      MDC UID: {getattr(sample_student.student.mdc_course, 'uid', None) if getattr(sample_student.student, 'mdc_course', None) else None}")

        # Build Assessment Filter
        asmnt_filter = Q(student_id__in=registered_student_ids, label__iregex=r'^ESE-Theory')
        
        if schedules:
            paper_codes = [s.exam_subject.course_code for s in schedules if s.exam_subject and s.exam_subject.course_code]
            if paper_codes:
                asmnt_filter &= Q(course_code__in=paper_codes)
        elif course_code:
            asmnt_filter &= Q(course_code__iexact=course_code)

        # Apply department filters on StudentCourseAssessment
        if mjc_uid:
            asmnt_filter &= Q(department__uid=mjc_uid, course_type__iexact='MJC')
        if mic_uid:
            asmnt_filter &= Q(department__uid=mic_uid, course_type__iexact='MIC')
        if mdc_uid:
            asmnt_filter &= Q(department__uid=mdc_uid, course_type__iexact='MDC')
        if department_uid:
            asmnt_filter &= Q(department__uid=department_uid)

        assessments = StudentCourseAssessment.objects.filter(asmnt_filter).select_related('student', 'student__college').order_by('student__college__name', 'student__roll_no')
        print(f"Final Assessments (ESE-Theory) Count: {len(assessments)}")

        # 6. Group Data by Home College
        colleges_dict = {}
        total_present = 0
        total_absent = 0
        total_expelled = 0

        for asmnt in assessments:
            student = asmnt.student
            college_name = student.college.name if student.college else "Unknown College"
            college_addr = student.college.address.split(',')[0] if student.college and student.college.address else ""
            display_name = f"{college_name}, {college_addr}" if college_addr else college_name
            
            if display_name not in colleges_dict:
                colleges_dict[display_name] = {
                    "college_name": display_name,
                    "present_rolls": [],
                    "absent_rolls": [],
                    "expelled_rolls": []
                }
            
            roll = student.roll_no or student.registration_no

            if asmnt.ind_is_absent:
                colleges_dict[display_name]["absent_rolls"].append(roll)
                total_absent += 1
            else:
                colleges_dict[display_name]["present_rolls"].append(roll)
                total_present += 1
                
        # 7. Build Final JSON Response
        memo_data = {
            "header": {
                "center_name": center_college.name,
                "center_code": getattr(center_college, 'center_code', None),
                "university_name": "Purnea University, Purnea", 
                "exam_name": exam_name_display,
                "year": exam.session.split('-')[0] if (exam and exam.session) else "",
                "subject": ", ".join(set(str(s.exam_subject.course_name) for s in schedules if s.exam_subject)) if schedules else (course_code or course_name or "ALL SUBJECTS"),
                "date": exam_date.strftime("%d/%m/%Y"),
                "shift": exam_time_str or "ALL SHIFTS",
            },
            "colleges_data": list(colleges_dict.values()),
            "summary": {
                "total_present": total_present,
                "total_absent": total_absent,
                "total_expelled": total_expelled,
                "grand_total": total_present + total_absent + total_expelled
            }
        }

        return Response(memo_data, status=status.HTTP_200_OK)


class UGStudentAttendanceListView(APIView):
    """
    GET /api/ug/student-attendance/list/?college_uid=<uid>&department_uid=<uid>
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsExamCenterUser]

    def get(self, request):
        from colleges.models import College
        from django.db.models import Q
        import re

        college_uid = request.query_params.get('college_uid')
        department_uid = request.query_params.get('department_uid')

        if not college_uid:
            return Response(
                {"error": "college_uid is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        college = get_object_or_404(College, uid=college_uid)
        
        department = None
        if department_uid:
            department = get_object_or_404(UGDepartment, uid=department_uid)

        now_local = timezone.localtime(timezone.now())
        today = now_local.date()
        current_time = now_local.time()
        exam_type_param = request.query_params.get('exam_type', '').strip().upper()

        # Build schedule filter for TODAY
        schedule_filter = Q(exam_date=today) | Q(attendance_from__lte=now_local, attendance_to__gte=now_local)
        
        # Initial schedules queryset
        todays_schedules = UGExamSchedule.objects.filter(schedule_filter).select_related('exam', 'exam_subject').prefetch_related('mjc', 'department').order_by('exam_time').distinct()

        # If a specific department or category is selected, narrow down schedules
        if department:
            dept_filter = (
                Q(department=department) | 
                Q(mjc=department) | 
                Q(exam_subject__department=department) |
                (Q(department__isnull=True) & Q(mjc__isnull=True) & Q(exam_subject__department__isnull=True))
            )
            todays_schedules = todays_schedules.filter(dept_filter)

        if exam_type_param:
            todays_schedules = todays_schedules.filter(exam_type__iexact=exam_type_param)

        # --- STRICT 1st SEMESTER AUTO-SELECTION ---
        # Only show Semester-I exams by default as per requirement
        todays_schedules = todays_schedules.filter(exam__semester__icontains="I")

        # Pick the most recently added exam that matches today's Semester-I criteria
        recent_exam_id = todays_schedules.order_by('exam__id').values_list('exam', flat=True).last()
        
        if not recent_exam_id:
            # Absolute fallback to the last UG exam in the system if no schedules match today
            last_exam = UGExam.objects.all().last()
            if last_exam:
                recent_exam_id = last_exam.id
        
        # If we have a resolve context (either from today or absolute fallback)
        if recent_exam_id:
            # Sync todays_schedules to the finalized exam ID
            todays_schedules = UGExamSchedule.objects.filter(schedule_filter, exam_id=recent_exam_id).select_related('exam', 'exam_subject').prefetch_related('mjc', 'department').order_by('exam_time').distinct()
            
            # Re-apply dept/type filters if they were active
            if department:
                todays_schedules = todays_schedules.filter(dept_filter)
            if exam_type_param:
                todays_schedules = todays_schedules.filter(exam_type__iexact=exam_type_param)

        print(f"{todays_schedules = }")
        if not todays_schedules.exists():
            return Response({
                "attendance_open": False,
                "message": "No exams scheduled for the selected criteria.",
                "students": [],
                "total": 0
            }, status=status.HTTP_200_OK)

        active_schedules = list(todays_schedules)
        
        # Check custom attendance window logic
        is_window_open = False
        window_message = "Attendance window has closed for today."
        
        for schedule in active_schedules:
            if schedule.attendance_from and schedule.attendance_to:
                # If custom range provided
                if schedule.attendance_from <= now_local <= schedule.attendance_to:
                    is_window_open = True
                    break
                else:
                    window_message = f"Attendance allowed from {schedule.attendance_from.strftime('%I:%M %p')} to {schedule.attendance_to.strftime('%I:%M %p')}."
            else:
                # Regular cutoff fallback
                CUTOFF_HOUR = 23
                if current_time.hour < CUTOFF_HOUR:
                    is_window_open = True
                    break
        
        if not is_window_open:
            return Response({
                "attendance_open": False,
                "message": window_message,
                "students": [],
                "total": 0
            }, status=status.HTTP_200_OK)

        time_slots = []
        for s in todays_schedules:
            slot = f"{s.exam_time} to {s.sitting}" if s.exam_time and s.sitting else (s.exam_time or s.sitting or "TBD")
            if slot not in time_slots:
                time_slots.append(slot)
        active_exam_details = {
            "exam_date": str(today),
            "exam_time": ", ".join(time_slots)
        }

        active_exam = active_schedules[-1].exam
        relevant_paper_names = []
        relevant_course_types = []
        
        for s in active_schedules:
            if s.exam_subject and s.exam_subject.course_name:
                relevant_paper_names.append(s.exam_subject.course_name.strip())
            else:
                # Fallback: Agar Admin ne subject blank chhod chuka hai par Type (MJC/MIC) daala hai
                if getattr(s, 'exam_type', None):
                    relevant_course_types.append(s.exam_type.upper().strip())
                
        relevant_paper_names = list(set(relevant_paper_names))
        relevant_course_types = list(set(relevant_course_types))

        if not relevant_paper_names and not relevant_course_types:
            return Response({
                "attendance_open": True,
                "message": "Active slot found but no paper names/types configured.",
                "students": [],
                "total": 0
            }, status=status.HTTP_200_OK)

        # Center Mapping Logic: Aggregate students from all colleges mapped to this center
        center_mapping = UGExamCenterMapping.objects.filter(
            exam=active_exam,
            center=college
        ).first()

        if center_mapping:
            attached_colleges = list(center_mapping.attached_colleges.all())
            if college not in attached_colleges:
                attached_colleges.append(college)
            
            college_filter = Q(student__college__in=attached_colleges)
            print(f"DEBUG: Found center mapping with {len(attached_colleges)} colleges.")
        else:
            college_filter = Q(student__college=college)
            print(f"DEBUG: No center mapping found, using only current college students.")

        # Registration Query
        registration_filter = Q(college_filter, exam=active_exam, status='REGISTERED')
        
        # NOTE: We do NOT filter by student__major_course=department here. 
        # This allows a center to see students from ANY major who are taking a specific paper 
        # (critical for common/generic subjects like Hindi, AEC, VAC, etc.)
        
        registered_student_ids = ExamRegistration.objects.filter(
            registration_filter
        ).values_list('student_id', flat=True).distinct()

        if not registered_student_ids:
            return Response({
                "attendance_open": True,
                "exam_details": active_exam_details,
                "message": "No registered students found for this college.",
                "students": [],
                "total": 0
            }, status=status.HTTP_200_OK)

        student_assessments = StudentCourseAssessment.objects.filter(
            student_id__in=registered_student_ids,
            label__iregex=r'^ESE-Theory',
            semester = '1ST'
        ).select_related('student').order_by('student__roll_no', 'student__registration_no')

        q_filter = Q()
        if relevant_paper_names:
            q_filter |= Q(course_name__in=relevant_paper_names)
        if relevant_course_types:
            q_filter |= Q(course_type__in=relevant_course_types)

        if q_filter:
            student_assessments = student_assessments.filter(q_filter)

        search_query = request.query_params.get('search', '').strip()
        if search_query:
            student_assessments = student_assessments.filter(
                Q(student__roll_no__icontains=search_query) | 
                Q(student__registration_no__icontains=search_query)
            )

        from .pagination import LargeResultsSetPagination
        paginator = LargeResultsSetPagination()
        paginated_qs = paginator.paginate_queryset(student_assessments, request)
        
        # Pass both Global details and specific schedules for shift-matching
        serializer_context = {
            'exam_details': active_exam_details,
            'todays_schedules': list(todays_schedules)
        }
        serializer = UGAttendanceStudentSerializer(paginated_qs, many=True, context=serializer_context)


        paginated_response = paginator.get_paginated_response(serializer.data)
        paginated_response.data.update({
            "attendance_open": True,
            # "exam_details": active_exam_details,
        })
        return paginated_response


class UGAttendanceMarkView(APIView):
    """
    POST /api/ug/student-attendance/mark/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsExamCenterUser]

    def post(self, request):
        from datetime import datetime
        from django.db.models import Q

        is_bulk = isinstance(request.data, list)
        serializer = UGAttendanceMarkSerializer(data=request.data, many=is_bulk)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data_list = serializer.validated_data if is_bulk else [serializer.validated_data]

        uids = [item['assessment_uid'] for item in data_list]
        assessments_queryset = StudentCourseAssessment.objects.filter(
            uid__in=uids
        ).select_related('student')
        
        assessments_map = {str(a.uid): a for a in assessments_queryset}

        now_local = timezone.localtime(timezone.now())
        today = now_local.date()
        current_time = now_local.time()

        def parse_exam_time_window(exam_time_str):
            try:
                cleaned = exam_time_str.replace(' ', '').upper()
                parts = cleaned.split('-')
                if len(parts) < 2: return None, None
                start = datetime.strptime(parts[0], '%I:%M%p').time()
                end = datetime.strptime('-'.join(parts[1:]), '%I:%M%p').time()
                return start, end
            except Exception: return None, None

        schedule_cache = {}
        results = []
        to_update = []
        updated_at_now = timezone.now()

        for item in data_list:
            uid_str = str(item['assessment_uid'])
            is_absent = item['is_absent']
            
            assessment = assessments_map.get(uid_str)
            if not assessment:
                results.append({"assessment_uid": uid_str, "status": "error", "error": "Assessment not found."})
                continue

            course_name_key = (assessment.course_name or '').strip()
            cache_key = f"{course_name_key}"

            if cache_key not in schedule_cache:
                # Dynamic Filter: Course Name OR Exam Type (fallback for generic MJC/MIC schedules)
                time_filter = Q(exam_date=today) | Q(attendance_from__lte=now_local, attendance_to__gte=now_local)
                subject_filter = Q()

                if course_name_key:
                    subject_filter |= Q(exam_subject__course_name__iexact=course_name_key)
                
                c_type = (assessment.course_type or '').upper().strip()
                if c_type:
                    subject_filter |= Q(exam_type__iexact=c_type, exam_subject__isnull=True)

                if not course_name_key and not c_type:
                    subject_filter = Q(pk__isnull=True)

                schedules_today = UGExamSchedule.objects.filter(time_filter & subject_filter).distinct()
                
                active_slot_exists = False
                for sched in schedules_today:
                    # Priority: custom attendance fields
                    if sched.attendance_from and sched.attendance_to:
                        if sched.attendance_from <= now_local <= sched.attendance_to:
                            active_slot_exists = True
                            break
                        continue # Skip parsing if custom fields present but not matching

                    if not sched.exam_time: continue
                    start_t, end_t = parse_exam_time_window(sched.exam_time)
                    if start_t and end_t and start_t <= current_time <= end_t:
                        active_slot_exists = True
                        break
                        
                schedule_cache[cache_key] = active_slot_exists

            if not schedule_cache[cache_key]:
                err_msg = f"Attendance is not open for {course_name_key}. No active exam slot."
                if not is_bulk: return Response({"error": err_msg}, status=status.HTTP_403_FORBIDDEN)
                results.append({"assessment_uid": uid_str, "status": "error", "error": err_msg})
                continue

            assessment.ind_is_absent = is_absent
            assessment.updated_at = updated_at_now
            to_update.append(assessment)
            results.append({
                "assessment_uid": uid_str,
                "status": "success",
                "is_absent": assessment.ind_is_absent,
            })

        if to_update:
            StudentCourseAssessment.objects.bulk_update(to_update, ['ind_is_absent', 'updated_at'])

        return Response({
            "message": f"Processed {len(data_list)} records.",
            "results": results if is_bulk else results[0]
        }, status=status.HTTP_200_OK)


class UGCenterDropdown(APIView):
    permission_classes = []
    def get(self, request):
        centers = UGExamCenterMapping.objects.all().values('uid', 'center__name')
        return Response({"centers": list(centers)}, status=status.HTTP_200_OK)


class UGAttendanceCountView(APIView):
    permission_classes = []
    def get(self, request):
        from colleges.models import College
        from django.db.models import Q
        from .utils.memo_utils import get_ordinal

        exam_uid = request.query_params.get('exam_uid')
        semester_filter = request.query_params.get('semester')

        if not exam_uid:
            return Response({"error": "exam_uid is required."}, status=status.HTTP_400_BAD_REQUEST)

        exam = get_object_or_404(UGExam, uid=exam_uid)
        registration_qs = ExamRegistration.objects.filter(exam=exam, status='REGISTERED')

        if semester_filter:
            registration_qs = registration_qs.filter(sem=semester_filter)

        college_uid = request.query_params.get('college_uid')
        if college_uid:
            registration_qs = registration_qs.filter(student__college__uid=college_uid)

        registered_student_ids = registration_qs.values_list('student_id', flat=True).distinct()
        total_registered = registered_student_ids.count()

        assessment_qs = StudentCourseAssessment.objects.filter(
            student_id__in=registered_student_ids,
            label__iregex=r'^ESE',
            session=exam.session
        )

        if semester_filter:
             # In StudentCourseAssessment, semester is usually a string like "1ST", "2ND"
             sem_str = get_ordinal(semester_filter).upper()
             assessment_qs = assessment_qs.filter(semester__icontains=sem_str)

        assessments_values = assessment_qs.values('course_code', 'course_name', 'ind_is_absent')

        schedules = UGExamSchedule.objects.filter(exam=exam)
        exam_date_map = {}
        for s in schedules:
            if s.exam_subject and s.exam_subject.course_code:
                exam_date_map[s.exam_subject.course_code.upper().strip()] = s.exam_date

        subject_map = {}
        today = timezone.localdate()

        for a in assessments_values:
            code = (a['course_code'] or 'UNKNOWN').upper().strip()
            name = a['course_name'] or ''
            exam_date = exam_date_map.get(code)
            if not exam_date or exam_date > today: continue

            if code not in subject_map:
                subject_map[code] = {'course_code': code, 'course_name': name, 'present': 0, 'absent': 0, 'exam_date': exam_date}

            if a['ind_is_absent']: subject_map[code]['absent'] += 1
            else: subject_map[code]['present'] += 1

        subjects = []
        for code in sorted(subject_map.keys()):
            entry = subject_map[code]
            entry['total'] = entry['present'] + entry['absent']
            subjects.append(entry)

        return Response({
            "exam": str(exam),
            "exam_uid": str(exam.uid),
            "session": exam.session or "",
            "total_registered": total_registered,
            "subjects": subjects,
        }, status=status.HTTP_200_OK)


class UGExamDropDownloadView(APIView):
    permission_classes = []
    def get(self, request):
        exams = UGExam.objects.all()
        serializer = UGExamDropSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UGCenterDepartmentListView(APIView):
    """
    GET /api/ug/center/departments/
    List all active departments for UI dropdowns in Center Attendance.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = UGDepartment.objects.filter(is_publish=True).order_by('name')
        data = [
            {
                "uid": str(dept.uid),
                "name": dept.name,
                "code": getattr(dept, 'code', '')
            } for dept in departments
        ]
        return Response(data, status=status.HTTP_200_OK)
