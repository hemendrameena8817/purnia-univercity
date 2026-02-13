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
        if batch_name:
            filters['batch__name'] = batch_name
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




class PGFillDataView(APIView):
    """
    API View to get 'fill data' (json_data) for a specific assessment.
    
    URL: /api/pg/fill-data/<uid>/
    Method: GET
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, uid):
        # 1. Fetch the assessment
        try:
            assessment = PGStudentCourseAssessment.objects.get(uid=uid)
        except PGStudentCourseAssessment.DoesNotExist:
            return Response({
                "error": "Assessment not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # 2. Check permissions (Optional but recommended)
        # If the user is a college user, ensure the student belongs to their college
        if request.user.user_type == 'college_user':
            try:
                college_profile = request.user.college_profile
                user_college = college_profile.college
                if assessment.student.college != user_college:
                     return Response({
                        "error": "Access denied. Student does not belong to your college."
                    }, status=status.HTTP_403_FORBIDDEN)
            except AttributeError:
                 return Response({
                    "error": "College profile not found."
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Return the json_data
        return Response({
            "uid": assessment.uid,
            "json_data": assessment.json_data
        }, status=status.HTTP_200_OK)

class PGFillDataLookupView(APIView):
    """
    API View to get 'fill data' (json_data) by Student UID and Subject UID.
    
    URL: /api/pg/fill-data/lookup/?student=<uid>&subject=<uid>
    Method: GET
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student_uid = request.query_params.get('student')
        subject_uid = request.query_params.get('subject')

        if not student_uid or not subject_uid:
            return Response({
                "error": "Both 'student' and 'subject' query parameters are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 1. Fetch Subject to get the paper code
        from .models import PGCourseStructure
        try:
            subject = PGCourseStructure.objects.get(uid=subject_uid)
            target_code = subject.code
            if not target_code:
                 return Response({
                    "error": "The selected subject does not have a valid code."
                }, status=status.HTTP_400_BAD_REQUEST)
        except PGCourseStructure.DoesNotExist:
            return Response({
                "error": "Subject not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # 2. Fetch Assessment matching Student and Subject Code
        try:
            # We filter by student and paper_code (or course_code which seems to be used interchangeably)
            # Taking the most recent one if multiple exist (though ideally unique per semester/session)
            assessment = PGStudentCourseAssessment.objects.filter(
                student__uid=student_uid,
                paper_code=target_code,
                semester=subject.semester # Ensure semester matches
            ).order_by('-created_at').first()

            if not assessment:
                 return Response({
                    "error": "No assessment found for this student and subject."
                }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
             return Response({
                "error": f"Error finding assessment: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Check permissions
        if request.user.user_type == 'college_user':
            try:
                college_profile = request.user.college_profile
                user_college = college_profile.college
                if assessment.student.college != user_college:
                     return Response({
                        "error": "Access denied. Student does not belong to your college."
                    }, status=status.HTTP_403_FORBIDDEN)
            except AttributeError:
                 return Response({
                    "error": "College profile not found."
                }, status=status.HTTP_400_BAD_REQUEST)

        # 4. Return Data
        return Response({
            "uid": assessment.uid,
            "json_data": assessment.json_data
        }, status=status.HTTP_200_OK)
