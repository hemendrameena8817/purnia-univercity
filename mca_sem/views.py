from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils.pdf_generator import generate_mca_admit_card_pdf
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCACourseStructure, MCACommonCourseStructure,
    MCAExam, MCAExamSchedule, MCASemesterRegistration, 
    MCAExamRegistration, MCAStudentAssessment, MCAExamResult,
    MCAExamCenterMapping
)
import os
from django.conf import settings
from .serializers import (
    MCACourseSerializer, MCASessionSerializer,
    MCABatchSerializer, MCAStudentProfileSerializer,
    MCACourseStructureSerializer, MCACommonCourseStructureSerializer,
    MCAExamSerializer, MCAExamScheduleSerializer, 
    MCASemesterRegistrationSerializer, MCAExamRegistrationSerializer,
    MCAStudentAssessmentSerializer, MCAExamResultSerializer
)

# Course Views
class MCACourseListView(APIView):
    def get(self, request):
        courses = MCACourse.objects.all()
        serializer = MCACourseSerializer(courses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCACourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCACourseDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCACourse, uid=uid)

    def get(self, request, uid):
        course = self.get_object(uid)
        serializer = MCACourseSerializer(course)
        return Response(serializer.data)

    def put(self, request, uid):
        course = self.get_object(uid)
        serializer = MCACourseSerializer(course, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        course = self.get_object(uid)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Session Views
class MCASessionListView(APIView):
    def get(self, request):
        sessions = MCASession.objects.all()
        serializer = MCASessionSerializer(sessions, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCASessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCASessionDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCASession, uid=uid)

    def get(self, request, uid):
        session = self.get_object(uid)
        serializer = MCASessionSerializer(session)
        return Response(serializer.data)

    def put(self, request, uid):
        session = self.get_object(uid)
        serializer = MCASessionSerializer(session, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        session = self.get_object(uid)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Batch Views
class MCABatchListView(APIView):
    def get(self, request):
        batches = MCABatch.objects.all()
        serializer = MCABatchSerializer(batches, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCABatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCABatchDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCABatch, uid=uid)

    def get(self, request, uid):
        batch = self.get_object(uid)
        serializer = MCABatchSerializer(batch)
        return Response(serializer.data)

    def put(self, request, uid):
        batch = self.get_object(uid)
        serializer = MCABatchSerializer(batch, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        batch = self.get_object(uid)
        batch.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Student Profile Views
class MCAStudentProfileListView(APIView):
    def get(self, request):
        queryset = MCAStudentProfile.objects.all()
        roll_no = request.query_params.get('roll_no')
        if roll_no: queryset = queryset.filter(roll_no=roll_no)
        reg_no = request.query_params.get('registration_no')
        if reg_no: queryset = queryset.filter(registration_no=reg_no)
        serializer = MCAStudentProfileSerializer(queryset, many=True)
        return Response(serializer.data)

class MCAStudentProfileCreateView(APIView):
    def post(self, request):
        serializer = MCAStudentProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCAStudentProfileDetailView(APIView):
    def get_object(self, roll_no):
        return get_object_or_404(MCAStudentProfile, roll_no=roll_no)

    def get(self, request, roll_no):
        student = self.get_object(roll_no)
        serializer = MCAStudentProfileSerializer(student)
        return Response(serializer.data)

    def put(self, request, roll_no):
        student = self.get_object(roll_no)
        serializer = MCAStudentProfileSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, roll_no):
        student = self.get_object(roll_no)
        student.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Course Structure Views
class MCACourseStructureListView(APIView):
    def get(self, request):
        structures = MCACourseStructure.objects.all()
        serializer = MCACourseStructureSerializer(structures, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCACourseStructureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCACourseStructureDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCACourseStructure, uid=uid)

    def get(self, request, uid):
        structure = self.get_object(uid)
        serializer = MCACourseStructureSerializer(structure)
        return Response(serializer.data)

    def put(self, request, uid):
        structure = self.get_object(uid)
        serializer = MCACourseStructureSerializer(structure, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        structure = self.get_object(uid)
        structure.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Views
class MCAExamListView(APIView):
    def get(self, request):
        exams = MCAExam.objects.all()
        serializer = MCAExamSerializer(exams, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCAExamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCAExamDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCAExam, uid=uid)

    def get(self, request, uid):
        exam = self.get_object(uid)
        serializer = MCAExamSerializer(exam)
        return Response(serializer.data)

    def put(self, request, uid):
        exam = self.get_object(uid)
        serializer = MCAExamSerializer(exam, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        exam = self.get_object(uid)
        exam.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Schedule Views
class MCAExamScheduleListView(APIView):
    def get(self, request):
        queryset = MCAExamSchedule.objects.all()
        exam_id = request.query_params.get('exam')
        if exam_id: queryset = queryset.filter(exam_id=exam_id)
        serializer = MCAExamScheduleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCAExamScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCAExamScheduleDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCAExamSchedule, uid=uid)

    def get(self, request, uid):
        schedule = self.get_object(uid)
        serializer = MCAExamScheduleSerializer(schedule)
        return Response(serializer.data)

    def put(self, request, uid):
        schedule = self.get_object(uid)
        serializer = MCAExamScheduleSerializer(schedule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        schedule = self.get_object(uid)
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Assessment Views
class MCAStudentAssessmentListView(APIView):
    def get(self, request):
        queryset = MCAStudentAssessment.objects.all()
        student = request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        serializer = MCAStudentAssessmentSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCAStudentAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCAStudentAssessmentDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCAStudentAssessment, uid=uid)

    def get(self, request, uid):
        assessment = self.get_object(uid)
        serializer = MCAStudentAssessmentSerializer(assessment)
        return Response(serializer.data)

    def put(self, request, uid):
        assessment = self.get_object(uid)
        serializer = MCAStudentAssessmentSerializer(assessment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        assessment = self.get_object(uid)
        assessment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Result Views
class MCAExamResultListView(APIView):
    def get(self, request):
        queryset = MCAExamResult.objects.all()
        student = request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        serializer = MCAExamResultSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCAExamResultSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCAExamResultDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MCAExamResult, uid=uid)

    def get(self, request, uid):
        result = self.get_object(uid)
        serializer = MCAExamResultSerializer(result)
        return Response(serializer.data)

    def put(self, request, uid):
        result = self.get_object(uid)
        serializer = MCAExamResultSerializer(result, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        result = self.get_object(uid)
        result.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Registration Views
class MCASemesterRegistrationListView(APIView):
    def get(self, request):
        registrations = MCASemesterRegistration.objects.all()
        serializer = MCASemesterRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCASemesterRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MCAExamRegistrationListView(APIView):
    def get(self, request):
        registrations = MCAExamRegistration.objects.all()
        serializer = MCAExamRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MCAExamRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class MCAAdmitCardPDFView(View):
    """
    Generates and returns admit card PDF for a student.
    Query params: registration_no, exam_uid
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        exam_uid = request.GET.get("exam_uid")

        if not registration_no or not exam_uid:
            return HttpResponse("Registration number and Exam UID are required", status=400, content_type='text/plain')

        student = get_object_or_404(MCAStudentProfile, registration_no=registration_no)
        exam = get_object_or_404(MCAExam, uid=exam_uid)

        pdf_content = generate_mca_admit_card_pdf(student, exam)

        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500, content_type='text/plain')

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="Admit_Card_{registration_no}_SEM_{exam.semester}.pdf"'
        return response

class MCABulkAdmitCardPDFView(APIView):
    """
    Generates and saves admit card PDFs for all students registered for a specific exam.
    Query params: exam_uid
    """
    def get(self, request):
        exam_uid = request.GET.get("exam_uid")
        if not exam_uid:
            return Response({"error": "exam_uid is required"}, status=status.HTTP_400_BAD_REQUEST)

        exam = get_object_or_404(MCAExam, uid=exam_uid)
        
        # Find students who are actually registered for this specific exam
        registrations = MCAExamRegistration.objects.filter(exam=exam).select_related('student')
        
        if not registrations.exists():
            return Response({"message": f"No registrations found for Exam: {exam.name}"}, status=status.HTTP_404_NOT_FOUND)

        # Create directory for saving PDFs
        # Use a safe name for the directory
        safe_exam_name = "".join([c if c.isalnum() else "_" for c in str(exam.name)])
        save_dir_name = f"{safe_exam_name}_{str(exam_uid)[:8]}"
        save_dir = os.path.join(settings.MEDIA_ROOT, 'mca', 'admit_cards', save_dir_name)
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        success_count = 0
        failure_count = 0
        results = []

        for reg in registrations:
            student = reg.student
            if not student:
                continue
                
            reg_no = student.registration_no or f"unknown_{student.uid}"
            filename = f"Admit_Card_{reg_no}_SEM_{exam.semester}.pdf"
            file_path = os.path.join(save_dir, filename)

            try:
                pdf_content = generate_mca_admit_card_pdf(student, exam)
                if pdf_content:
                    with open(file_path, 'wb') as f:
                        f.write(pdf_content)
                    success_count += 1
                    relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    results.append({
                        "registration_no": reg_no,
                        "status": "success",
                        "url": f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                    })
                else:
                    failure_count += 1
                    results.append({"registration_no": reg_no, "status": "failed", "error": "PDF generation returned None"})
            except Exception as e:
                failure_count += 1
                results.append({"registration_no": reg_no, "status": "error", "error": str(e)})

        return Response({
            "message": "Bulk generation completed",
            "exam_name": exam.name,
            "total_attempted": registrations.count(),
            "success_count": success_count,
            "failure_count": failure_count,
            "save_directory": save_dir,
            "results": results
        })

class MCARollSheetPDFView(View):
    """
    Generates and returns Exam Roll Sheet PDF for MCA.
    Query params: exam_uid, college_uid
    """
    def get(self, request):
        from colleges.models import College
        from .utils.pdf_generator import generate_mca_roll_sheet_pdf
        
        exam_uid = request.GET.get("exam_uid")
        college_uid = request.GET.get("college_uid")

        if not all([exam_uid, college_uid]):
            return HttpResponse("exam_uid and college_uid are required", status=400, content_type='text/plain')

        exam = get_object_or_404(MCAExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)

        pdf_content = generate_mca_roll_sheet_pdf(exam, college)

        if not pdf_content:
            return HttpResponse(f"Failed to generate Roll Sheet for {college.name}. Ensure students are enrolled for this exam.", status=404, content_type='text/plain')

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        safe_college_name = "".join([c if c.isalnum() else "_" for c in college.name])
        response["Content-Disposition"] = f'{disposition}; filename="Roll_Sheet_{safe_college_name}_SEM_{exam.semester}.pdf"'
        return response

class MCAAttendanceSheetPDFView(View):
    """
    Generates and returns Student-wise Attendance Sheet PDF for MCA.
    Query params: exam_uid, college_uid
    """
    def get(self, request):
        from colleges.models import College
        from .utils.pdf_generator import generate_mca_attendance_sheet_pdf
        
        exam_uid = request.GET.get("exam_uid")
        college_uid = request.GET.get("college_uid")

        if not all([exam_uid, college_uid]):
            return HttpResponse("exam_uid and college_uid are required", status=400, content_type='text/plain')

        exam = get_object_or_404(MCAExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)

        pdf_content = generate_mca_attendance_sheet_pdf(exam, college)

        if not pdf_content:
            return HttpResponse(f"Failed to generate Attendance Sheets for {college.name}. Ensure students are registered for this exam.", status=404, content_type='text/plain')

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        safe_college_name = "".join([c if c.isalnum() else "_" for c in college.name])
        response["Content-Disposition"] = f'{disposition}; filename="Attendance_Sheets_{safe_college_name}_SEM_{exam.semester}.pdf"'
        return response

class MCATabularRecordPDFView(View):
    """
    Generates and returns MCA Tabular Record (TR) PDF.

    Query params:
        - college_uid (required)
        - exam_uid (required)
        - batch_uid (optional)
    """

    def get(self, request):
        from colleges.models import College
        from .utils.pdf_generator import generate_mca_tr_pdf
        from .models import (
            MCAStudentProfile,
            MCAStudentAssessment,
            MCAExam,
            MCAExamRegistration
        )

        college_uid = request.GET.get("college_uid")
        exam_uid = request.GET.get("exam_uid")
        batch_uid = request.GET.get("batch_uid")

        if not college_uid or not exam_uid:
            return HttpResponse(
                "college_uid and exam_uid are required",
                status=400,
                content_type='text/plain'
            )

        # 1️⃣ Get objects
        college = get_object_or_404(College, uid=college_uid)
        exam = get_object_or_404(MCAExam, uid=exam_uid)

        # 2️⃣ Get ONLY registered students for this exam + college
        registrations = MCAExamRegistration.objects.filter(
            exam=exam,
            student__college=college
        ).select_related('student')

        if not registrations.exists():
            return HttpResponse(
                f"No students registered for {exam.name} in {college.name}",
                status=404,
                content_type='text/plain'
            )

        # 3️⃣ Extract student IDs
        registered_student_ids = registrations.values_list('student_id', flat=True)

        students_qs = MCAStudentProfile.objects.filter(
            id__in=registered_student_ids
        )

        # 4️⃣ Apply batch filtering logic
        target_batch_uid = batch_uid

        if not target_batch_uid and exam.batch:
            # If batch not passed, use exam.batch automatically
            target_batch_uid = str(exam.batch.uid)
            students_qs = students_qs.filter(batch=exam.batch)

        elif target_batch_uid:
            students_qs = students_qs.filter(batch__uid=target_batch_uid)

        # 5️⃣ Ensure students have assessment data for this exam AND semester
        assessment_student_ids = MCAStudentAssessment.objects.filter(
            exam=exam,
            semester=str(exam.semester),  # <-- STRICT SEMESTER CHECK
            student_id__in=students_qs.values_list('id', flat=True)
        ).values_list('student_id', flat=True).distinct()

        students = students_qs.filter(
            id__in=assessment_student_ids
        ).order_by('roll_no')

        if not students.exists():
            return HttpResponse(
                f"No assessment data found for {exam.name} in {college.name}",
                status=404,
                content_type='text/plain'
            )

        # 6️⃣ Generate TR PDF
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[TR Generation] Found {students.count()} students for Exam '{exam.name}' and College '{college.name}'. Sending to PDF generator.")

        pdf_content = generate_mca_tr_pdf(
            students=students,
            college=college,
            exam=exam,
            batch_uid=target_batch_uid
        )

        if not pdf_content:
            return HttpResponse(
                "Failed to generate Tabular Record PDF.",
                status=500,
                content_type='text/plain'
            )

        # 7️⃣ Return PDF
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="MCA_TR_{college.college_code}_SEM_{exam.semester}.pdf"'
        )

        return response