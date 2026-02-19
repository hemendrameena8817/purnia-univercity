from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from .models import PGStudentCourseAssessment, PGDepartment
from .serializers import PGStudentCourseAssessmentSerializer
from django.utils import timezone

class PGCIAMarksEntryView(APIView):
    """
    API View for Bulk CIA Marks Entry.
    Only accessible by college users who can manage marks.
    Restricted to students from the user's college.
    
    Request Body:
    [
        {"uid": "123e4567-e89b-12d3-a456-426614174000", "ind_marks_obtained": 25, "ind_is_absent": false},
        {"uid": "223e4567-e89b-12d3-a456-426614174001", "ind_marks_obtained": 0, "ind_is_absent": true}
    ]
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user is a college user
        if request.user.user_type != 'college_user':
            return Response({
                "error": "Access denied. Only college users can enter marks."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get college from user's college profile
        try:
            college_profile = request.user.college_profile
            user_college = college_profile.college
                
        except AttributeError:
            return Response({
                "error": "College profile not found for this user."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data
        if not isinstance(data, list):
            return Response({
                "error": "Expected a list of updates."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for item in data:
                assess_uid = item.get('uid')
                if not assess_uid:
                    errors.append({"error": "Missing 'uid' field", "item": item})
                    continue
                
                try:
                    assessment = PGStudentCourseAssessment.objects.select_for_update().get(uid=assess_uid)
                    
                    # Verify that the student belongs to the user's college
                    if assessment.student.college != user_college:
                        errors.append({
                            "uid": assess_uid,
                            "error": f"Student does not belong to your college. Student college: {assessment.student.college}, Your college: {user_college}"
                        })
                        continue
                        
                except PGStudentCourseAssessment.DoesNotExist:
                    errors.append({"error": f"Assessment with uid {assess_uid} not found."})
                    continue
                
                serializer = PGStudentCourseAssessmentSerializer(assessment, data=item, partial=True)
                if serializer.is_valid():
                    # Save the marks and set is_cia_fill to True
                    assessment_obj = serializer.save()
                    assessment_obj.is_cia_fill = True
                    assessment_obj.save()
                    updated_count += 1
                else:
                    errors.append({"uid": assess_uid, "errors": serializer.errors})
        
        response_data = {
            "message": f"Successfully updated {updated_count} records.",
        }
        
        if errors:
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
            
        return Response(response_data, status=status.HTTP_200_OK)


class PGCollegeStudentsView(APIView):
    """
    API View to get students from the logged-in college user's college.
    Queries from PGStudentCourseAssessment to get students with actual assessment records.
    
    Query Parameters:
    - department: Filter by department UID
    - semester: Filter by semester (e.g., '3RD')
    - batch: Filter by batch name (e.g., '2024-26')
    - session: Filter by session (e.g., '2024-25')
    
    Example: GET /api/pg/college-students/?department=<uid>&semester=3RD&batch=2024-26&session=2024-25
    
    Returns: List of students with uid and name only
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a college user
        if request.user.user_type != 'college_user':
            return Response({
                "error": "Access denied. Only college users can access this endpoint."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get college from user's college profile
        try:
            college_profile = request.user.college_profile
            user_college = college_profile.college
        except AttributeError:
            return Response({
                "error": "College profile not found for this user."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get query parameters
        department_uid = request.query_params.get('department')
        semester = request.query_params.get('semester')
        batch_name = request.query_params.get('batch')
        session = request.query_params.get('session')
        subject_uid = request.query_params.get('subject')
        
        # Build filter for assessments
        filters = {
            'student__college': user_college
        }
        
        if department_uid:
            filters['department__uid'] = department_uid
        if semester:
            filters['semester'] = semester
        # if batch_name:
        #     filters['batch__name'] = batch_name
        if session:
            filters['session'] = session
        if subject_uid:
            from .models import PGCourseStructure
            from django.core.exceptions import ValidationError
            try:
                subject = PGCourseStructure.objects.get(uid=subject_uid)
                # Filter by course_code from the subject (e.g., 'EC-1', 'CC-2')
                # Use either 'code' or 'course_code' field from PGCourseStructure
                course_code_value = subject.course_code or subject.code
                if course_code_value:
                    filters['course_code'] = course_code_value
                # Keep the user's semester filter - don't override it
            except (PGCourseStructure.DoesNotExist, ValidationError):
                 return Response({
                    "error": "Subject not found or invalid UID."
                }, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Status Filter
        status_filter = request.query_params.get('status', 'pending').lower() # Default to pending
        
        if status_filter == 'filled':
            filters['is_cia_fill'] = True
        elif status_filter == 'pending':
            filters['is_cia_fill'] = False
        # If 'all', we don't filter by is_cia_fill
        
        # Get assessments with student data
        assessments = PGStudentCourseAssessment.objects.filter(**filters).select_related('student')
        assessments = assessments.order_by('student__roll_no')

        # Build response with all assessment records
        # Each assessment is a separate entry (student may appear multiple times for different courses)
        students_data = []
        for assessment in assessments:
            students_data.append({
                'uid': assessment.uid,  # Assessment UID for marks entry
                'registration_no': assessment.student.registration_no,
                'roll_no': assessment.student.roll_no or '-',  # Roll number
                'name': f"{assessment.student.first_name} {assessment.student.last_name or ''}".strip(),
                'ind_max_marks': assessment.ind_max_marks,
                'ind_pass_marks': assessment.ind_pass_marks,
                'ind_marks_obtained': assessment.ind_marks_obtained,
                'ind_is_absent': assessment.ind_is_absent,
                'is_cia_fill': assessment.is_cia_fill,
                'updated_at': timezone.localtime(assessment.updated_at).strftime('%d-%m-%Y %I:%M %p') if assessment.updated_at else None
            })
        
        # Apply pagination
        from .pagination import StandardResultsSetPagination
        
        paginator = StandardResultsSetPagination()
        paginated_data = paginator.paginate_queryset(students_data, request)
        
        # Serialize the data
        from .serializers import PGCollegeStudentSerializer
        serializer = PGCollegeStudentSerializer(paginated_data, many=True)
        
        # Return paginated response
        return paginator.get_paginated_response(serializer.data)


class PGDepartmentDropdownView(APIView):
    """
    API View to get all PG departments for dropdown.
    Returns uid, name, and code for each department.
    
    Example: GET /api/pg/departments/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a college user
        if request.user.user_type != 'college_user':
            return Response({
                "error": "Access denied. Only college users can access this endpoint."
            }, status=status.HTTP_403_FORBIDDEN)
        
        from .serializers import PGDepartmentSerializer
        from accounts.models import CollegeUserProfile
        
        # Get user's college profile to check assigned department
        try:
            college_profile = CollegeUserProfile.objects.get(user=request.user)
            user_department = college_profile.PG_department
        except CollegeUserProfile.DoesNotExist:
            user_department = None
        
        # Filter departments based on user's assigned department
        if user_department:
            # User has a specific department assigned - show only that department
            departments = PGDepartment.objects.filter(id=user_department.id).order_by('name')
        else:
            # User has no department assigned - show all departments
            departments = PGDepartment.objects.all().order_by('name')
        
        serializer = PGDepartmentSerializer(departments, many=True)
        
        return Response({
            'total': departments.count(),
            'departments': serializer.data
        }, status=status.HTTP_200_OK)


class PGBatchDropdownView(APIView):
    """
    API View to get all PG batches for dropdown.
    Returns uid and name for each batch.
    
    Example: GET /api/pg/batches/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a college user
        if request.user.user_type != 'college_user':
            return Response({
                "error": "Access denied. Only college users can access this endpoint."
            }, status=status.HTTP_403_FORBIDDEN)
        
        from .models import PGBatch
        
        batches = PGBatch.objects.all().order_by('name')
        
        batches_data = [
            {
                'uid': str(batch.uid),
                'name': batch.name
            }
            for batch in batches
        ]
        
        return Response({
            'total': len(batches_data),
            'batches': batches_data
        }, status=status.HTTP_200_OK)


class PGSubjectDropdownView(APIView):
    """
    API View to get subjects (courses) for dropdown based on department and semester.
    
    Query Parameters:
    - department: Filter by Department UID (required)
    - semester: Filter by Semester (optional, e.g., '1ST', '2ND', '3RD', '4TH')
    
    Example: GET /api/pg/subjects/?department=<uid>&semester=3RD
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @staticmethod
    def roman_to_int(roman):
        """Convert Roman numeral to integer for sorting."""
        if not roman:
            return 0
        
        roman_values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }
        
        total = 0
        prev_value = 0
        
        for char in reversed(roman.upper()):
            value = roman_values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        
        return total
    
    @staticmethod
    def get_sort_key(subject):
        """
        Generate a sort key for subject code.
        Handles codes like 'EC-I', 'CC-II', 'DSE-III', etc.
        Places AECC and AEC subjects at the bottom.
        Returns tuple of (priority, prefix, numeric_value) for proper sorting.
        """
        code = subject.code or ''
        if not code:
            return (0, '', 0)
        
        # Split by hyphen to separate prefix from Roman numeral
        parts = code.split('-')
        if len(parts) >= 2:
            prefix = parts[0].strip()
            roman = parts[1].strip()
            numeric_value = PGSubjectDropdownView.roman_to_int(roman)
            
            # Place AECC and AEC at the bottom (priority 1), others at top (priority 0)
            priority = 1 if prefix in ['AECC', 'AEC'] else 0
            
            return (priority, prefix, numeric_value)
        else:
            # If no hyphen, just use the code as-is
            # Check if it's AECC or AEC
            priority = 1 if code.strip() in ['AECC', 'AEC'] else 0
            return (priority, code, 0)
    
    def get(self, request):
        # Check if user is a college user
        if request.user.user_type != 'college_user':
            return Response({
                "error": "Access denied. Only college users can access this endpoint."
            }, status=status.HTTP_403_FORBIDDEN)
        
        department_uid = request.query_params.get('department')
        semester = request.query_params.get('semester')
        
        if not department_uid:
            return Response({
                "error": "Department UID is required."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        from .models import PGCourseStructure
        from .serializers import PGSubjectDropdownSerializer
        
        # Build filters
        filters = {
            'department__uid': department_uid
        }
        
        # Add semester filter if provided
        if semester:
            filters['semester'] = semester
        
        # Get subjects filtered by department and optionally semester
        subjects = PGCourseStructure.objects.filter(
            **filters
        ).select_related('department')
        
        # Filter duplicates in Python (since distinct('field') is Postgres only)
        # We want unique courses based on course_name and code
        seen = set()
        unique_subjects = []
        for subject in subjects:
            identifier = (subject.course_name, subject.code)
            if identifier not in seen:
                seen.add(identifier)
                unique_subjects.append(subject)
        
        # Sort by code with proper Roman numeral ordering
        unique_subjects.sort(key=self.get_sort_key)
        
        serializer = PGSubjectDropdownSerializer(unique_subjects, many=True)
        

        return Response({
            'total': len(unique_subjects),
            'subjects': serializer.data
        }, status=status.HTTP_200_OK)


class PGStudentFilterView(APIView):
    """
    API View to get students filtered by Department and optionally by Subject.
    
    Query Parameters:
    - department: Department UID (required)
    - subject: Subject (Course) UID (optional)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        department_uid = request.query_params.get('department')
        subject_uid = request.query_params.get('subject') # This corresponds to PGCourseStructure UID
        
        if not department_uid:
            return Response({'error': 'Department UID is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Base query: Active students in the department
        from .models import PGStudentProfile, PGCourseStructure

        students = PGStudentProfile.objects.filter(
            department__uid=department_uid,
            is_active=True
        ).select_related('department', 'degree', 'program', 'college')

        # Filter by Subject if provided
        if subject_uid:
            try:
                subject = PGCourseStructure.objects.get(uid=subject_uid)
                # Filter students who have an assessment entry for this subject
                # We match on paper_code or course_code/code as needed. 
                # Ideally, assessment.paper_code matches course.code
                
                # Using paper_code from PGCourseStructure (which seems to be 'code' in the model based on previous view)
                target_code = subject.code 
                
                if target_code:
                     students = students.filter(
                        course_assessments__paper_code=target_code,
                        course_assessments__semester=subject.semester # Ensure semester matches too
                     ).distinct()
                else:
                    # If subject has no code, we might not be able to filter accurately by assessment
                     return Response({'error': 'Selected subject has no code'}, status=status.HTTP_400_BAD_REQUEST)

            except PGCourseStructure.DoesNotExist:
                return Response({'error': 'Subject not found'}, status=status.HTTP_404_NOT_FOUND)

        # Serialize
        # Use a lightweight serializer for the list view
        data = []
        for student in students:
            data.append({
                'uid': student.uid,
                'registration_no': student.registration_no,
                'name': student.get_full_name(),
                'father_name': student.father_name,
                'roll_no': student.roll_no,
                'program': student.program.name if student.program else None,
                'session': student.session,
                'semester': student.current_semester,
                'department': student.department.name if student.department else None
            })
            
        return Response(data, status=status.HTTP_200_OK)




# class PGFillDataView(APIView):
#     """
#     API View to get 'fill data' (json_data) for a specific assessment.
    
#     URL: /api/pg/fill-data/<uid>/
#     Method: GET
#     """
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, uid):
#         # 1. Fetch the assessment
#         try:
#             assessment = PGStudentCourseAssessment.objects.get(uid=uid)
#         except PGStudentCourseAssessment.DoesNotExist:
#             return Response({
#                 "error": "Assessment not found."
#             }, status=status.HTTP_404_NOT_FOUND)

#         # 2. Check permissions (Optional but recommended)
#         # If the user is a college user, ensure the student belongs to their college
#         if request.user.user_type == 'college_user':
#             try:
#                 college_profile = request.user.college_profile
#                 user_college = college_profile.college
#                 if assessment.student.college != user_college:
#                      return Response({
#                         "error": "Access denied. Student does not belong to your college."
#                     }, status=status.HTTP_403_FORBIDDEN)
#             except AttributeError:
#                  return Response({
#                     "error": "College profile not found."
#                 }, status=status.HTTP_400_BAD_REQUEST)
        
#         # 3. Return the json_data
#         return Response({
#             "uid": assessment.uid,
#             "json_data": assessment.json_data
#         }, status=status.HTTP_200_OK)

# class PGFillDataLookupView(APIView):
#     """
#     API View to get 'fill data' (json_data) by Student UID and Subject UID.
    
#     URL: /api/pg/fill-data/lookup/?student=<uid>&subject=<uid>
#     Method: GET
#     """
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         student_uid = request.query_params.get('student')
#         subject_uid = request.query_params.get('subject')

#         if not student_uid or not subject_uid:
#             return Response({
#                 "error": "Both 'student' and 'subject' query parameters are required."
#             }, status=status.HTTP_400_BAD_REQUEST)

#         # 1. Fetch Subject to get the paper code
#         from .models import PGCourseStructure
#         try:
#             subject = PGCourseStructure.objects.get(uid=subject_uid)
#             target_code = subject.code
#             if not target_code:
#                  return Response({
#                     "error": "The selected subject does not have a valid code."
#                 }, status=status.HTTP_400_BAD_REQUEST)
#         except PGCourseStructure.DoesNotExist:
#             return Response({
#                 "error": "Subject not found."
#             }, status=status.HTTP_404_NOT_FOUND)

#         # 2. Fetch Assessment matching Student and Subject Code
#         try:
#             # We filter by student and paper_code (or course_code which seems to be used interchangeably)
#             # Taking the most recent one if multiple exist (though ideally unique per semester/session)
#             assessment = PGStudentCourseAssessment.objects.filter(
#                 student__uid=student_uid,
#                 paper_code=target_code,
#                 semester=subject.semester # Ensure semester matches
#             ).order_by('-created_at').first()

#             if not assessment:
#                  return Response({
#                     "error": "No assessment found for this student and subject."
#                 }, status=status.HTTP_404_NOT_FOUND)
        
#         except Exception as e:
#              return Response({
#                 "error": f"Error finding assessment: {str(e)}"
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         # 3. Check permissions
#         if request.user.user_type == 'college_user':
#             try:
#                 college_profile = request.user.college_profile
#                 user_college = college_profile.college
#                 if assessment.student.college != user_college:
#                      return Response({
#                         "error": "Access denied. Student does not belong to your college."
#                     }, status=status.HTTP_403_FORBIDDEN)
#             except AttributeError:
#                  return Response({
#                     "error": "College profile not found."
#                 }, status=status.HTTP_400_BAD_REQUEST)

#         # 4. Return Data
#         return Response({
#             "uid": assessment.uid,
#             "json_data": assessment.json_data
#         }, status=status.HTTP_200_OK)


class PGExamRegistrationDetailView(APIView):
    """
    API View to get Exam Registration details including student profile and assessments.
    Student is identified from the JWT token (no student_uid param needed).
    
    Query Parameters:
    - sem: Semester (optional, returns most recent registration if not provided)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import PGStudentProfile, PGExamRegistration
        from django.utils import timezone

        try:
            student = PGStudentProfile.objects.select_related(
                'department', 'degree', 'program', 'college'
            ).get(user=request.user)
        except PGStudentProfile.DoesNotExist:
            return Response(
                {'error': 'No PG student profile found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from .services.pg_registration_eligiblity import check_pg_registration_eligibility
        from .serializers import PGExamRegistrationSerializer
        from django.utils import timezone as tz

        sem = request.query_params.get('sem')
        response_data = check_pg_registration_eligibility(student, semester=sem)

        # Pull out the raw registration object (private key set by service)
        registration_obj = response_data.pop('_registration', None)

        if registration_obj is not None:
            # Build registration_window here in the view
            def fmt_date(dt):
                if not dt:
                    return None
                return tz.localtime(dt).strftime('%d %b %Y, %I:%M %p')

            response_data['registration_window'] = {
                'start_date': fmt_date(registration_obj.start_date),
                'end_date': fmt_date(registration_obj.end_date),
                'status': registration_obj.status,
            }

            # Serialize registration
            response_data['registration'] = PGExamRegistrationSerializer(registration_obj).data

        status_code = status.HTTP_200_OK
        if not response_data.get('eligible') and 'reason' in response_data:
             # If not eligible due to no record found, service returns reason
             # We might want 404 if no record, or just 200 with eligible=False depending on frontend needs.
             # Original code returned 404 for 'No exam registration record found'.
             if 'No exam registration record found' in response_data['reason']:
                 status_code = status.HTTP_404_NOT_FOUND

        return Response(response_data, status=status_code)
 


class PGRegistrationCardPDFView(APIView):
    """
    GET /api/pg/registration-card/
    Generates a PG Registration Card PDF for the logged-in student.
    Fetches the latest 'REGISTERED' exam registration for the user.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import PGExamRegistration, PGStudentProfile
        from .utils.registration_card_pdf import generate_pg_registration_card_pdf
        from django.http import HttpResponse

        # ── Resolve Student ───────────────────────────────────────────────────
        try:
            student = PGStudentProfile.objects.select_related(
                'college', 'department', 'program', 'degree'
            ).get(user=request.user)
        except PGStudentProfile.DoesNotExist:
             return Response(
                 {'error': 'PG Student profile not found for this user.'},
                 status=status.HTTP_404_NOT_FOUND
             )

        # ── Find Latest REGISTERED Registration ──────────────────────────────
        registration = PGExamRegistration.objects.defer('admission_receipt').filter(
            student=student,
            status='REGISTERED'
        ).select_related('student', 'student__college', 'student__department').order_by('-created_at').first()

        if not registration:
            return Response(
                {'error': 'No active REGISTERED exam registration found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ── Generate PDF ──────────────────────────────────────────────────────
        pdf_buffer = generate_pg_registration_card_pdf(
            student, 
            registration
        )
        
        if not pdf_buffer:
            return Response(
                {'error': 'Failed to generate PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        force_download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if force_download else 'inline'
        filename = f"PG_Registration_{student.registration_no}.pdf"

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response


class PGAdmitCardPDFView(APIView):
    """
    Generates and returns an Admit Card PDF for the logged-in PG student.

    No query parameters needed — the student is identified from the JWT token
    and the exam is resolved automatically via PGExamSchedule for the
    student's department (picks the nearest upcoming exam).

    Optional:
    - download : 'true' to force download (default: inline)

    Example: GET /api/pg/admit-card/
             GET /api/pg/admit-card/?download=true
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import PGStudentProfile, PGExam
        from django.shortcuts import get_object_or_404
        from .utils.pdf_generator import generate_pg_admit_card_pdf

        # ── Resolve student from request.user ──────────────────────────────────
        try:
            # Need strict match? Or allow college user to view admit card? 
            # Original code implies logged-in student.
            # Assuming 'student' user_type for now.
            if hasattr(request.user, 'pg_student_profile'):
                 student = request.user.pg_student_profile
            else:
                 return Response({'error': 'PG Student profile not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
            
        # ... rest of admit card logic ... (I am overwriting the start of PGAdmitCard? No I should define *before* or *after*).
        # Ah, replace_file_content replaces a block. I should append the new class *after* PGAdmitCardPDFView logic.
        
        from .models import PGStudentProfile, PGExam
        from django.shortcuts import get_object_or_404
        from .utils.pdf_generator import generate_pg_admit_card_pdf

        # ── Resolve student from request.user ──────────────────────────────────
        try:
            student = PGStudentProfile.objects.select_related(
                'college', 'department', 'program', 'degree'
            ).get(user=request.user)
        except PGStudentProfile.DoesNotExist:
            return Response(
                {'error': 'No PG student profile found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ── Auto-resolve exam via PGExamSchedule ──────────────────────────────
        from .models import PGExamSchedule
        from django.utils import timezone as tz
        from datetime import timedelta

        # Include exams from last 30 days so recently-started exams still work
        cutoff_date = tz.now().date() - timedelta(days=30)

        schedule = PGExamSchedule.objects.filter(
            group__department=student.department,
            exam_date__gte=cutoff_date          # upcoming or recently started
        ).select_related('exam').order_by('-exam__created_at').first()

        if not schedule or not schedule.exam:
            return Response(
                {'error': 'No active exam schedule found for your department.'},
                status=status.HTTP_404_NOT_FOUND
            )

        exam = schedule.exam

        # ── Generate PDF ───────────────────────────────────────────────────────
        pdf_content = generate_pg_admit_card_pdf(student, exam)

        if not pdf_content:
            return Response(
                {'error': 'Failed to generate PDF. Please check server logs.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        download = request.GET.get("download", "false").lower() == "true"
        disposition = "attachment" if download else "inline"
        safe_reg = "".join(c if c.isalnum() else "_" for c in student.registration_no)


        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'{disposition}; filename="PG_Admit_Card_{safe_reg}.pdf"'
        )
        return response


# ─────────────────────────────────────────────────────────────────────────────
# PG PAYMENT VIEWS  (CC Avenue)
# ─────────────────────────────────────────────────────────────────────────────

class PGPaymentInfoView(APIView):
    """
    GET  /pg/payment-info/?registration_uid=<uid>
    Returns fee amount and student details before initiating payment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import PGExamRegistration, PGStudentProfile, PGExamRegistrationPayment

        try:
            student = PGStudentProfile.objects.get(user=request.user)
        except PGStudentProfile.DoesNotExist:
            return Response({'error': 'No PG student profile found.'}, status=status.HTTP_404_NOT_FOUND)

        registration_uid = request.query_params.get('registration_uid')
        if registration_uid:
            try:
                registration = PGExamRegistration.objects.get(uid=registration_uid, student=student)
            except PGExamRegistration.DoesNotExist:
                return Response({'error': 'Registration not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            registration = PGExamRegistration.objects.filter(student=student).order_by('-sem', '-created_at').first()
            if not registration:
                return Response({'error': 'No exam registration found.'}, status=status.HTTP_404_NOT_FOUND)

        if registration.status == 'REGISTERED':
            return Response({
                'message': 'Payment already completed. Registration is confirmed.',
                'payment_required': False,
                'registration_uid': str(registration.uid),
            }, status=status.HTTP_200_OK)

        if not registration.fees or registration.fees <= 0:
            return Response({'error': 'Fee amount not set for this registration. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)

        # Latest payment status
        latest_payment = registration.payments.order_by('-created_at').first()

        return Response({
            'payment_required': True,
            'registration_uid': str(registration.uid),
            'student_name': student.get_full_name(),
            'father_name': student.father_name,
            'registration_no': student.registration_no,
            'sem': registration.sem,
            'session': registration.session,
            'exam_type': registration.exam_type,
            'amount': registration.fees,
            'latest_payment_status': latest_payment.payment_status if latest_payment else None,
        }, status=status.HTTP_200_OK)


class PGInitiatePaymentView(APIView):
    """
    POST  /pg/initiate-payment/
    Body: { "registration_uid": "<uid>" }
    Generates CC Avenue encrypted order and returns enc_request + access_code.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .models import PGExamRegistration, PGStudentProfile, PGExamRegistrationPayment
        from .utils.ccavenue_utils import encrypt
        from decouple import config
        import uuid as uuid_lib

        try:
            student = PGStudentProfile.objects.get(user=request.user)
        except PGStudentProfile.DoesNotExist:
            return Response({'error': 'No PG student profile found.'}, status=status.HTTP_404_NOT_FOUND)

        registration_uid = request.data.get('registration_uid') or request.data.get('registration_no')
        if not registration_uid:
            return Response({'error': 'registration_uid or registration_no is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Accept either UUID or student registration_no
        import uuid as _uuid
        registration = None
        try:
            _uuid.UUID(str(registration_uid))          # valid UUID?
            registration = PGExamRegistration.objects.filter(
                uid=registration_uid, student=student
            ).first()
        except ValueError:
            pass  # not a UUID — fall through to registration_no lookup

        if registration is None:
            # Fallback: look up by student registration_no
            try:
                prof = PGStudentProfile.objects.get(registration_no=registration_uid)
                registration = PGExamRegistration.objects.filter(
                    student=prof
                ).order_by('-sem', '-created_at').first()
            except PGStudentProfile.DoesNotExist:
                pass

        if registration is None:
            return Response({'error': 'Registration not found.'}, status=status.HTTP_404_NOT_FOUND)


        if registration.status == 'REGISTERED':
            return Response({'error': 'Registration already confirmed. Payment not required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not registration.fees or registration.fees <= 0:
            return Response({'error': 'Fee amount not configured for this registration.'}, status=status.HTTP_400_BAD_REQUEST)

        merchant_id = config('CCAVENUE_MERCHANT_ID', default='')
        access_code = config('CCAVENUE_ACCESS_CODE', default='')
        working_key = config('CCAVENUE_WORKING_KEY', default='')
        redirect_url = config(
            'CCAVENUE_PG_REDIRECT_URL',
            default=f"{request.scheme}://{request.get_host()}/api/pg/payment-response/"
        )
        cancel_url = redirect_url

        amount = str(registration.fees)
        order_id = f"PG_{uuid_lib.uuid4().hex[:12].upper()}"

        PGExamRegistrationPayment.objects.create(
            registration=registration,
            order_id=order_id,
            amount=amount,
            payment_status='PENDING'
        )

        merchant_data = (
            f"merchant_id={merchant_id}&order_id={order_id}&"
            f"amount={amount}&currency=INR&"
            f"redirect_url={redirect_url}&cancel_url={cancel_url}&"
            f"language=EN&billing_name={student.get_full_name()}&"
            f"billing_tel={student.mobile_no or ''}&"
            f"billing_email={student.user.email if hasattr(student, 'user') else ''}"
        )

        encrypted_data = encrypt(merchant_data, working_key)
        ccavenue_url = config('CCAVENUE_URL', default='https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction')

        return Response({
            'order_id': order_id,
            'enc_request': encrypted_data,
            'access_code': access_code,
            'production_url': ccavenue_url,
        }, status=status.HTTP_200_OK)


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class PGPaymentResponseView(APIView):
    """
    POST  /pg/payment-response/
    CC Avenue posts the encrypted payment result here.
    Decrypts the response, updates payment record, marks registration REGISTERED on success,
    then redirects to the frontend.
    """
    permission_classes = []  # CC Avenue posts here — no JWT

    def post(self, request):
        import logging
        from django.shortcuts import redirect as django_redirect
        from .models import PGExamRegistrationPayment
        from .utils.ccavenue_utils import decrypt, parse_response
        from decouple import config

        logger = logging.getLogger(__name__)
        logger.info(f"PG Payment response received. Data: {request.data}")

        if request.content_type == 'application/x-www-form-urlencoded':
            enc_response = request.POST.get('encResp')
        else:
            enc_response = request.data.get('encResp')

        if not enc_response:
            logger.error("No encResp parameter in PG payment response")
            return Response({'error': 'Invalid response: Missing encResp parameter'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            working_key = config('CCAVENUE_WORKING_KEY')
            decrypted_response = decrypt(enc_response, working_key)
            response_data = parse_response(decrypted_response)
            logger.info(f"PG Decrypted response: {response_data}")

            order_id = response_data.get('order_id')
            auth_status = response_data.get('order_status', '').lower()

            if not order_id:
                raise ValueError("No order_id in decrypted response")

            try:
                payment = PGExamRegistrationPayment.objects.select_related('registration').get(order_id=order_id)
            except PGExamRegistrationPayment.DoesNotExist:
                logger.error(f"PG Payment record not found for order_id: {order_id}")
                return Response({'error': 'Payment record not found'}, status=status.HTTP_404_NOT_FOUND)

            payment.tracking_id = response_data.get('tracking_id')
            payment.bank_ref_no = response_data.get('bank_ref_no')
            payment.payment_mode = response_data.get('payment_mode')
            payment.raw_response = response_data

            if auth_status == 'success':
                payment.payment_status = 'SUCCESS'
                reg = payment.registration
                reg.status = 'REGISTERED'
                reg.save()
                logger.info(f"PG Registration confirmed for order_id: {order_id}")
            elif auth_status == 'aborted':
                payment.payment_status = 'ABORTED'
            else:
                payment.payment_status = 'FAILED'

            payment.save()

            frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
            uid = str(payment.registration.uid)
            redirect_url = (
                f"{frontend_url}/pg-registration/"
                f"?uid={uid}"
                f"&payment_status={payment.payment_status.lower()}"
                f"&order_id={order_id}"
            )
            return django_redirect(redirect_url)

        except Exception as e:
            logger.exception("Error processing PG payment response")
            frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
            return django_redirect(f"{frontend_url}/pg/payment-status?error={str(e)[:100]}")


class PGStudentUploadView(APIView):
    """
    POST /pg/student-image-upload/
    Uploads student's photo and signature.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import logging
        from .models import PGStudentProfile, PGExamRegistration, PGExamRegistrationPayment

        logger = logging.getLogger(__name__)

        # ── 1. Resolve student from JWT ───────────────────────────────────────
        try:
            student = PGStudentProfile.objects.get(user=request.user)
        except PGStudentProfile.DoesNotExist:
            return Response(
                {'error': 'No PG student profile found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ── 2. Resolve target registration ────────────────────────────────────
        registration_uid = request.data.get('registration_uid')
        if registration_uid:
            try:
                registration = PGExamRegistration.objects.get(
                    uid=registration_uid, student=student
                )
            except PGExamRegistration.DoesNotExist:
                return Response(
                    {'error': 'Registration not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            registration = (
                PGExamRegistration.objects
                .filter(student=student)
                .order_by('-sem', '-created_at')
                .first()
            )
            if not registration:
                return Response(
                    {'error': 'No exam registration found for this student.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # ── 3. Verify payment success ─────────────────────────────────────────
        if registration.status != 'REGISTERED':
            payment_success = PGExamRegistrationPayment.objects.filter(
                registration=registration,
                payment_status='SUCCESS'
            ).exists()

            if not payment_success:
                latest_status = (
                    registration.payments.order_by('-created_at')
                    .values_list('payment_status', flat=True)
                    .first()
                ) or 'NO_PAYMENT'
                return Response(
                    {
                        'error': (
                            'Payment not completed. Please complete your fee '
                            'payment before uploading documents.'
                        ),
                        'payment_status': latest_status,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ── 4. Apply uploads / field updates ──────────────────────────────────
        updated_fields = []

        profile_image = request.FILES.get('profile_image')
        if profile_image:
            student.profile_image = profile_image
            updated_fields.append('profile_image')

        signature = request.FILES.get('signature')
        if signature:
            student.signature = signature
            updated_fields.append('signature')

        gender = request.data.get('gender')
        VALID_GENDERS = {'Male', 'Female', 'Other'}
        if gender:
            if gender not in VALID_GENDERS:
                return Response(
                    {'error': f"Invalid gender. Must be one of: {', '.join(sorted(VALID_GENDERS))}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            student.gender = gender
            updated_fields.append('gender')

        religion = request.data.get('religion')
        if religion:
            student.religion = religion
            updated_fields.append('religion')

        nationality = request.data.get('nationality')
        if nationality:
            student.nationality = nationality
            updated_fields.append('nationality')

        caste = request.data.get('caste')
        if caste:
            student.caste = caste
            updated_fields.append('caste')

        # ── 5. Handle PGExamRegistration uploads / updates ────────────────────
        reg_updated_fields = []
        
        # New Field: Admission Receipt
        admission_receipt = request.FILES.get('admission_receipt')
        if admission_receipt:
            registration.admission_receipt = admission_receipt
            reg_updated_fields.append('admission_receipt')

        if not updated_fields and not reg_updated_fields:
            return Response(
                {
                    'error': (
                        'No fields provided. Send at least one of: '
                        'profile_image, signature, gender, admission_receipt, religion, nationality, caste.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if updated_fields:
            student.save(update_fields=updated_fields)
            logger.info(
                f"PG student {student.registration_no} updated fields: {updated_fields}"
            )

        # ── 6. Mark registration as REGISTERED (if needed) & Save Registration ──
        if registration.status != 'REGISTERED':
            registration.status = 'REGISTERED'
            reg_updated_fields.append('status')
            logger.info(
                f"PGExamRegistration uid={registration.uid} marked REGISTERED "
                f"for student {student.registration_no}"
            )
        
        if reg_updated_fields:
            registration.save(update_fields=reg_updated_fields)

        return Response(
            {'message': 'Success'},
            status=status.HTTP_200_OK
        )


class PGRegistrationStatusView(APIView):
    """
    GET /api/pg/<uuid:uid>/status/

    Public endpoint (no auth required) that returns the status of a
    PGExamRegistration and its latest payment — used by the frontend
    after a CC Avenue redirect to show the student their outcome.

    Path param:
      uid  —  PGExamRegistration.uid  (UUID)
    """

    permission_classes = []

    def get(self, request, uid):
        from .models import PGExamRegistration
        from .serializers import PGExamRegistrationSerializer

        # ── Fetch registration ─────────────────────────────────────────────
        try:
            registration = (
                PGExamRegistration.objects
                .select_related('student', 'student__department', 'student__college')
                .get(uid=uid)
            )
        except (PGExamRegistration.DoesNotExist, ValueError):
            return Response(
                {'error': 'Registration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Latest payment ─────────────────────────────────────────────────
        latest_payment = registration.payments.order_by('-created_at').first()
        payment_data = None
        if latest_payment:
            payment_data = {
                'order_id':       latest_payment.order_id,
                'payment_status': latest_payment.payment_status,
                'amount':         str(latest_payment.amount),
                'payment_mode':   latest_payment.payment_mode,
                'tracking_id':    latest_payment.tracking_id,
                'bank_ref_no':    latest_payment.bank_ref_no,
                'created_at':     latest_payment.created_at,
            }

        # ── Build response ─────────────────────────────────────────────────
        registration_data = PGExamRegistrationSerializer(registration).data
        registration_data['payment_details']        = payment_data
        registration_data['latest_payment_status']  = (
            latest_payment.payment_status if latest_payment else None
        )

        return Response(registration_data, status=status.HTTP_200_OK)
