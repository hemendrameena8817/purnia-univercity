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
    Query params: roll_no, exam_uid
    """
    def get(self, request):
        roll_no = request.GET.get("roll_no")
        exam_uid = request.GET.get("exam_uid")

        if not roll_no or not exam_uid:
            return HttpResponse("Roll number and Exam UID are required", status=400, content_type='text/plain')

        student = get_object_or_404(MCAStudentProfile, roll_no=roll_no)
        exam = get_object_or_404(MCAExam, uid=exam_uid)

        pdf_content = generate_mca_admit_card_pdf(student, exam)

        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500, content_type='text/plain')

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="admit_card_{roll_no}.pdf"'
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
        
        # Find registered students for this exam's semester and session
        registrations = MCAExamRegistration.objects.filter(
            sem=exam.semester,
            session=exam.session,
            # status='Approved'
        ).select_related('student')

        if not registrations.exists():
            return Response({"message": "No students found for this exam registration"}, status=status.HTTP_404_NOT_FOUND)

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
                
            roll_no = student.roll_no or student.registration_no or f"student_{student.uid}"
            filename = f"admit_card_{roll_no}.pdf"
            file_path = os.path.join(save_dir, filename)

            try:
                pdf_content = generate_mca_admit_card_pdf(student, exam)
                if pdf_content:
                    with open(file_path, 'wb') as f:
                        f.write(pdf_content)
                    success_count += 1
                    relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    results.append({
                        "roll_no": roll_no,
                        "status": "success",
                        "url": f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                    })
                else:
                    failure_count += 1
                    results.append({"roll_no": roll_no, "status": "failed", "error": "PDF generation returned None"})
            except Exception as e:
                failure_count += 1
                results.append({"roll_no": roll_no, "status": "error", "error": str(e)})

        return Response({
            "message": "Bulk generation completed",
            "exam_name": exam.name,
            "total_attempted": registrations.count(),
            "success_count": success_count,
            "failure_count": failure_count,
            "save_directory": save_dir,
            "results": results
        })
