from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.conf import settings
import os

from .models import PGOldResult, PGOldStudentProfile, PGExamMasterDump
from .serializers import (
    PGOldResultSerializer, StudentInfoSerializer, SubjectDetailSerializer, 
    PGOldStudentProfileSerializer, PGExamMasterDumpSerializer
)

from .services.result_calculator import (
    calculate_pg_result, 
    get_pg_old_result_for_pdf,
    recalculate_pgo_sgpa
)
from .services.pdf_generator import generate_marksheet_pdf as generate_pdf, PGMarksheetPDFGenerator
from django.db.models import Count


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
                # Find student profile first, then get results
                student_profile = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
                if student_profile:
                    all_results = PGOldResult.objects.filter(student_profile=student_profile)
                else:
                    all_results = PGOldResult.objects.none()
                search_type = 'roll_no'
                search_value = roll_no
            else:
                # Find student profile first, then get results
                student_profile = PGOldStudentProfile.objects.filter(registration_no=reg_no).first()
                if student_profile:
                    all_results = PGOldResult.objects.filter(student_profile=student_profile)
                else:
                    all_results = PGOldResult.objects.none()
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
            
            # Get unique semester+session combinations for the current filtered results
            # We use both to distinguish different exam appearances (e.g. backlogs)
            exam_groups = list(results.values('semester_code', 'session_code').distinct().order_by('semester_code', 'session_code'))
            
            response_data = {
                'success': True,
                'student_info': student_info,
                'academic_summary': academic_summary,
                'sessions': [] # Keeping name 'sessions' for compatibility, but each is a Sem+Sess group
            }

            # Process each exam group separately
            for group in exam_groups:
                semester = group['semester_code']
                session = group['session_code']
                session_results = results.filter(semester_code=semester, session_code=session)
                
                # Fetch exam master details for THIS specific semester and session
                # Use batch_code from the results in this group
                current_batch = session_results.first().batch_code if session_results.exists() else student_info.get('batch_code')
                
                exam_master = PGExamMasterDump.objects.filter(
                    batch_code=current_batch,
                    semester_code=semester,
                    session_code=session
                ).first()
                
                exam_details = PGExamMasterDumpSerializer(exam_master).data if exam_master else None

                
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
                    'semester_code': semester,
                    'session_code': session,
                    'exam_details': exam_details,
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
                'total_groups': len(exam_groups),

                'filters_applied': {
                    'batch_code': batch_code,
                    'semester_code': semester_code,
                    'session_code': session_code
                },
                'search_type': search_type,
                'search_value': search_value
            })
            
            # Global exam details (optional legacy support)
            response_data['exam_details'] = response_data['sessions'][0]['exam_details'] if response_data['sessions'] else None


            
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
            # Try to get profile UID from 'profile_uid' or 'uid'
            profile_uid = request.data.get('profile_uid') or request.data.get('uid')
            profile = None
            response_data = []
            
            # --- PHASE 1: Identify or Create Profile ---
            if profile_uid:
                try:
                    profile = PGOldStudentProfile.objects.get(uid=profile_uid)
                except PGOldStudentProfile.DoesNotExist:
                    return Response({'success': False, 'error': f'Profile {profile_uid} not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                reg_no = request.data.get('registration_no') or request.data.get('college_reg_no')
                roll_no = request.data.get('roll_no')
                if not (reg_no or roll_no):
                    return Response({'success': False, 'error': 'Either registration_no or roll_no is required'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Update or create profile
                student_data = {
                    'registration_no': reg_no,
                    'roll_no': roll_no,
                    'student_name': request.data.get('student_name'),
                    'fathers_name': request.data.get('fathers_name'),
                    'mothers_name': request.data.get('mothers_name'),
                    'student_name_hindi': request.data.get('student_name_hindi'),
                }
                
                lookup = {'registration_no': reg_no} if reg_no else {'roll_no': roll_no}
                profile, _ = PGOldStudentProfile.objects.update_or_create(**lookup, defaults={k: v for k, v in student_data.items() if v is not None})

            # --- PHASE 2: Update Profile Fields (if provided) ---
            profile_fields = ['student_name', 'fathers_name', 'mothers_name', 'student_name_hindi', 'final_result', 'gpa', 'cgpa', 'total_percentage']
            
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
                    if not instance:
                        return {'success': False, 'error': f'Assessment with UID {uid} not found'}
                
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
            
            # --- PHASE 5: Handle Exam Master Data ---
            exam_master_data = request.data.get('exam_master_data')
            if exam_master_data:
                exam_uid = exam_master_data.get('uid') or exam_master_data.get('exam_uid')
                exam_code = exam_master_data.get('exam_code')
                
                exam_instance = None
                if exam_uid:
                    exam_instance = PGExamMasterDump.objects.filter(uid=exam_uid).first()
                elif exam_code:
                    exam_instance = PGExamMasterDump.objects.filter(exam_code=exam_code).first()

                if exam_instance:
                    exam_serializer = PGExamMasterDumpSerializer(exam_instance, data=exam_master_data, partial=True)
                    action = "updated"
                elif not exam_uid: # Create only if no UID provided (since UID record must exist)
                    exam_serializer = PGExamMasterDumpSerializer(data=exam_master_data)
                    action = "created"
                else:
                    exam_serializer = None
                    response_data.append({
                        'success': False,
                        'type': 'exam_master',
                        'error': f'Exam with UID {exam_uid} not found'
                    })
                
                if exam_serializer:
                    if exam_serializer.is_valid():
                        exam_instance = exam_serializer.save()
                        response_data.append({
                            'success': True,
                            'type': 'exam_master',
                            'action': action,
                            'data': exam_serializer.data
                        })
                    else:
                        response_data.append({
                            'success': False,
                            'type': 'exam_master',
                            'errors': exam_serializer.errors
                        })

            # --- PHASE 7: Recalculate SGPA/Totals ---
            try:
                # Use registration_no/semester/session from current context
                current_reg_no = profile.registration_no
                # We need sem/sess for recalculation. If not in request, try to get from first result
                first_res = PGOldResult.objects.filter(student_profile=profile).first()
                current_sem = request.data.get('semester_code') or request.data.get('semester') or (first_res.semester_code if first_res else None)
                current_sess = request.data.get('session_code') or request.data.get('session') or (first_res.session_code if first_res else None)
                
                if current_reg_no and current_sem and current_sess:
                    recalculate_pgo_sgpa(current_reg_no, current_sem, current_sess)
            except Exception as e:
                print(f"Recalculation error: {e}")

            # --- PHASE 8: Complete ---
            return Response({
                'success': True,
                'message': 'Data updated successfully and results recalculated.',
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
            # Find student profile first, then get results
            student_profile = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
            if student_profile:
                query = query.filter(student_profile=student_profile)
            else:
                query = query.none()
        else:
            # Find student profile first, then get results
            student_profile = PGOldStudentProfile.objects.filter(registration_no=reg_no).first()
            if student_profile:
                query = query.filter(student_profile=student_profile)
            else:
                query = query.none()
            
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



class PGoldprofilecount(APIView):
    permission_classes = []
    def get(self, request):
        try:
            profile_count = PGOldStudentProfile.objects.count()
            result_count=PGOldResult.objects.count()
            batch_wise = (
                PGOldStudentProfile.objects
                .values('batch_code')
                .annotate(count=Count('id'))
                .order_by('batch_code')
            )
            result_batch_wise = (
                PGOldResult.objects
                .exclude(batch_code__isnull=True)  # field name check karo
                .values('batch_code')
                .annotate(count=Count('id'))
                .order_by('batch_code')
            )

            return Response({
                'profile_count': profile_count,
                'result_count': result_count,
                'batch_wise': batch_wise,
                'result_batch_wise': result_batch_wise,
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)