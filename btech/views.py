from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils.pdf_generator import generate_btech_admit_card_pdf, generate_btech_roll_sheet_pdf
from .models import (
    BTechCourse, BTechBranch, BTechSession, BTechBatch, BTechStudentProfile, 
    BTechCourseStructure, BTechCommonCourseStructure,
    BTechExam, BTechExamSchedule, BTechYearRegistration, 
    BTechExamRegistration, BTechStudentAssessment, BTechExamResult,
    BTechExamCenterMapping
)
from colleges.models import College
import os
from django.conf import settings
from .serializers import (
    BTechCourseSerializer, BTechSessionSerializer,
    BTechBatchSerializer, BTechStudentProfileSerializer,
    BTechCourseStructureSerializer, BTechCommonCourseStructureSerializer,
    BTechExamSerializer, BTechExamScheduleSerializer, 
    BTechYearRegistrationSerializer, BTechExamRegistrationSerializer,
    BTechStudentAssessmentSerializer, BTechExamResultSerializer
)

# Course Views
class BTechCourseListView(APIView):
    def get(self, request):
        courses = BTechCourse.objects.all()
        serializer = BTechCourseSerializer(courses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechCourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechCourseDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechCourse, uid=uid)

    def get(self, request, uid):
        course = self.get_object(uid)
        serializer = BTechCourseSerializer(course)
        return Response(serializer.data)

    def put(self, request, uid):
        course = self.get_object(uid)
        serializer = BTechCourseSerializer(course, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        course = self.get_object(uid)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Session Views
class BTechSessionListView(APIView):
    def get(self, request):
        sessions = BTechSession.objects.all()
        serializer = BTechSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechSessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechSessionDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechSession, uid=uid)

    def get(self, request, uid):
        session = self.get_object(uid)
        serializer = BTechSessionSerializer(session)
        return Response(serializer.data)

    def put(self, request, uid):
        session = self.get_object(uid)
        serializer = BTechSessionSerializer(session, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        session = self.get_object(uid)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Batch Views
class BTechBatchListView(APIView):
    def get(self, request):
        batches = BTechBatch.objects.all()
        serializer = BTechBatchSerializer(batches, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechBatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechBatchDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechBatch, uid=uid)

    def get(self, request, uid):
        batch = self.get_object(uid)
        serializer = BTechBatchSerializer(batch)
        return Response(serializer.data)

    def put(self, request, uid):
        batch = self.get_object(uid)
        serializer = BTechBatchSerializer(batch, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        batch = self.get_object(uid)
        batch.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Student Profile Views
class BTechStudentProfileListView(APIView):
    def get(self, request):
        queryset = BTechStudentProfile.objects.all()
        roll_no = request.query_params.get('roll_no')
        if roll_no: queryset = queryset.filter(roll_no=roll_no)
        reg_no = request.query_params.get('registration_no')
        if reg_no: queryset = queryset.filter(registration_no=reg_no)
        serializer = BTechStudentProfileSerializer(queryset, many=True)
        return Response(serializer.data)

class BTechStudentProfileCreateView(APIView):
    def post(self, request):
        serializer = BTechStudentProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechStudentProfileDetailView(APIView):
    def get_object(self, roll_no):
        return get_object_or_404(BTechStudentProfile, roll_no=roll_no)

    def get(self, request, roll_no):
        student = self.get_object(roll_no)
        serializer = BTechStudentProfileSerializer(student)
        return Response(serializer.data)

    def put(self, request, roll_no):
        student = self.get_object(roll_no)
        serializer = BTechStudentProfileSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, roll_no):
        student = self.get_object(roll_no)
        student.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Course Structure Views
class BTechCourseStructureListView(APIView):
    def get(self, request):
        structures = BTechCourseStructure.objects.all()
        serializer = BTechCourseStructureSerializer(structures, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechCourseStructureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechCourseStructureDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechCourseStructure, uid=uid)

    def get(self, request, uid):
        structure = self.get_object(uid)
        serializer = BTechCourseStructureSerializer(structure)
        return Response(serializer.data)

    def put(self, request, uid):
        structure = self.get_object(uid)
        serializer = BTechCourseStructureSerializer(structure, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        structure = self.get_object(uid)
        structure.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Views
class BTechExamListView(APIView):
    def get(self, request):
        exams = BTechExam.objects.all()
        serializer = BTechExamSerializer(exams, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechExamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechExamDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechExam, uid=uid)

    def get(self, request, uid):
        exam = self.get_object(uid)
        serializer = BTechExamSerializer(exam)
        return Response(serializer.data)

    def put(self, request, uid):
        exam = self.get_object(uid)
        serializer = BTechExamSerializer(exam, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        exam = self.get_object(uid)
        exam.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Schedule Views
class BTechExamScheduleListView(APIView):
    def get(self, request):
        queryset = BTechExamSchedule.objects.all()
        exam_id = request.query_params.get('exam')
        if exam_id: queryset = queryset.filter(exam_id=exam_id)
        serializer = BTechExamScheduleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechExamScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechExamScheduleDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechExamSchedule, uid=uid)

    def get(self, request, uid):
        schedule = self.get_object(uid)
        serializer = BTechExamScheduleSerializer(schedule)
        return Response(serializer.data)

    def put(self, request, uid):
        schedule = self.get_object(uid)
        serializer = BTechExamScheduleSerializer(schedule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        schedule = self.get_object(uid)
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Assessment Views
class BTechStudentAssessmentListView(APIView):
    def get(self, request):
        queryset = BTechStudentAssessment.objects.all()
        student = request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        serializer = BTechStudentAssessmentSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechStudentAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechStudentAssessmentDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechStudentAssessment, uid=uid)

    def get(self, request, uid):
        assessment = self.get_object(uid)
        serializer = BTechStudentAssessmentSerializer(assessment)
        return Response(serializer.data)

    def put(self, request, uid):
        assessment = self.get_object(uid)
        serializer = BTechStudentAssessmentSerializer(assessment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        assessment = self.get_object(uid)
        assessment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Result Views
class BTechExamResultListView(APIView):
    def get(self, request):
        queryset = BTechExamResult.objects.all()
        student = request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        serializer = BTechExamResultSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechExamResultSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechExamResultDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(BTechExamResult, uid=uid)

    def get(self, request, uid):
        result = self.get_object(uid)
        serializer = BTechExamResultSerializer(result)
        return Response(serializer.data)

    def put(self, request, uid):
        result = self.get_object(uid)
        serializer = BTechExamResultSerializer(result, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        result = self.get_object(uid)
        result.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Registration Views
class BTechYearRegistrationListView(APIView):
    def get(self, request):
        registrations = BTechYearRegistration.objects.all()
        serializer = BTechYearRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechYearRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BTechExamRegistrationListView(APIView):
    def get(self, request):
        registrations = BTechExamRegistration.objects.all()
        serializer = BTechExamRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BTechExamRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class BTechAdmitCardPDFView(View):
    """
    Generates and returns admit card PDF for a student.
    Query params: registration_no, exam_uid
    """
    def get(self, request):
        registration_no = request.GET.get("registration_no")
        exam_uid = request.GET.get("exam_uid")

        if not registration_no or not exam_uid:
            return HttpResponse("Registration number and Exam UID are required", status=400, content_type='text/plain')

        student = get_object_or_404(BTechStudentProfile, registration_no=registration_no)
        exam = get_object_or_404(BTechExam, uid=exam_uid)

        pdf_content = generate_btech_admit_card_pdf(student, exam)

        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500, content_type='text/plain')

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="Admit_Card_{registration_no}_YEAR_{exam.year}.pdf"'
        return response

class BTechBulkAdmitCardPDFView(APIView):
    """
    Generates and saves admit card PDFs for all students registered for a specific exam.
    Query params: exam_uid
    """
    def get(self, request):
        exam_uid = request.GET.get("exam_uid")
        if not exam_uid:
            return Response({"error": "exam_uid is required"}, status=status.HTTP_400_BAD_REQUEST)

        exam = get_object_or_404(BTechExam, uid=exam_uid)
        
        # Find students who are actually registered for this specific exam
        registrations = BTechExamRegistration.objects.filter(exam=exam).select_related('student')
        
        if not registrations.exists():
            return Response({"message": f"No registrations found for Exam: {exam.name}"}, status=status.HTTP_404_NOT_FOUND)

        # Create directory for saving PDFs
        # Use a safe name for the directory
        safe_exam_name = "".join([c if c.isalnum() else "_" for c in str(exam.name)])
        save_dir_name = f"{safe_exam_name}_{str(exam_uid)[:8]}"
        save_dir = os.path.join(settings.MEDIA_ROOT, 'btech', 'admit_cards', save_dir_name)
        
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
            filename = f"Admit_Card_{reg_no}_YEAR_{exam.year}.pdf"
            file_path = os.path.join(save_dir, filename)

            try:
                pdf_content = generate_btech_admit_card_pdf(student, exam)
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

class BTechRollSheetPDFView(View):
    """
    Generates and returns Exam Roll Sheet PDF.
    Query params: exam_uid, college_uid, branch_uid
    """
    def get(self, request):
        exam_uid = request.GET.get("exam_uid")
        college_uid = request.GET.get("college_uid")
        branch_uid = request.GET.get("branch_uid")

        if not all([exam_uid, college_uid, branch_uid]):
            return HttpResponse("exam_uid, college_uid, and branch_uid are required", status=400, content_type='text/plain')

        exam = get_object_or_404(BTechExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)
        branch = get_object_or_404(BTechBranch, uid=branch_uid)

        pdf_content = generate_btech_roll_sheet_pdf(exam, college, branch)

        if not pdf_content:
            return HttpResponse(f"Failed to generate Roll Sheet for {college.name} - {branch.name}. Ensure students are registered for this exam.", status=404, content_type='text/plain')

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        safe_college_name = "".join([c if c.isalnum() else "_" for c in college.name])
        safe_branch_name = "".join([c if c.isalnum() else "_" for c in branch.name])
        response["Content-Disposition"] = f'{disposition}; filename="Roll_Sheet_{safe_college_name}_{safe_branch_name}_Year_{exam.year}.pdf"'
        return response
