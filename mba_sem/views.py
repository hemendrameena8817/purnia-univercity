from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils.pdf_generator import generate_mba_admit_card_pdf
from .models import *

import os
from django.conf import settings
from .serializers import *

# Course Views
class MBACourseListView(APIView):
    def get(self, request):
        courses = MBACourse.objects.all()
        serializer = MBACourseSerializer(courses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBACourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBACourseDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBACourse, uid=uid)

    def get(self, request, uid):
        course = self.get_object(uid)
        serializer = MBACourseSerializer(course)
        return Response(serializer.data)

    def put(self, request, uid):
        course = self.get_object(uid)
        serializer = MBACourseSerializer(course, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        course = self.get_object(uid)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Session Views
class MBASessionListView(APIView):
    def get(self, request):
        sessions = MBASession.objects.all()
        serializer = MBASessionSerializer(sessions, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBASessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBASessionDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBASession, uid=uid)

    def get(self, request, uid):
        session = self.get_object(uid)
        serializer = MBASessionSerializer(session)
        return Response(serializer.data)

    def put(self, request, uid):
        session = self.get_object(uid)
        serializer = MBASessionSerializer(session, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        session = self.get_object(uid)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Batch Views
class MBABatchListView(APIView):
    def get(self, request):
        batches = MBABatch.objects.all()
        serializer = MBABatchSerializer(batches, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBABatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBABatchDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBABatch, uid=uid)

    def get(self, request, uid):
        batch = self.get_object(uid)
        serializer = MBABatchSerializer(batch)
        return Response(serializer.data)

    def put(self, request, uid):
        batch = self.get_object(uid)
        serializer = MBABatchSerializer(batch, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        batch = self.get_object(uid)
        batch.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Student Profile Views
class MBAStudentProfileListView(APIView):
    def get(self, request):
        queryset = MBAStudentProfile.objects.all()
        roll_no = request.query_params.get('roll_no')
        if roll_no: queryset = queryset.filter(roll_no=roll_no)
        reg_no = request.query_params.get('registration_no')
        if reg_no: queryset = queryset.filter(registration_no=reg_no)
        serializer = MBAStudentProfileSerializer(queryset, many=True)
        return Response(serializer.data)

class MBAStudentProfileCreateView(APIView):
    def post(self, request):
        serializer = MBAStudentProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBAStudentProfileDetailView(APIView):
    def get_object(self, roll_no):
        return get_object_or_404(MBAStudentProfile, roll_no=roll_no)

    def get(self, request, roll_no):
        student = self.get_object(roll_no)
        serializer = MBAStudentProfileSerializer(student)
        return Response(serializer.data)

    def put(self, request, roll_no):
        student = self.get_object(roll_no)
        serializer = MBAStudentProfileSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, roll_no):
        student = self.get_object(roll_no)
        student.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Course Structure Views
class MBACourseStructureListView(APIView):
    def get(self, request):
        structures = MBACourseStructure.objects.all()
        serializer = MBACourseStructureSerializer(structures, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBACourseStructureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBACourseStructureDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBACourseStructure, uid=uid)

    def get(self, request, uid):
        structure = self.get_object(uid)
        serializer = MBACourseStructureSerializer(structure)
        return Response(serializer.data)

    def put(self, request, uid):
        structure = self.get_object(uid)
        serializer = MBACourseStructureSerializer(structure, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        structure = self.get_object(uid)
        structure.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Views
class MBAExamListView(APIView):
    def get(self, request):
        exams = MBAExam.objects.all()
        serializer = MBAExamSerializer(exams, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBAExamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBAExamDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBAExam, uid=uid)

    def get(self, request, uid):
        exam = self.get_object(uid)
        serializer = MBAExamSerializer(exam)
        return Response(serializer.data)

    def put(self, request, uid):
        exam = self.get_object(uid)
        serializer = MBAExamSerializer(exam, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        exam = self.get_object(uid)
        exam.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Schedule Views
class MBAExamScheduleListView(APIView):
    def get(self, request):
        queryset = MBAExamSchedule.objects.all()
        exam_id = request.query_params.get('exam')
        if exam_id: queryset = queryset.filter(exam_id=exam_id)
        serializer = MBAExamScheduleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBAExamScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBAExamScheduleDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBAExamSchedule, uid=uid)

    def get(self, request, uid):
        schedule = self.get_object(uid)
        serializer = MBAExamScheduleSerializer(schedule)
        return Response(serializer.data)

    def put(self, request, uid):
        schedule = self.get_object(uid)
        serializer = MBAExamScheduleSerializer(schedule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        schedule = self.get_object(uid)
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Assessment Views
class MBAStudentAssessmentListView(APIView):
    def get(self, request):
        queryset = MBAStudentAssessment.objects.all()
        student = request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        serializer = MBAStudentAssessmentSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBAStudentAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBAStudentAssessmentDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBAStudentAssessment, uid=uid)

    def get(self, request, uid):
        assessment = self.get_object(uid)
        serializer = MBAStudentAssessmentSerializer(assessment)
        return Response(serializer.data)

    def put(self, request, uid):
        assessment = self.get_object(uid)
        serializer = MBAStudentAssessmentSerializer(assessment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        assessment = self.get_object(uid)
        assessment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Exam Result Views
class MBAExamResultListView(APIView):
    def get(self, request):
        queryset = MBAExamResult.objects.all()
        student = request.query_params.get('student')
        if student: queryset = queryset.filter(student_id=student)
        serializer = MBAExamResultSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBAExamResultSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBAExamResultDetailView(APIView):
    def get_object(self, uid):
        return get_object_or_404(MBAExamResult, uid=uid)

    def get(self, request, uid):
        result = self.get_object(uid)
        serializer = MBAExamResultSerializer(result)
        return Response(serializer.data)

    def put(self, request, uid):
        result = self.get_object(uid)
        serializer = MBAExamResultSerializer(result, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uid):
        result = self.get_object(uid)
        result.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Registration Views
class MBASemesterRegistrationListView(APIView):
    def get(self, request):
        registrations = MBASemesterRegistration.objects.all()
        serializer = MBASemesterRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBASemesterRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MBAExamRegistrationListView(APIView):
    def get(self, request):
        registrations = MBAExamRegistration.objects.all()
        serializer = MBAExamRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MBAExamRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class MBAAdmitCardPDFView(View):
    """
    Generates and returns admit card PDF for a student.
    Query params: roll_no, exam_uid
    """
    def get(self, request):
        print("mca admit card")
        roll_no = request.GET.get("roll_no")
        exam_uid = request.GET.get("exam_uid")

        if not roll_no or not exam_uid:
            return HttpResponse("Roll number and Exam UID are required", status=400, content_type='text/plain')

        student = get_object_or_404(MBAStudentProfile, roll_no=roll_no)
        exam = get_object_or_404(MBAExam, uid=exam_uid)

        pdf_content = generate_mba_admit_card_pdf(student, exam)

        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500, content_type='text/plain')

        # Check if user wants to force download or view inline
        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="admit_card_{roll_no}.pdf"'
        return response

from rest_framework.permissions import AllowAny


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
import os

from .models import MBAExam, MBAStudentProfile
from .utils import pdf_generator


class MCABulkAdmitCardPDFView(APIView):
    permission_classes = [AllowAny]

    """
    MCA / MBA Bulk Admit Card PDF Generator

    Query Params:
        exam_uid (required) : UUID of exam
        roll_no  (required) : comma separated roll numbers
    """

    def get(self, request):

        # ------------------ GET & CLEAN PARAMS ------------------
        exam_uid = request.GET.get("exam_uid", "").strip()
        roll_nos = request.GET.get("roll_no", "").strip()

        # ------------------ VALIDATION ------------------
        if not exam_uid:
            return Response(
                {"error": "exam_uid is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not roll_nos:
            return Response(
                {"error": "roll_no is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ------------------ FETCH EXAM ------------------
        try:
            exam = get_object_or_404(MBAExam, uid=exam_uid)
        except Exception:
            return Response(
                {"error": "Invalid exam_uid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ------------------ ROLL NO LIST ------------------
        roll_no_list = [
            r.strip() for r in roll_nos.split(",") if r.strip()
        ]

        if not roll_no_list:
            return Response(
                {"error": "No valid roll numbers provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ------------------ FETCH STUDENTS ------------------
        students = MBAStudentProfile.objects.filter(
            roll_no__in=roll_no_list,
            is_active=True
        )

        if not students.exists():
            return Response(
                {"error": "No students found for given roll numbers"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ------------------ CREATE DIRECTORY ------------------
        safe_exam_name = "".join(
            c if c.isalnum() else "_" for c in str(exam.name)
        )

        save_dir_name = f"{safe_exam_name}_{str(exam_uid)[:8]}"
        save_dir = os.path.join(
            settings.MEDIA_ROOT, "mba_students", "admit_cards", save_dir_name
        )
        os.makedirs(save_dir, exist_ok=True)

        # ------------------ GENERATE PDFs ------------------
        success_count = 0
        failure_count = 0
        results = []    

        for student in students:
            roll_no = (
                student.roll_no
                or student.registration_no
                or str(student.uid)
            )

            file_name = f"admit_card_2nd_sem_{roll_no}.pdf"
            file_path = os.path.join(save_dir, file_name)

            try:
                pdf_content = generate_mba_admit_card_pdf(student, exam)

                if not pdf_content:
                    failure_count += 1
                    results.append({
                        "roll_no": roll_no,
                        "status": "failed",
                        "error": "PDF generation returned None"
                    })
                    continue

                with open(file_path, "wb") as pdf_file:
                    pdf_file.write(pdf_content)

                success_count += 1
                relative_path = os.path.relpath(
                    file_path, settings.MEDIA_ROOT
                )

                results.append({
                    "roll_no": roll_no,
                    "status": "success",
                    "url": f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
                })

            except Exception as e:
                failure_count += 1
                results.append({
                    "roll_no": roll_no,
                    "status": "error",
                    "error": str(e)
                })

        # ------------------ FINAL RESPONSE ------------------
        return Response({
            "message": "Bulk admit card PDF generation completed",
            "exam_name": exam.name,
            "exam_uid": exam_uid,
            "requested_roll_nos": roll_no_list,
            "total_students_found": students.count(),
            "success_count": success_count,
            "failure_count": failure_count,
            "save_directory": save_dir,
            "results": results
        }, status=status.HTTP_200_OK)



# class MCABulkAdmitCardPDFView(APIView):
#     """
#     Generates and saves admit card PDFs for given roll numbers.
#     Query params:
#         exam_uid (required)
#         roll_no (required) -> comma separated
#     """

#     def get(self, request):
#         print("ssj")
#         exam_uid = request.GET.get("exam_uid")
#         roll_nos = request.GET.get("roll_no")

#         if not exam_uid:
#             return Response(
#                 {"error": "exam_uid is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         if not roll_nos:
#             return Response(
#                 {"error": "roll_no is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # exam
#         exam = get_object_or_404(MBAExam, uid=exam_uid)

#         # roll_no list
#         roll_no_list = [r.strip() for r in roll_nos.split(",") if r.strip()]

#         # students from MBAStudentProfile only
#         students = MBAStudentProfile.objects.filter(
#             roll_no__in=roll_no_list,
#             is_active=True
#         )

#         if not students.exists():
#             return Response(
#                 {"message": "No students found for given roll numbers"},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         # directory
#         safe_exam_name = "".join(
#             [c if c.isalnum() else "_" for c in str(exam.name)]
#         )
#         save_dir_name = f"{safe_exam_name}_{str(exam_uid)[:8]}"
#         save_dir = os.path.join(
#             settings.MEDIA_ROOT, "mca", "admit_cards", save_dir_name
#         )
#         os.makedirs(save_dir, exist_ok=True)

#         success_count = 0
#         failure_count = 0
#         results = []

#         for student in students:
#             roll_no = student.roll_no or student.registration_no or str(student.uid)
#             filename = f"admit_card_{roll_no}.pdf"
#             file_path = os.path.join(save_dir, filename)

#             try:
#                 pdf_content = generate_mba_admit_card_pdf(student, exam)

#                 if not pdf_content:
#                     failure_count += 1
#                     results.append({
#                         "roll_no": roll_no,
#                         "status": "failed",
#                         "error": "PDF generation returned None"
#                     })
#                     continue

#                 with open(file_path, "wb") as f:
#                     f.write(pdf_content)

#                 success_count += 1
#                 relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)

#                 results.append({
#                     "roll_no": roll_no,
#                     "status": "success",
#                     "url": f"{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
#                 })

#             except Exception as e:
#                 failure_count += 1
#                 results.append({
#                     "roll_no": roll_no,
#                     "status": "error",
#                     "error": str(e)
#                 })

#         return Response({
#             "message": "Bulk admit card generation completed",
#             "exam_name": exam.name,
#             "requested_roll_nos": roll_no_list,
#             "total_students": students.count(),
#             "success_count": success_count,
#             "failure_count": failure_count,
#             "save_directory": save_dir,
#             "results": results
#         })
from colleges .models import *
from mba_sem.utils.pdf_generator import generate_mba_roll_sheet_pdf

class MBARollSheetPDFView(View):
    """
    Generates and returns Exam Roll Sheet PDF.
    Query params: exam_uid, college_uid, branch_uid
    """
    def get(self, request):
        exam_uid = request.GET.get("exam_uid")
        college_uid = request.GET.get("college_uid")
        course_uid = request.GET.get("course_uid")

        if not all([exam_uid, college_uid, course_uid]):
            return HttpResponse(
                "exam_uid, college_uid, and course_uid are required",
                status=400,
                content_type="text/plain"
            )

        exam = get_object_or_404(MBAExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)
        course = get_object_or_404(MBACourse, uid=course_uid)

        pdf_content = generate_mba_roll_sheet_pdf(
            exam=exam,
            college=college,
            course=course
        )

        if not pdf_content:
            return HttpResponse(
                f"Failed to generate Roll Sheet for {college.name} - {course.name}. "
                f"Ensure students are registered for this exam.",
                status=404,
                content_type="text/plain"
            )

        # inline / download
        download = request.GET.get("download", "false").lower() == "true"
        disposition = "attachment" if download else "inline"

        response = HttpResponse(pdf_content, content_type="application/pdf")

        safe_college_name = "".join(c if c.isalnum() else "_" for c in college.name)
        safe_course_name = "".join(c if c.isalnum() else "_" for c in course.name)

        response["Content-Disposition"] = (
            f'{disposition}; '
            f'filename="MBA_Roll_Sheet_{safe_college_name}_{safe_course_name}_'
            f'Sem_{exam.semester}_{exam.exam_month_year}.pdf"'
        )

        return response



class MBAAttendanceSheetPDFView(View):
    """
    Generates and returns Student-wise Attendance Sheet PDF for MBA.
    Query params: exam_uid, college_uid
    """
    def get(self, request):
        from colleges.models import College
        from mba_sem.models import MBAExam
        from .utils.pdf_generator import generate_mba_attendance_sheet_pdf
        from pup_umis_backend.utils.file_utils import image_to_base64, generate_barcode_base64
        print("MBA Attendence sheet")
        exam_uid = request.GET.get("exam_uid")
        college_uid = request.GET.get("college_uid")

        if not all([exam_uid, college_uid]):
            return HttpResponse(
                "exam_uid and college_uid are required",
                status=400,
                content_type='text/plain'
            )

        exam = get_object_or_404(MBAExam, uid=exam_uid)
        college = get_object_or_404(College, uid=college_uid)

        pdf_content = generate_mba_attendance_sheet_pdf(exam, college)

        if not pdf_content:
            return HttpResponse(
                f"No students found for {college.name} - Semester {exam.semester}",
                status=404,
                content_type='text/plain'
            )

        download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if download else 'inline'

        response = HttpResponse(pdf_content, content_type="application/pdf")
        safe_college_name = "".join(c if c.isalnum() else "_" for c in college.name)

        response["Content-Disposition"] = (
            f'{disposition}; filename="MBA_Attendance_Sheet_'
            f'{safe_college_name}_Sem_{exam.semester}.pdf"'
        )
        return response


