from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.conf import settings
import os

from .models import PGOldResult, PGOldStudentProfile
from .serializers import PGOldResultSerializer, StudentInfoSerializer, SubjectDetailSerializer, PGOldStudentProfileSerializer
from .services.result_calculator import (
    calculate_pg_result, 
    get_pg_old_result_for_pdf,
    recalculate_pgo_sgpa
)
from .services.pdf_generator import generate_marksheet_pdf as generate_pdf, PGMarksheetPDFGenerator


class PGOldResultAPIView(APIView):
    """
    API view to get and create PG old results by roll number or registration number
    """
    permission_classes = []
    
    
    def get(self, request):
        """
        Get PG old result by roll_no or reg_no parameter
        Query parameters:
        - roll_no: College roll number
        - reg_no: College registration number
        - batch_code: Batch code filter (optional)
        - semester_code: Semester code filter (optional)
        - session_code: Session code filter (optional)
        """
        from rest_framework import status
        roll_no = request.GET.get('roll_no')
        reg_no = request.GET.get('reg_no')
        batch_code = request.GET.get('batch_code')
        semester_code = request.GET.get('semester_code')
        session_code = request.GET.get('session_code')
        
        if not roll_no and not reg_no:
            return Response(
                {'error': 'Either roll_no or reg_no parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if roll_no:
                all_results = PGOldResult.objects.filter(college_roll_no=roll_no)
                search_type = 'roll_no'
                search_value = roll_no
            else:
                all_results = PGOldResult.objects.filter(college_reg_no=reg_no)
                search_type = 'reg_no'
                search_value = reg_no
            
            if not all_results.exists():
                return Response(
                    {'error': f'No results found for {search_type}: {search_value}'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Apply filters for the detailed results
            results = all_results
            if batch_code:
                results = results.filter(batch_code=batch_code)
            if semester_code:
                results = results.filter(semester_code=semester_code)
            if session_code:
                results = results.filter(session_code=session_code)
            
            # Get academic summary for the FILTERED results (as requested by user)
            academic_summary = []
            distinct_filtered = results.values('semester_code', 'session_code').distinct().order_by('semester_code', 'session_code')
            for item in distinct_filtered:
                academic_summary.append({
                    'semester_code': item['semester_code'],
                    'session_code': item['session_code']
                })
            
            if not results.exists():
                # Get student info for the academic summary response even if filtered results are empty
                student_profile = None
                if roll_no:
                    student_profile = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
                elif reg_no:
                    student_profile = PGOldStudentProfile.objects.filter(registration_no=reg_no).first()
                
                student_info = None
                if student_profile:
                    student_info = PGOldStudentProfileSerializer(student_profile).data
                else:
                    first_result = all_results.first()
                    student_info = StudentInfoSerializer(first_result).data

                return Response({
                    'success': True,
                    'student_info': student_info,
                    'academic_summary': academic_summary,
                    'sessions': [],
                    'message': 'No results found for the applied filters.'
                })
            
            # Get unique student info from profile first
            student_profile = None
            student_info = None
            
            # Try to get student profile first
            if roll_no:
                student_profile = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
            elif reg_no:
                student_profile = PGOldStudentProfile.objects.filter(registration_no=reg_no).first()
            
            if student_profile:
                # Use profile data if available
                student_info = PGOldStudentProfileSerializer(student_profile).data
            else:
                # Fallback to result data if no profile
                first_result = results.first()
                student_info = StudentInfoSerializer(first_result).data
            
            # Get unique sessions as list for the current filtered results
            sessions = list(results.values_list('session_code', flat=True).distinct())
            
            response_data = {
                'success': True,
                'student_info': student_info,
                'academic_summary': academic_summary,
                'sessions': []
            }

            
            # Process each session separately
            for session in sessions:
                session_results = results.filter(session_code=session)
                
                # Separate results by exam_type for this session
                regular_results = session_results.filter(exam_type='REGULAR')
                back_results = session_results.filter(exam_type='BACK')
                
                # Further separate by status (END_TERM/MID_TERM)
                regular_end_term = SubjectDetailSerializer(regular_results.filter(status='ESE'), many=True).data
                regular_mid_term = SubjectDetailSerializer(regular_results.filter(status='CIA'), many=True).data
                back_end_term = SubjectDetailSerializer(back_results.filter(status='ESE'), many=True).data
                back_mid_term = SubjectDetailSerializer(back_results.filter(status='CIA'), many=True).data
                
                # Handle cases where status might be legacy END_TERM/MID_TERM
                if not regular_end_term:
                    regular_end_term = SubjectDetailSerializer(regular_results.filter(status='END_TERM'), many=True).data
                if not regular_mid_term:
                    regular_mid_term = SubjectDetailSerializer(regular_results.filter(status='MID_TERM'), many=True).data
                if not back_end_term:
                    back_end_term = SubjectDetailSerializer(back_results.filter(status='END_TERM'), many=True).data
                if not back_mid_term:
                    back_mid_term = SubjectDetailSerializer(back_results.filter(status='MID_TERM'), many=True).data

                session_data = {
                    'session_code': session,
                    'regular_data': {
                        'total_subjects': regular_results.count(),
                        'end_term_subjects': regular_end_term,
                        'mid_term_subjects': regular_mid_term
                    },
                    'back_data': {
                        'total_subjects': back_results.count(),
                        'end_term_subjects': back_end_term,
                        'mid_term_subjects': back_mid_term
                    },
                    'total_subjects': session_results.count()
                }
                
                response_data['sessions'].append(session_data)
            
            response_data.update({
                'total_subjects': results.count(),
                'total_sessions': len(sessions),
                'filters_applied': {
                    'batch_code': batch_code,
                    'semester_code': semester_code,
                    'session_code': session_code
                },
                'search_type': search_type,
                'search_value': search_value
            })
            
            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """
        Create new PG old result record with student profile
        Request body should contain PGOldResult data with student info
        Automatically creates/updates student profile first
        Supports UID-based profile updates
        Supports bulk assessment updates with multiple UIDs
        Supports profile + multiple assessments update in single call
        """
        try:
            profile_uid = request.data.get('profile_uid')
            profile = None
            response_data = []
            
            # --- PHASE 1: Identify or Create Profile ---
            if profile_uid:
                try:
                    profile = PGOldStudentProfile.objects.get(uid=profile_uid)
                except PGOldStudentProfile.DoesNotExist:
                    return Response({'success': False, 'error': f'Profile {profile_uid} not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                reg_no = request.data.get('college_reg_no')
                roll_no = request.data.get('college_roll_no')
                if not (reg_no or roll_no):
                    return Response({'success': False, 'error': 'Either college_reg_no or college_roll_no is required'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Update or create profile
                student_data = {
                    'registration_no': reg_no,
                    'roll_no': roll_no,
                    'student_name': request.data.get('student_name'),
                    'fathers_name': request.data.get('fathers_name'),
                    'mothers_name': request.data.get('mothers_name'),
                    'pg_faculty': request.data.get('pg_faculty'),
                    'pg_department': request.data.get('pg_department'),
                    'pg_degree': request.data.get('pg_degree'),
                    'pg_program': request.data.get('pg_program'),
                    'student_name_hindi': request.data.get('student_name_hindi'),
                }
                
                lookup = {'registration_no': reg_no} if reg_no else {'roll_no': roll_no}
                profile, _ = PGOldStudentProfile.objects.update_or_create(**lookup, defaults={k: v for k, v in student_data.items() if v is not None})

            # --- PHASE 2: Update Profile Fields (if provided) ---
            profile_fields = ['student_name', 'fathers_name', 'mothers_name', 'pg_faculty', 'pg_department', 
                            'pg_degree', 'pg_program', 'student_name_hindi', 'final_result', 'gpa', 'cgpa', 'total_percentage']
            
            profile_updated = False
            for field in profile_fields:
                if field in request.data and request.data[field] is not None:
                    setattr(profile, field, request.data[field])
                    profile_updated = True
            
            if profile_updated:
                profile.save()

            # --- PHASE 3: Handle Multiple Assessments ---
            result_uid = request.data.get('result_uid')
            result_uids = request.data.get('result_uids', [])
            assessments = request.data.get('assessments', [])  # New: Multiple assessments array
            
            # Helper to save a result
            def save_result(data, profile_inst):
                data['student_profile'] = profile_inst.id
                # Check if we should update an existing record by UID or by (student+paper+status)
                uid = data.get('uid') or data.get('result_uid')
                semester = data.get('semester_code') or data.get('semester')
                session = data.get('session_code') or data.get('session')
                paper_code = data.get('paper_code')
                status_val = data.get('status')
                
                # Auto-detect status if not provided
                if not status_val:
                    # Try to detect from exam_type or default to ESE
                    exam_type = data.get('exam_type', '').upper()
                    if exam_type in ('MID_TERM', 'CIA', 'MID', 'INTERNAL'):
                        status_val = 'CIA'
                    else:
                        status_val = 'ESE'  # Default to ESE
                
                # Normalize status for lookup
                norm_status = status_val
                if status_val:
                    stat_upper = status_val.strip().upper()
                    if stat_upper in ('MID_TERM', 'CIA', 'MID', 'INTERNAL'):
                        norm_status = 'CIA'
                    elif stat_upper in ('END_TERM', 'ESE', 'END', 'EXTERNAL'):
                        norm_status = 'ESE'
                data['status'] = norm_status # Save with normalized status
                
                instance = None
                
                # Priority 1: Update by UID
                if uid:
                    instance = PGOldResult.objects.filter(uid=uid).first()
                
                # Priority 2: Update by student+paper+semester+status (most common case)
                elif paper_code and semester and norm_status:
                    # Look for existing record for same paper/semester/status
                    # Expand search to include legacy status names for compatibility
                    status_targets = [norm_status]
                    if norm_status == 'CIA':
                        status_targets.extend(['MID_TERM', 'MID', 'INTERNAL'])
                    elif norm_status == 'ESE':
                        status_targets.extend(['END_TERM', 'END', 'EXTERNAL'])
                    
                    lookup = {
                        'student_profile': profile_inst,
                        'paper_code': paper_code,
                        'semester_code': semester,
                        'status__in': status_targets
                    }
                    if session:
                        lookup['session_code'] = session
                        
                    instance = PGOldResult.objects.filter(**lookup).first()
                
                # Priority 3: Update by student+paper only (if semester/status missing)
                elif paper_code:
                    # Look for any record with same paper for this student
                    instance = PGOldResult.objects.filter(
                        student_profile=profile_inst,
                        paper_code=paper_code
                    ).first()
                
                # Priority 4: Update by student only (if paper missing)
                else:
                    # Look for any result for this student
                    instance = PGOldResult.objects.filter(
                        student_profile=profile_inst
                    ).first()

                if instance:
                    serializer = PGOldResultSerializer(instance, data=data, partial=True)
                    action = "updated"
                else:
                    serializer = PGOldResultSerializer(data=data)
                    action = "created"
                
                if serializer.is_valid():
                    instance = serializer.save()
                    return {
                        'success': True, 
                        'data': serializer.data, 
                        'instance': instance,
                        'action': action
                    }
                return {'success': False, 'errors': serializer.errors}

            # --- PHASE 4: Process Results ---
            
            # Case 1: Single result UID
            if result_uid:
                try:
                    res_inst = PGOldResult.objects.get(uid=result_uid)
                    response_data.append(save_result(request.data.copy(), profile))
                except PGOldResult.DoesNotExist:
                    response_data.append({'success': False, 'error': f'Result {result_uid} not found'})
            
            # Case 2: Multiple result UIDs
            elif result_uids and isinstance(result_uids, list):
                for uid in result_uids:
                    request.data['result_uid'] = uid
                    response_data.append(save_result(request.data.copy(), profile))
            
            # Case 3: Multiple assessments array (NEW!)
            elif assessments and isinstance(assessments, list):
                for assessment in assessments:
                    # Merge base request data with assessment-specific data
                    merged_data = request.data.copy()
                    merged_data.update(assessment)
                    # Remove assessments array to avoid recursion
                    merged_data.pop('assessments', None)
                    response_data.append(save_result(merged_data, profile))
            
            # Case 4: Single assessment (existing behavior)
            else:
                response_data.append(save_result(request.data.copy(), profile))

            # --- PHASE 5: Complete ---
            return Response({
                'success': True,
                'message': 'Data updated successfully.',
                'results': [{k: v for k, v in r.items() if k != 'instance'} for r in response_data],
                'student_profile': PGOldStudentProfileSerializer(profile).data
            }, status=status.HTTP_200_OK if profile_uid else status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """
        Delete PG old results by UID or by query parameters (roll_no/reg_no + semester/session/paper)
        """
        result_uid = request.data.get('result_uid')
        result_uids = request.data.get('result_uids', []) or []
        
        if result_uid:
            if isinstance(result_uid, list):
                result_uids.extend(result_uid)
            else:
                result_uids.append(result_uid)
        
        if result_uids:
            # Delete by UIDs
            deleted_count, _ = PGOldResult.objects.filter(uid__in=result_uids).delete()
            return Response({
                'success': True,
                'message': f'Deleted {deleted_count} results.',
                'deleted_count': deleted_count
            })
        
        # Fallback to query parameters/filters if no UIDs provided
        roll_no = request.data.get('roll_no')
        reg_no = request.data.get('reg_no')
        semester = request.data.get('semester_code') or request.data.get('semester')
        session = request.data.get('session_code') or request.data.get('session')
        paper_code = request.data.get('paper_code')
        
        if not (roll_no or reg_no):
            return Response({
                'success': False,
                'error': 'Either result_uid(s) or roll_no/reg_no is required for deletion.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        query = PGOldResult.objects.all()
        if roll_no:
            query = query.filter(college_roll_no=roll_no)
        else:
            query = query.filter(college_reg_no=reg_no)
            
        if semester:
            query = query.filter(semester_code=semester)
        if session:
            query = query.filter(session_code=session)
        if paper_code:
            query = query.filter(paper_code=paper_code)
            
        count = query.count()
        if count == 0:
            return Response({
                'success': False,
                'error': 'No matching results found to delete.'
            }, status=status.HTTP_404_NOT_FOUND)
            
        deleted_count, _ = query.delete()
        return Response({
            'success': True,
            'message': f'Deleted {deleted_count} matching results.',
            'deleted_count': deleted_count
        })


class PGResultCalculatorView(APIView):
    """
    Calculate PG results from ESE and CIA data and generate marksheet
    """
    permission_classes = []
    
    def get(self, request):
        """
        Calculate PG result for a student
        Query parameters:
        - registration_no: Student registration number (optional)
        - roll_no: Student roll number (optional)
        - semester: Semester code (required)
        - session: Academic session (required)
        - format: Response format - 'json', 'html', or 'pdf' (default: 'json')
        """
        registration_no = request.GET.get('registration_no')
        roll_no = request.GET.get('roll_no')
        semester = request.GET.get('semester')
        session = request.GET.get('session')
        response_format = request.GET.get('format', 'pdf')
        save_to_old_result = request.GET.get('save', 'false').lower() == 'true'
        
        if not semester or not session:
            from rest_framework import status
            return Response({
                'error': 'semester and session parameters are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not registration_no and not roll_no:
            from rest_framework import status
            return Response({
                'error': 'Either registration_no or roll_no parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # First try fetching from migrated PGOldResult data
            result_data = get_pg_old_result_for_pdf(
                registration_no=registration_no,
                roll_no=roll_no,
                semester=semester,
                session=session
            )
            
            # If nothing found or fresh save requested, fallback to fresh calculation
            if 'error' in result_data or save_to_old_result:
                result_data = calculate_pg_result(
                    registration_no=registration_no,
                    roll_no=roll_no,
                    semester=semester,
                    session=session,
                    save_to_old_result=save_to_old_result
                )
            
            if 'error' in result_data:
                from rest_framework import status
                return Response(result_data, status=status.HTTP_404_NOT_FOUND)
            
            if response_format == 'pdf':
                # Generate PDF
                try:
                    pdf_bytes, filename = generate_pdf(result_data)
                    
                    # Return PDF as downloadable file
                    response = HttpResponse(pdf_bytes, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    response['Content-Length'] = len(pdf_bytes)
                    response['Access-Control-Allow-Origin'] = '*'
                    response['Access-Control-Allow-Methods'] = 'GET'
                    response['Access-Control-Allow-Headers'] = 'Content-Type'
                    
                    return response
                    
                except Exception as e:
                    from rest_framework import status
                    return Response({
                        'error': f'PDF generation failed: {str(e)}',
                        'details': 'Please ensure WeasyPrint is installed: pip install WeasyPrint'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            elif response_format == 'html':
                # Return HTML marksheet
                return self._generate_marksheet_html(result_data)
            else:
                # Return JSON response
                return Response({
                    'success': True,
                    'data': result_data
                })
                
        except Exception as e:
            from rest_framework import status
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_marksheet_html(self, result_data: dict) -> HttpResponse:
        """Generate HTML marksheet using template"""
        try:
            generator = PGMarksheetPDFGenerator()
            
            template = get_template('pgoldresult/marksheet_pdf.html')
            
            # Prepare context for template
            context = {
                'student_info': result_data.get('student_info', {}),
                'semester': result_data.get('semester', ''),
                'session': result_data.get('session', ''),
                'cia_subjects': result_data.get('cia_subjects', []),
                'ese_subjects': result_data.get('ese_subjects', []),
                'combined_results': result_data.get('combined_results', []),
                'sgpa_data': result_data.get('sgpa_data', {}),
                'semester_result': result_data.get('semester_result', {}),
                'total_subjects': result_data.get('total_subjects', 0),
                'university_logo': generator._get_university_logo_base64(),
                'controller_sign': generator._get_controller_sign_base64(),
            }
            
            html_content = template.render(context)
            
            return HttpResponse(html_content, content_type='text/html')
            
        except Exception as e:
            return HttpResponse(f"Error generating marksheet: {e}", status=500)


@api_view(['GET'])
def generate_marksheet_pdf(request):
    """
    Generate PDF marksheet - Now fully functional with WeasyPrint
    """
    registration_no = request.GET.get('registration_no')
    roll_no = request.GET.get('roll_no')
    semester = request.GET.get('semester')
    session = request.GET.get('session')
    
    if not semester or not session:
        from rest_framework import status
        return Response({
            'error': 'semester and session parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not registration_no and not roll_no:
        from rest_framework import status
        return Response({
            'error': 'Either registration_no or roll_no parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from pgoldresult.services.result_calculator import recalculate_pgo_sgpa, get_pg_old_result_for_pdf
        from pgoldresult.models import PGOldStudentProfile
        
        # 0. Ensure we have registration_no for recalculation
        calc_reg_no = registration_no
        if not calc_reg_no and roll_no:
            prof = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
            if prof:
                calc_reg_no = prof.registration_no

        if calc_reg_no:
            # 1. Trigger fresh recalculation before fetching for PDF
            recalculate_pgo_sgpa(
                registration_no=calc_reg_no,
                semester=semester,
                session=session
            )

        # 2. Fetch from PGOldResult data (now updated)
        result_data = get_pg_old_result_for_pdf(
            registration_no=registration_no,
            roll_no=roll_no,
            semester=semester,
            session=session
        )
        
        if 'error' in result_data:
            # Fallback to calculating fresh if not found in migrated data
            result_data = calculate_pg_result(
                registration_no=registration_no,
                roll_no=roll_no,
                semester=semester,
                session=session,
                save_to_old_result=False
            )
            
        if 'error' in result_data:
            from rest_framework import status
            return Response(result_data, status=status.HTTP_404_NOT_FOUND)
        
        # Generate PDF
        pdf_bytes, filename = generate_pdf(result_data)
        
        # Return PDF as downloadable file
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response
        
    except Exception as e:
        from rest_framework import status
        return Response({
            'error': f'PDF generation failed: {str(e)}',
            'details': 'Please ensure WeasyPrint is installed: pip install WeasyPrint'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PGOldStudentProfileAPIView(APIView):
    """
    API view to manage PG student profiles
    """
    permission_classes = []
    
    def get(self, request):
        """
        Get PG student profile by registration number or roll number
        Query parameters:
        - registration_no: Student registration number
        - roll_no: Student roll number
        """
        registration_no = request.GET.get('registration_no')
        roll_no = request.GET.get('roll_no')
        
        if not registration_no and not roll_no:
            return Response(
                {'error': 'Either registration_no or roll_no parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if registration_no:
                profile = get_object_or_404(PGOldStudentProfile, registration_no=registration_no)
            else:
                profile = get_object_or_404(PGOldStudentProfile, roll_no=roll_no)
            
            serializer = PGOldStudentProfileSerializer(profile)
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """
        Create new PG student profile
        Request body should contain PGOldStudentProfile data
        """
        try:
            serializer = PGOldStudentProfileSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'PG student profile created successfully',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
