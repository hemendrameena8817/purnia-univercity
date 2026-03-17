import os
from itertools import groupby

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views import View

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny

from accounts.permissions import IsUniversityAdmin
from .models import (
    LLBCourse, LLBSession, LLBBatch, LLBStudentProfile, 
    LLBCourseStructure, LLBExam, LLBStudentCourseAssessment,
    LLBExamCenterMapping
)
from .serializers import (
    LLBCourseSerializer, LLBSessionSerializer, LLBBatchSerializer,
    LLBStudentProfileSerializer, LLBCourseStructureSerializer, LLBExamSerializer,
    LLBStudentCourseAssessmentSerializer
)
from .utils.pdf_generator import generate_marksheet_pdf
from .utils.progressive_context import get_center_info_for_student
# from .debug_center_mapping import debug_center_mapping

def normalize_semester(semester):
    """Convert semester names to consistent format (1ST, 2ND, etc.)"""
    semester_mapping = {
        '1st': '1ST', 'first': '1ST', '1': '1ST',
        '2nd': '2ND', 'second': '2ND', '2': '2ND', 
        '3rd': '3RD', 'third': '3RD', '3': '3RD',
        '4th': '4TH', 'fourth': '4TH', '4': '4TH',
        '5th': '5TH', 'fifth': '5TH', '5': '5TH',
        '6th': '6TH', 'sixth': '6TH', '6': '6TH'
    }
    return semester_mapping.get(semester.lower(), semester.upper())

# Course Views
class LLBCourseListView(generics.ListCreateAPIView):
    queryset = LLBCourse.objects.all()
    serializer_class = LLBCourseSerializer


class LLBCourseStructureByPartView(APIView):
    """
    Returns the LLBCourseStructure entries filtered by semester (part).
    Optionally also filter by course_code.

    Query Params:
        - semester (required): e.g. 1ST, 2ND, 3RD, 4TH, 5TH, 6TH
        - course_code (optional): e.g. LLB-3

    Example:
        GET /api/llb/course-structure/?semester=1ST
        GET /api/llb/course-structure/?semester=2ND&course_code=LLB-3
    """
    permission_classes = [AllowAny]

    def get(self, request):
        semester = request.query_params.get('semester')
        course_code = request.query_params.get('course_code')

        if not semester:
            return Response(
                {"error": "Part is required (e.g. 1ST, 2ND, 3RD)"},
                status=http_status.HTTP_400_BAD_REQUEST
            )

        semester_normalized = normalize_semester(semester)

        queryset = LLBCourseStructure.objects.filter(
            semester__iexact=semester_normalized
        ).order_by('paper_code')

        if course_code:
            queryset = queryset.filter(course_code__iexact=course_code)

        serializer = LLBCourseStructureSerializer(queryset, many=True)
        return Response({
            'semester': semester_normalized,
            'count': queryset.count(),
            'course_structure': serializer.data
        }, status=http_status.HTTP_200_OK)

class LLBCourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBCourse.objects.all()
    serializer_class = LLBCourseSerializer

# Session Views
class LLBSessionListView(generics.ListCreateAPIView):
    queryset = LLBSession.objects.all()
    serializer_class = LLBSessionSerializer

class LLBSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBSession.objects.all()
    serializer_class = LLBSessionSerializer

# Batch Views
class LLBBatchListView(generics.ListCreateAPIView):
    queryset = LLBBatch.objects.all()
    serializer_class = LLBBatchSerializer

class LLBBatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBBatch.objects.all()
    serializer_class = LLBBatchSerializer

# Student Profile Views
class LLBStudentProfileListView(APIView):
    """List and create student profiles with filtering support"""
    def get(self, request):
        queryset = LLBStudentProfile.objects.all()
        
        roll_no = request.query_params.get('roll_no')
        if roll_no:
            queryset = queryset.filter(roll_no=roll_no)
            
        registration_no = request.query_params.get('registration_no')
        if registration_no:
            queryset = queryset.filter(registration_no=registration_no)
            
        batch = request.query_params.get('batch')
        if batch:
            queryset = queryset.filter(batch_id=batch)
            
        course = request.query_params.get('course')
        if course:
            queryset = queryset.filter(course_id=course)
            
        semester = request.query_params.get('semester')
        if semester:
            semester_normalized = normalize_semester(semester)
            queryset = queryset.filter(course_assessments__semester=semester_normalized).distinct()
        
        serializer = LLBStudentProfileSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = LLBStudentProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=http_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=http_status.HTTP_400_BAD_REQUEST)

class LLBStudentProfileDetailView(APIView):
    """Retrieve, update, or delete a student profile by UID"""
    def get_object(self, uid):
        return get_object_or_404(LLBStudentProfile, uid=uid)
    
    def get(self, request, uid):
        student = self.get_object(uid)
        serializer = LLBStudentProfileSerializer(student)
        return Response(serializer.data)
    
    def put(self, request, uid):
        student = self.get_object(uid)
        serializer = LLBStudentProfileSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=http_status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, uid):
        student = self.get_object(uid)
        student.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)

# Course Structure Views
class LLBCourseStructureListView(generics.ListCreateAPIView):
    queryset = LLBCourseStructure.objects.all()
    serializer_class = LLBCourseStructureSerializer

class LLBCourseStructureDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LLBCourseStructure.objects.all()
    serializer_class = LLBCourseStructureSerializer

# Exam Views
class LLBExamListView(APIView):
    """List and create exams with filtering support"""
    def get(self, request):
        queryset = LLBExam.objects.all()
        
        semester = request.query_params.get('semester')
        if semester:
            semester_normalized = normalize_semester(semester)
            queryset = queryset.filter(semester=semester_normalized)
            
        session = request.query_params.get('session')
        if session:
            queryset = queryset.filter(session__icontains=session)
            
        batch = request.query_params.get('batch')
        if batch:
            queryset = queryset.filter(batch_id=batch)
        
        serializer = LLBExamSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = LLBExamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=http_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=http_status.HTTP_400_BAD_REQUEST)

class LLBExamDetailView(APIView):
    """Retrieve, update, or delete an exam by UID"""
    def get_object(self, uid):
        return get_object_or_404(LLBExam, uid=uid)
    
    def get(self, request, uid):
        exam = self.get_object(uid)
        serializer = LLBExamSerializer(exam)
        return Response(serializer.data)
    
    def put(self, request, uid):
        exam = self.get_object(uid)
        serializer = LLBExamSerializer(exam, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=http_status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, uid):
        exam = self.get_object(uid)
        exam.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)

# Assessment (Marks) Views
class LLBStudentCourseAssessmentListView(APIView):
    """List and create assessments with filtering support"""
    def get(self, request):
        queryset = LLBStudentCourseAssessment.objects.all()
            
        semester = request.query_params.get('semester')
        if semester:
            semester_normalized = normalize_semester(semester)
            queryset = queryset.filter(semester=semester_normalized)
            
        student = request.query_params.get('student')
        if student:
            queryset = queryset.filter(student_id=student)
            
        exam = request.query_params.get('exam')
        if exam:
            queryset = queryset.filter(exam_id=exam)
            
        label = request.query_params.get('label')
        if label:
            queryset = queryset.filter(label__icontains=label)
        
        registration_no = request.query_params.get('registration_no')
        if registration_no:
            queryset = queryset.filter(student__registration_no=registration_no)
        
        serializer = LLBStudentCourseAssessmentSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = LLBStudentCourseAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=http_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=http_status.HTTP_400_BAD_REQUEST)

class LLBStudentCourseAssessmentDetailView(APIView):
    """Retrieve, update, or delete an assessment by UID"""
    def get_object(self, uid):
        return get_object_or_404(LLBStudentCourseAssessment, uid=uid)
    
    def get(self, request, uid):
        assessment = self.get_object(uid)
        serializer = LLBStudentCourseAssessmentSerializer(assessment)
        return Response(serializer.data)
    
    def put(self, request, uid):
        assessment = self.get_object(uid)
        serializer = LLBStudentCourseAssessmentSerializer(assessment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=http_status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, uid):
        assessment = self.get_object(uid)
        assessment.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)

class LLBStudentCourseAssessmentCreateView(APIView):
    """
    Create individual assessment entry for a student.
    Allows adding subject-wise entries one at a time.
    Similar to UGOldResultCreateView in ug_before_cbcs.
    """
    permission_classes = [IsUniversityAdmin]
    
    def post(self, request):
        # Required fields
        registration_no = request.data.get("registration_no")
        roll_no = request.data.get("roll_no")
        exam_uid = request.data.get("exam_uid")
        
        if not (registration_no or roll_no):
            return Response(
                {"error": "registration_no or roll_no is required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        
        if not exam_uid:
            return Response(
                {"error": "exam_uid is required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        
        # Get student
        if registration_no:
            student = get_object_or_404(LLBStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(LLBStudentProfile, roll_no=roll_no)
        
        # Get exam
        exam = get_object_or_404(LLBExam, uid=exam_uid)
        
        # course_structure_uid is required — resolve it first so we can derive other fields from it
        course_structure_uid = request.data.get("course_structure_uid")
        if not course_structure_uid:
            return Response(
                {"error": "course_structure_uid is required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        course_structure = LLBCourseStructure.objects.filter(uid=course_structure_uid).first()
        if not course_structure:
            return Response(
                {"error": f"No LLBCourseStructure found with uid={course_structure_uid}"},
                status=http_status.HTTP_404_NOT_FOUND
            )

        # Derive optional fields from course_structure if not explicitly sent
        # label  <- course_structure.status  (e.g. "ESE", "CIA")
        # paper_code <- course_structure.paper_code (if not provided)
        # ind_max_marks <- course_structure.full_marks
        # ind_pass_marks <- course_structure.pass_marks
        label = request.data.get("label") or course_structure.status or "ESE"
        if not paper_code:
            paper_code = course_structure.paper_code
        exam_type = request.data.get("exam_type", "REGULAR")
        semester = request.data.get("semester") or course_structure.semester or exam.semester
        if semester:
            semester = normalize_semester(semester)
        
        ind_max_marks = request.data.get("ind_max_marks") or course_structure.full_marks
        ind_pass_marks = request.data.get("ind_pass_marks") or course_structure.pass_marks
        
        # Check for duplicate entry
        existing = LLBStudentCourseAssessment.objects.filter(
            student=student,
            exam=exam,
            paper_code=paper_code,
            label=label
        ).first()
        
        if existing:
            return Response(
                {
                    "error": "Assessment entry already exists for this student, exam, paper_code, and label",
                    "existing_uid": str(existing.uid)
                },
                status=http_status.HTTP_409_CONFLICT
            )
        
        # Create new assessment entry
        assessment = LLBStudentCourseAssessment.objects.create(
            student=student,
            exam=exam,
            course=student.course,
            course_structure=course_structure,
            batch=student.batch,
            paper_code=paper_code,
            label=label,
            exam_type=exam_type,
            semester=semester,
            session=request.data.get("session", exam.session),
            college_code=request.data.get("college_code"),
            ind_max_marks=ind_max_marks,
            ind_pass_marks=ind_pass_marks,
            ind_marks_obtained=request.data.get("ind_marks_obtained"),
            ind_grace_obtained=request.data.get("ind_grace_obtained"),
            ind_is_absent=request.data.get("ind_is_absent", False),
            subject_result=request.data.get("subject_result"),
            grade=request.data.get("grade"),
        )
        
        return Response(
            {
                "message": "Assessment entry created successfully",
                "uid": str(assessment.uid),
                "student": {
                    "registration_no": student.registration_no,
                    "roll_no": student.roll_no,
                    "full_name": student.user.get_full_name()
                },
                "exam": {
                    "uid": str(exam.uid),
                    "name": exam.name,
                    "session": exam.session
                },
                "assessment": {
                    "paper_code": assessment.paper_code,
                    "label": assessment.label,
                    "exam_type": assessment.exam_type,
                    "ind_marks_obtained": assessment.ind_marks_obtained,
                    "ind_max_marks": assessment.ind_max_marks,
                    "course_structure_mapped": str(assessment.course_structure.uid) if assessment.course_structure else None,
                    "course_structure_name": assessment.course_structure.name if assessment.course_structure else None,
                }
            },
            status=http_status.HTTP_201_CREATED
        )

class LLBStudentCourseAssessmentDeleteView(APIView):
    """
    Delete individual assessment entry by UID.
    Similar to UGOldResultDeleteView in ug_before_cbcs.
    """
    permission_classes = [IsUniversityAdmin]
    
    def delete(self, request, uid):
        try:
            assessment = LLBStudentCourseAssessment.objects.get(uid=uid)
            deleted_info = {
                "uid": str(assessment.uid),
                "paper_code": assessment.paper_code,
                "label": assessment.label,
                "exam_type": assessment.exam_type,
                "ind_marks_obtained": assessment.ind_marks_obtained,
            }
            assessment.delete()
            return Response(
                {
                    "message": "Assessment entry deleted successfully",
                    "deleted_entry": deleted_info
                },
                status=http_status.HTTP_200_OK
            )
        except LLBStudentCourseAssessment.DoesNotExist:
            return Response(
                {"error": "Assessment entry not found"},
                status=http_status.HTTP_404_NOT_FOUND
            )


class LLBResultPDFView(View):
    """
    Generates and returns a single PDF marksheet for viewing/downloading.
    URL: /results/<registration_no>/pdf/?semester=1ST
    
    Modes (similar to ug_before_cbcs UGOldMarksheetPDFView):
      1. Default (no type, no session): Latest consolidated PDF.
         REGULAR + BACK papers merged, latest session overrides duplicates.
      2. ?session=2022-23: PDF for that specific session only.
      3. ?type=regular: Only REGULAR papers (original behavior).
      4. ?type=back: Only BACK papers (original behavior).
    
    Priority: session > type > default (latest consolidated)
    
    Query Parameters:
        - semester: Semester to return (1ST, 2ND, 3RD, etc.)
        - session: Optional. Generate PDF for a specific exam session.
        - type: Optional. 'regular' or 'back'. Ignored if session is provided.
    """
    def get(self, request, registration_no):
        semester = request.GET.get('semester', '1')
        semester_normalized = normalize_semester(semester)
        exam_type = request.GET.get('type', None)
        session_param = request.GET.get('session', None)
        
        student = get_object_or_404(LLBStudentProfile, registration_no=registration_no)
        
        # Priority: session > type > default (latest consolidated)
        if session_param or not exam_type:
            # Use latest consolidation logic (or specific session)
            from .utils.progressive_context import get_llb_latest_assessments
            
            assessments_list, exam = get_llb_latest_assessments(
                student, semester_normalized, session=session_param
            )
            
            if not assessments_list:
                session_msg = f" session={session_param}" if session_param else ""
                raise Http404(
                    f"No results found for {registration_no} in semester "
                    f"{semester_normalized}{session_msg}"
                )
        else:
            # Filter by exam_type only (original behavior)
            exam_type_value = None
            exam_type_lower = exam_type.lower()
            if exam_type_lower == 'regular':
                exam_type_value = 'Regular'
            elif exam_type_lower == 'back':
                exam_type_value = 'Back'
            
            filtered = LLBStudentCourseAssessment.objects.select_related(
                'student', 'student__user', 'student__course', 'student__college',
                'student__batch', 'exam', 'course_structure'
            ).filter(
                student=student,
                semester=semester_normalized,
                exam_type__iexact=exam_type_value
            ).exclude(exam__isnull=True).order_by('-exam__publication_date', 'paper_code')
            
            if not filtered.exists():
                raise Http404(
                    f"No results found for {registration_no} in semester "
                    f"{semester_normalized} ({exam_type_value})"
                )
            
            assessments_list = list(filtered)
            exam = assessments_list[0].exam

        pdf_content = generate_marksheet_pdf(
            semester=semester_normalized,
            student=student,
            exam=exam,
            assessments=assessments_list,
        )
        
        if not pdf_content:
            return HttpResponse("Failed to generate PDF", status=500, content_type='text/plain')
             
        response = HttpResponse(pdf_content, content_type='application/pdf')
        session_formatted = (exam.session or 'unknown').replace('-', '_')
        filename = f"MARKSHEET_{student.registration_no}_LLB_{session_formatted}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

class LLBBulkMarksheetGenerateView(APIView):
    """
    Generates PDF marksheets for all filtered filtered filtered results and saves them locally.
    Query Params: exam_id (required)
    """
    def post(self, request):
        exam_uid = request.data.get('exam_uid') or request.query_params.get('exam_uid')
        
        try:
            assessments = LLBStudentCourseAssessment.objects.select_related(
                'student', 'student__user', 'student__course', 'student__college', 'student__batch', 'exam', 'course_structure'
            ).exclude(exam__isnull=True).order_by('exam_id', 'student_id', 'paper_code')

            if exam_uid:
                assessments = assessments.filter(exam__uid=exam_uid)
                if not assessments.exists():
                    return Response({"error": f"No results found for exam_uid: {exam_uid}"}, status=http_status.HTTP_404_NOT_FOUND)

                exam = assessments.first().exam
                folder_name = f"Marksheets_{slugify(exam.name)}_{exam_uid}"
            else:
                if not assessments.exists():
                    return Response({"error": "No results found in the system"}, status=http_status.HTTP_404_NOT_FOUND)
                folder_name = "Marksheets_all"

            save_path = os.path.join(settings.MEDIA_ROOT, folder_name)
            os.makedirs(save_path, exist_ok=True)
            
            generated_count = 0

            for (exam_id, student_id), grouped in groupby(assessments, key=lambda assessment: (assessment.exam_id, assessment.student_id)):
                grouped_assessments = list(grouped)
                first_assessment = grouped_assessments[0]
                exam = first_assessment.exam
                student = first_assessment.student
                semester = normalize_semester(exam.semester) if exam and exam.semester else None

                pdf_content = generate_marksheet_pdf(
                    semester=semester,
                    student=student,
                    exam=exam,
                    assessments=grouped_assessments,
                )
                if pdf_content:
                    session_formatted = exam.session.replace('-', '_')
                    filename = f"MARKSHEET_{student.registration_no}_LLB_{session_formatted}.pdf"
                    file_path = os.path.join(save_path, filename)
                    with open(file_path, 'wb') as f:
                        f.write(pdf_content)
                    generated_count += 1
            
            return Response({
                "message": f"Successfully generated {generated_count} marksheets.",
                "directory": save_path
            }, status=http_status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

class LLBMarksheetJSONView(APIView):
    """
    Returns the Marksheet data in JSON format for a specific semester.
    Query params: registration_no or roll_no, semester, exam_uid (optional)
    """
    permission_classes = [IsUniversityAdmin]
    
    def get(self, request):
        registration_no = request.query_params.get("registration_no")
        roll_no = request.query_params.get("roll_no")
        semester = request.query_params.get("semester")
        exam_uid = request.query_params.get("exam_uid")
        
        if not (registration_no or roll_no) or not semester:
            return Response(
                {"error": "registration_no/roll_no and semester are required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        
        semester_normalized = normalize_semester(semester)
        
        if registration_no:
            student = get_object_or_404(LLBStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(LLBStudentProfile, roll_no=roll_no)
        
        # Get assessments
        assessment_filters = {
            'student': student,
            'semester': semester_normalized
        }
        
        if exam_uid:
            assessment_filters['exam__uid'] = exam_uid
        
        assessments = LLBStudentCourseAssessment.objects.filter(
            **assessment_filters
        ).select_related('course_structure', 'exam').order_by('paper_code')
        
        if not assessments.exists():
            return Response(
                {"error": f"No marksheet data found for {student.user.get_full_name()} ({semester_normalized})."},
                status=http_status.HTTP_404_NOT_FOUND
            )
        
        # Serialize assessments
        serializer = LLBStudentCourseAssessmentSerializer(assessments, many=True)
        
        # Get center info
        from .utils.progressive_context import get_center_info_for_student
        center_info = get_center_info_for_student(student, assessments.first().exam)
        center_name = center_info.get('name') if center_info else None
        
        context_data = {
            'student': {
                'uid': str(student.uid),
                'registration_no': student.registration_no,
                'roll_no': student.roll_no,
                'full_name': student.user.get_full_name(),
                'father_name': student.father_name,
                'mother_name': student.mother_name,
                'college_name': student.college.name if student.college else None,
                'course_name': student.course.name if student.course else None,
            },
            'semester': semester_normalized,
            'exam': {
                'uid': str(assessments.first().exam.uid) if assessments.first().exam else None,
                'name': assessments.first().exam.name if assessments.first().exam else None,
                'session': assessments.first().exam.session if assessments.first().exam else None,
            },
            'center_name': center_name,
            'assessments': serializer.data,
            'result_stats': calculate_llb_result(assessments),
        }
        
        return Response(context_data, status=http_status.HTTP_200_OK)

class LLBMarksheetProgressiveView(APIView):
    """
    Returns year-by-year progressive marksheet data showing how marks evolved.
    Useful for tracking regular vs back paper progression.
    Query params: registration_no or roll_no, semester
    """
    permission_classes = [IsUniversityAdmin]
    
    def get(self, request):
        registration_no = request.query_params.get("registration_no")
        roll_no = request.query_params.get("roll_no")
        semester = request.query_params.get("semester")
        
        if not (registration_no or roll_no) or not semester:
            return Response(
                {"error": "registration_no/roll_no and semester are required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        
        semester_normalized = normalize_semester(semester)
        
        if registration_no:
            student = get_object_or_404(LLBStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(LLBStudentProfile, roll_no=roll_no)
        
        # Get progressive contexts using utility function
        from .utils.progressive_context import get_llb_progressive_contexts
        
        progressive_data = get_llb_progressive_contexts(student, semester_normalized)
        
        if not progressive_data or not progressive_data.get('results'):
            return Response(
                {"error": f"No marksheet data found for {student.user.get_full_name()} ({semester_normalized})."},
                status=http_status.HTTP_404_NOT_FOUND
            )
        
        # Get center info for the first exam
        center_name = None
        if progressive_data.get('results'):
            first_result = progressive_data['results'][0]
            exam_info = first_result.get('exam')
            if exam_info and exam_info.get('uid'):
                try:
                    # Get the actual exam instance
                    actual_exam = LLBExam.objects.get(uid=exam_info['uid'])
                    center_info = get_center_info_for_student(student, actual_exam)
                    center_name = center_info.get('name') if center_info else None
                except LLBExam.DoesNotExist:
                    center_name = exam_info.get('name') or '-'
        
        # Build response
        response_data = {
            'student': {
                'uid': str(student.uid),
                'registration_no': student.registration_no,
                'roll_no': student.roll_no,
                'full_name': student.user.get_full_name(),
                'father_name': student.father_name,
                'mother_name': student.mother_name,
                'college_name': student.college.name if student.college else None,
                'course_name': student.course.name if student.course else None,
            },
            'semester': semester_normalized,
            'center_name': center_name,
            'available_sessions': progressive_data.get('available_sessions', []),
            'results': progressive_data.get('results', []),
        }
        
        return Response(response_data, status=http_status.HTTP_200_OK)

class LLBMarksheetUpdateView(APIView):
    """
    Updates Marksheet data (Exam details, Student info, and individual marks).
    Supports filtering by exam_type and session for targeted updates.
    Similar to UGOldMarksheetUpdateView in ug_before_cbcs.
    """
    permission_classes = [IsUniversityAdmin]
    
    def post(self, request):
        registration_no = request.data.get("registration_no")
        roll_no = request.data.get("roll_no")
        semester = request.data.get("semester")
        
        if not (registration_no or roll_no) or not semester:
            return Response(
                {"error": "registration_no/roll_no and semester are required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        
        semester_normalized = normalize_semester(semester)
        
        if registration_no:
            student = get_object_or_404(LLBStudentProfile, registration_no=registration_no)
        else:
            student = get_object_or_404(LLBStudentProfile, roll_no=roll_no)
        
        # Build assessment filters
        assessment_filters = {
            'student': student,
            'semester': semester_normalized
        }
        
        exam_uid = request.data.get("exam_uid")
        exam_type = request.data.get("exam_type")
        session = request.data.get("session")
        
        if exam_uid:
            assessment_filters['exam__uid'] = exam_uid
        if exam_type:
            assessment_filters['exam_type__iexact'] = exam_type
        if session:
            assessment_filters['exam__session'] = session
        
        assessments = LLBStudentCourseAssessment.objects.filter(
            **assessment_filters
        ).select_related('exam', 'course_structure')
        
        first_assessment = assessments.first()
        if not first_assessment:
            return Response(
                {"error": "No marksheet data found"},
                status=http_status.HTTP_404_NOT_FOUND
            )
        
        exam = first_assessment.exam
        
        # Update Exam details (if provided)
        exam_name = request.data.get("exam_name")
        exam_month_year = request.data.get("exam_month_year")
        publication_date = request.data.get("publication_date")
        new_session = request.data.get("new_session")
        centre_name = request.data.get("center_name") or request.data.get("centre_name")
        
        if exam and (exam_name or exam_month_year or publication_date or new_session):
            if exam_name:
                exam.name = exam_name
            if exam_month_year:
                exam.exam_month_year = exam_month_year
            if publication_date:
                exam.publication_date = publication_date
            if new_session:
                exam.session = new_session
            exam.save()
        
        # Update Center Mapping (if provided)
        center_college_uid = request.data.get("center_college_uid")
        
        if centre_name or center_college_uid:
            from .models import LLBExamCenterMapping
            from colleges.models import College
            
            if exam and student.college:
                # Find existing mapping
                mapping = LLBExamCenterMapping.objects.filter(
                    exams=exam,
                    attached_colleges=student.college
                ).first()
                
                if mapping:
                    # Update existing mapping
                    if center_college_uid:
                        try:
                            center_col = College.objects.get(uid=center_college_uid)
                            mapping.center = center_col
                        except College.DoesNotExist:
                            pass
                    # Note: center_name is not a field in current LLBExamCenterMapping
                else:
                    # Create new mapping
                    mapping_data = {}
                    if center_college_uid:
                        try:
                            center_col = College.objects.get(uid=center_college_uid)
                            mapping_data['center'] = center_col
                        except College.DoesNotExist:
                            pass
                    
                    mapping = LLBExamCenterMapping.objects.create(**mapping_data)
                    mapping.exams.add(exam)
                    mapping.attached_colleges.add(student.college)
        
        # Update Student details (if provided)
        father_name = request.data.get("father_name")
        mother_name = request.data.get("mother_name")
        student_name = request.data.get("student_name")
        
        student_updated = False
        if father_name:
            student.father_name = father_name
            student_updated = True
        if mother_name:
            student.mother_name = mother_name
            student_updated = True
        if student_name:
            user = student.user
            # Split into first and last name
            parts = student_name.strip().split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.save()
        
        if student_updated:
            student.save()
        
        # Update Marks
        marks_data = request.data.get("marks", [])
        for mark_item in marks_data:
            assessment_uid = mark_item.get("uid")
            paper_code = mark_item.get("paper_code")
            label = mark_item.get("label")
            
            assessment_obj = None
            if assessment_uid:
                assessment_obj = assessments.filter(uid=assessment_uid).first()
            elif paper_code:
                if label:
                    assessment_obj = assessments.filter(paper_code=paper_code, label=label).first()
                else:
                    assessment_obj = assessments.filter(paper_code=paper_code).first()
            
            if assessment_obj:
                obtained = mark_item.get("obtained_marks")
                if obtained is not None:
                    # Validation: obtained <= max marks
                    max_marks = assessment_obj.ind_max_marks or (
                        assessment_obj.course_structure.full_marks if assessment_obj.course_structure else None
                    )
                    if max_marks:
                        try:
                            obt_val = float(str(obtained))
                            max_val = float(str(max_marks))
                            if obt_val > max_val:
                                return Response(
                                    {"error": f"Mark {obt_val} for {assessment_obj.paper_code} exceeds maximum {max_val}"},
                                    status=http_status.HTTP_400_BAD_REQUEST
                                )
                        except (ValueError, TypeError):
                            pass
                    
                    assessment_obj.ind_marks_obtained = obtained
                
                if "subject_result" in mark_item:
                    assessment_obj.subject_result = mark_item["subject_result"]
                if "grade" in mark_item:
                    assessment_obj.grade = mark_item["grade"]
                if "ind_is_absent" in mark_item:
                    assessment_obj.ind_is_absent = mark_item["ind_is_absent"]
                if "ind_grace_obtained" in mark_item:
                    assessment_obj.ind_grace_obtained = mark_item["ind_grace_obtained"]
                
                assessment_obj.save()
        
        return Response({"message": "Marksheet updated successfully"}, status=http_status.HTTP_200_OK)
