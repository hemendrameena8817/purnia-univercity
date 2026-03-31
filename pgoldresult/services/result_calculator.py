"""
PG Result Calculator Service
Integrates with PG app to fetch ESE and CIA data and calculate results for marksheet generation
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.db.models import Q, Avg, Sum
from django.shortcuts import get_object_or_404

# Import from pg app for ESE and CIA data
from pg.models import (
    PGStudentProfile, 
    PGStudentCourseAssessment,
    PGExamResult,
    PGExamRegistration,
    PGCommonCourseStructure
)

# Import from pgoldresult app
from pgoldresult.models import PGOldResult, PGOldStudentProfile, PGExamMasterDump


class PGResultCalculator:
    """
    Service to calculate PG results by fetching ESE and CIA data from pg app
    and generating marksheet data
    """
    
    # Grading System (CBCS)
    GRADE_THRESHOLDS = [
        (91, 'O', 10, 'Outstanding'),
        (81, 'A++', 9, 'Excellent'),
        (71, 'A+', 8, 'Very Good'),
        (61, 'A', 7, 'Good'),
        (51, 'B+', 6, 'Average'),
        (41, 'B', 5, 'Satisfactory'),
        (35, 'C', 4, 'Pass'),
        (0, 'F', 0, 'Fail'),
    ]
    
    def __init__(self, registration_no: str = None, roll_no: str = None, 
                 semester: str = None, session: str = None):
        """
        Initialize result calculator
        
        Args:
            registration_no: Student registration number
            roll_no: Student roll number  
            semester: Semester code (e.g., '1ST', '2ND')
            session: Academic session (e.g., '2024-25')
        """
        self.registration_no = registration_no
        self.roll_no = roll_no
        self.semester = semester
        self.session = session
        
        # Get student
        self.student = self._get_student()
        
    def _get_student(self) -> Optional[PGStudentProfile]:
        """Get student by registration number or roll number"""
        if self.registration_no:
            try:
                return PGStudentProfile.objects.get(registration_no=self.registration_no)
            except PGStudentProfile.DoesNotExist:
                return None
        elif self.roll_no:
            try:
                return PGStudentProfile.objects.get(roll_no=self.roll_no)
            except PGStudentProfile.DoesNotExist:
                return None
        return None
    
    def calculate_result(self) -> Dict:
        """
        Calculate complete result including CIA and ESE data
        
        Returns:
            Dictionary with calculated result data
        """
        if not self.student:
            return {'error': 'Student not found in PG app. Please use migrated data instead.'}
        
        try:
            # Get CIA assessments
            cia_data = self._get_cia_assessments()
            
            # Get ESE assessments  
            ese_data = self._get_ese_assessments()
            
            # Process results
            return self._process_results(cia_data, ese_data)
            
        except Exception as e:
            return {'error': f'Error calculating result: {str(e)}'}
    
    def _process_results(self, cia_data: List[Dict], ese_data: List[Dict]) -> Dict:
        """Process CIA and ESE data and return combined results"""
        try:
            # Calculate combined results
            combined_results = self._calculate_combined_results(cia_data, ese_data)
            
            # Calculate SGPA
            sgpa_data = self._calculate_sgpa(combined_results)
            
            # Determine semester result
            semester_result = self._determine_semester_result(combined_results)
            
            return {
                'student_info': self._get_student_info(),
                'semester': self.semester,
                'session': self.session,
                'cia_subjects': cia_data,
                'ese_subjects': ese_data,
                'combined_results': combined_results,
                'sgpa_data': sgpa_data,
                'semester_result': semester_result,
                'total_subjects': len(combined_results)
            }
        except Exception as e:
            return {'error': f'Error processing results: {str(e)}'}
    
    def _get_student_info(self) -> Dict:
        """Get student information"""
        if not self.student:
            return {}
            
        return {
            'registration_no': self.student.registration_no,
            'roll_no': self.student.roll_no,
            'name': f"{self.student.first_name or ''} ",
            'fathers_name': self.student.father_name or '',
            'mothers_name': self.student.mother_name or '',
            'batch': self.student.batch or '',
            'college': self.student.college.name if self.student.college else '',
            'department': self.student.department.name if self.student.department else '',
            'program': self.student.program.name if self.student.program else '',
        }
    
    def _get_cia_assessments(self) -> List[Dict]:
        """Get CIA assessments for the student"""
        if not self.student:
            return []
            
        assessments = PGStudentCourseAssessment.objects.filter(
            student=self.student,
            semester=self.semester,
            session=self.session,
            label__icontains='CIA'
        ).order_by('paper_code')
        
        cia_data = []
        for assessment in assessments:
            grade = self._calculate_grade(assessment.ind_marks_obtained, assessment.ind_max_marks)
            cia_data.append({
                'paper_code': assessment.paper_code or '',
                'course_code': assessment.course_code or '',
                'course_name': assessment.course_name or '',
                'max_marks': assessment.ind_max_marks or 0,
                'marks_obtained': assessment.ind_marks_obtained or 0,
                'pass_marks': assessment.ind_pass_marks or 0,
                'is_absent': assessment.ind_is_absent or False,
                'grade': grade['letter_grade'],
                'grade_point': grade['grade_point'],
                'assessment_type': 'CIA',
                'credits': assessment.course_max_credits or 0
            })
        
        return cia_data
    
    def _get_ese_assessments(self) -> List[Dict]:
        """Get ESE assessments for the student"""
        if not self.student:
            return []
            
        assessments = PGStudentCourseAssessment.objects.filter(
            student=self.student,
            semester=self.semester,
            session=self.session,
            label__icontains='ESE'
        ).order_by('paper_code')
        
        ese_data = []
        for assessment in assessments:
            grade = self._calculate_grade(assessment.ind_marks_obtained, assessment.ind_max_marks)
            ese_data.append({
                'paper_code': assessment.paper_code or '',
                'course_code': assessment.course_code or '',
                'course_name': assessment.course_name or '',
                'max_marks': assessment.ind_max_marks or 0,
                'marks_obtained': assessment.ind_marks_obtained or 0,
                'pass_marks': assessment.ind_pass_marks or 0,
                'is_absent': assessment.ind_is_absent or False,
                'grade': grade['letter_grade'],
                'grade_point': grade['grade_point'],
                'assessment_type': 'ESE',
                'credits': assessment.course_max_credits or 0
            })
        
        return ese_data
    
    def _calculate_combined_results(self, cia_data: List[Dict], ese_data: List[Dict]) -> List[Dict]:
        """Combine CIA and ESE data for each subject"""
        combined = {}
        
        # Add CIA data
        for cia in cia_data:
            paper_code = cia['paper_code']
            combined[paper_code] = {
                'paper_code': paper_code,
                'course_code': cia['course_code'],
                'course_name': cia['course_name'],
                'credits': cia['credits'],
                'cia': cia,
                'ese': None
            }
        
        # Add ESE data and calculate combined
        for ese in ese_data:
            paper_code = ese['paper_code']
            if paper_code in combined:
                combined[paper_code]['ese'] = ese
            else:
                combined[paper_code] = {
                    'paper_code': paper_code,
                    'course_code': ese['course_code'],
                    'course_name': ese['course_name'],
                    'credits': ese['credits'],
                    'cia': None,
                    'ese': ese
                }
        
        # Calculate combined totals and final grade
        results = []
        for paper_code, data in combined.items():
            cia_marks = data['cia']['marks_obtained'] if data['cia'] else 0
            cia_max = data['cia']['max_marks'] if data['cia'] else 0
            ese_marks = data['ese']['marks_obtained'] if data['ese'] else 0
            ese_max = data['ese']['max_marks'] if data['ese'] else 0
            
            total_marks = cia_marks + ese_marks
            total_max = cia_max + ese_max
            
            # Calculate final grade based on combined marks
            final_grade = self._calculate_grade(total_marks, total_max)
            
            # Determine subject result
            cia_pass = data['cia']['marks_obtained'] >= data['cia']['pass_marks'] if data['cia'] else False
            ese_pass = data['ese']['marks_obtained'] >= data['ese']['pass_marks'] if data['ese'] else False
            subject_result = 'PASS' if (cia_pass and ese_pass) else 'FAIL'
            
            data.update({
                'subject_total_mark': total_marks,
                'total_max_marks': total_max,
                'final_grade': final_grade['letter_grade'],
                'final_grade_point': final_grade['grade_point'],
                'subject_result': subject_result,
                'cia_pass': cia_pass,
                'ese_pass': ese_pass
            })
            
            results.append(data)
        
        return sorted(results, key=lambda x: x['course_code'])
    
    def _calculate_grade(self, marks_obtained: float, max_marks: float) -> Dict:
        """Calculate grade and grade point from marks"""
        if max_marks == 0:
            return {'letter_grade': 'F', 'grade_point': 0, 'percentage': 0}
        
        percentage = (marks_obtained / max_marks) * 100
        
        for threshold, letter, point, description in self.GRADE_THRESHOLDS:
            if percentage >= threshold:
                return {
                    'letter_grade': letter,
                    'grade_point': point,
                    'percentage': round(percentage, 2),
                    'description': description
                }
        
        return {'letter_grade': 'F', 'grade_point': 0, 'percentage': round(percentage, 2)}
    
    def _calculate_sgpa(self, combined_results: List[Dict]) -> Dict:
        """Calculate SGPA from combined results"""
        total_credits = 0
        total_grade_points = 0
        
        for result in combined_results:
            credits = result['credits']
            grade_point = result['final_grade_point']
            
            total_credits += credits
            total_grade_points += credits * grade_point
        
        sgpa = total_grade_points / total_credits if total_credits > 0 else 0
        
        return {
            'total_credits': total_credits,
            'total_grade_points': round(total_grade_points, 2),
            'sgpa': round(sgpa, 2)
        }
    
    def _determine_semester_result(self, combined_results: List[Dict]) -> Dict:
        """Determine overall semester result"""
        total_subjects = len(combined_results)
        passed_subjects = sum(1 for result in combined_results if result['subject_result'] == 'PASS')
        failed_subjects = total_subjects - passed_subjects
        
        # Passing rule: minimum 3 subjects must be passed
        # Sem 1 (5 subjects): pass 3, fail at most 2
        # Sem 2/3 (6 subjects): pass 3, fail at most 3
        # Music dept (5 subjects all sems): pass 3, fail at most 2
        MIN_PASS_REQUIRED = 3
        if failed_subjects == 0:
            status = 'PASS'
            status_text = 'PASSED - All subjects cleared'
        elif passed_subjects >= MIN_PASS_REQUIRED:
            status = 'BACK_PAPER'
            status_text = f'BACK PAPER - {failed_subjects} subject(s) to clear'
        else:
            status = 'FAIL'
            status_text = f'FAILED - {failed_subjects} subject(s) to clear'
        
        return {
            'status': status,
            'status_text': status_text,
            'total_subjects': total_subjects,
            'passed_subjects': passed_subjects,
            'failed_subjects': failed_subjects
        }
    
    def save_to_pg_old_result(self, result_data: Dict) -> bool:
        """
        Save calculated result to PGOldResult table
        
        Args:
            result_data: Calculated result data
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not self.student or 'error' in result_data:
            return False
        
        try:
            with transaction.atomic():
                # Clear existing records for this student/semester/session
                PGOldResult.objects.filter(
                    college_reg_no=self.student.registration_no,
                    semester_code=self.semester,
                    session_code=self.session
                ).delete()
                
                # Create new records for each subject
                for subject in result_data['combined_results']:
                    PGOldResult.objects.create(
                        college_reg_no=self.student.registration_no,
                        college_roll_no=self.student.roll_no or '',
                        student_name=f"{self.student.first_name} {self.student.last_name}".strip(),
                        fathers_name=self.student.father_name or '',
                        mothers_name=self.student.mother_name or '',
                        semester_code=self.semester,
                        batch_code=self.student.batch or '',
                        session_code=self.session,
                        course_code=subject['course_code'],
                        discipline_code=subject.get('discipline_code') or '',
                        paper_code=subject['paper_code'],
                        subject_name=subject['course_name'],
                        faculty=subject.get('faculty') or '',
                        
                        # CIA marks
                        subject_ca=subject['cia']['marks_obtained'] if subject['cia'] else 0,
                        
                        # ESE marks  
                        maximum_mark=subject['ese']['max_marks'] if subject['ese'] else 0,
                        mark_secured=subject['ese']['marks_obtained'] if subject['ese'] else 0,
                        pass_mark=subject['ese']['pass_marks'] if subject['ese'] else 0,
                        
                        # Combined results
                        subject_total_mark=subject['total_marks_obtained'],
                        subject_result=subject['subject_result'],
                        
                        # Grade information
                        subject_gp=subject['final_grade_point'],
                        let_grad_sub=subject['final_grade'],
                        
                        # Status information
                        status='END_TERM' if subject['ese'] else 'MID_TERM',
                        exam_type='ESE' if subject['ese'] else 'CIA',
                        exam_type_his='End Semester Examination' if subject['ese'] else 'Continuous Internal Assessment'
                    )
                
                return True
                
        except Exception as e:
            print(f"Error saving to PGOldResult: {e}")
            return False


def calculate_pg_result(registration_no: str = None, roll_no: str = None, 
                      semester: str = None, session: str = None, 
                      save_to_old_result: bool = False) -> Dict:
    """
    Convenience function to calculate PG result
    
    Args:
        registration_no: Student registration number
        roll_no: Student roll number
        semester: Semester code
        session: Academic session
        save_to_old_result: Whether to save to PGOldResult table
        
    Returns:
        Dictionary with calculated result data
    """
    calculator = PGResultCalculator(
        registration_no=registration_no,
        roll_no=roll_no,
        semester=semester,
        session=session
    )
    
    result_data = calculator.calculate_result()
    
    if save_to_old_result and 'error' not in result_data:
        calculator.save_to_pg_old_result(result_data)
    
    return result_data


def get_pg_old_result_for_pdf(registration_no=None, roll_no=None, semester=None, session=None):
    """
    Fetch and structure PG old result data for PDF template.
    Always triggers a recalculation to ensure latest rules are applied.
    """
    from pgoldresult.models import PGOldResult, PGOldStudentProfile, PGCenterInstituteMap, PGExamMasterDump
    from django.db.models import Sum
    
    if registration_no:
        profile = PGOldStudentProfile.objects.filter(registration_no=registration_no).first()
    else:
        profile = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
    if not profile:
        return {'error': 'Student profile not found'}
        
    # 2. Gather all subjects for this student and semester with Carry-Forward Logic
    all_res = PGOldResult.objects.filter(
        student_profile=profile,
        semester_code=semester
    ).order_by('paper_code', '-maximum_mark')
    
    if not all_res.exists():
        return {'error': 'No subjects found for this result in old database'}
        
    # Carry-Forward Logic: For each paper_code, pick the best/latest session records
    papers_history = {} # paper_code -> Set[session_code]
    for r in all_res:
        code = r.paper_code
        if code not in papers_history: papers_history[code] = set()
        papers_history[code].add(r.session_code)
        
    final_result_ids = []
    for p_code, sessions_available in papers_history.items():
        if session:
            # When session is specified, only include papers that exist in that session
            if session in sessions_available:
                target_p_session = session
            else:
                continue  # Skip papers not in the requested session
        else:
            # No session filter: carry-forward from latest session
            target_p_session = sorted(list(sessions_available), reverse=True)[0]
        
        # Add IDs of records for this paper from the selected session
        p_ids = list(all_res.filter(paper_code=p_code, session_code=target_p_session).values_list('id', flat=True))
        final_result_ids.extend(p_ids)
        
    results = PGOldResult.objects.filter(id__in=final_result_ids).order_by('paper_code', '-maximum_mark')

    # Determine the effective session from the actually selected records, then recalculate
    effective_session = results.first().session_code if results.exists() else session
    effective_reg_no = registration_no or (profile.registration_no if profile else None)
    if effective_reg_no and semester and effective_session:
        try: recalculate_pgo_sgpa(effective_reg_no, semester, effective_session)
        except: pass
        
    grouped_subjects = {}
    
    for r in results:
        paper_code = r.paper_code or ''
        
        if paper_code not in grouped_subjects:
            grouped_subjects[paper_code] = {
                'paper_code': paper_code,
                'course_code': r.course_code or '',
                'course_name': r.subject_name or '',
                'ese': {'max_marks': 0, 'marks_obtained': '--', 'pass_marks': 0},
                'cia': {'max_marks': 0, 'marks_obtained': '--', 'pass_marks': 0},
                'final_grade': r.let_grad_sub or r.grade or '',
                'grade_point': 0, 
                'total_gp': 0,
                'credits': 5,
                'total_max_marks': 100,
                'subject_total_mark': 0,
                'subject_result': r.subject_result or ''
            }
            
        subject = grouped_subjects[paper_code]
        
        try:
            max_marks = float(r.maximum_mark) if r.maximum_mark else 0
            # Support 'AB' string for absent
            obtained_str = r.mark_secured.strip().upper() if r.mark_secured else '0'
            obtained = obtained_str if obtained_str in ('AB', 'ABSENT') else float(obtained_str)
            pass_mrk = float(r.pass_mark) if r.pass_mark else 0
        except ValueError:
            obtained = r.mark_secured if r.mark_secured else '--'
        except Exception:
            obtained = 0
            
        try:
            max_marks = float(r.maximum_mark) if r.maximum_mark else 0
        except ValueError:
            max_marks = 0

        # Format obtained elegantly so '0' doesn't become falsy in templates, and 'AB' stays intact
        if isinstance(obtained, float):
            obtained_fmt = str(int(obtained)) if obtained.is_integer() else str(obtained)
        else:
            obtained_fmt = str(obtained)

        # Assign to ESE vs CIA based on marks and order
        ese_dict = subject.get('ese')
        if isinstance(ese_dict, dict) and (max_marks in (70, 80) or (max_marks == 50 and ese_dict.get('max_marks', 0) == 0)):
            subject['ese'] = {
                'max_marks': max_marks,
                'marks_obtained': obtained_fmt,
                'pass_marks': pass_mrk,
            }
        else:
            subject['cia'] = {
                'max_marks': max_marks,
                'marks_obtained': obtained_fmt,
                'pass_marks': pass_mrk,
            }

        # Handle overall stats (only populate if Truthy)
        # BUG FIX: Only take credits if not already set to a non-zero value, 
        # or if the current record has a non-zero credit value. 
        # This prevents CIA (often 0 credits in some DBs) from overwriting ESE (5 credits).
        if hasattr(r, 'subject_ca') and r.subject_ca:
            try: 
                new_credits = float(r.subject_ca)
                current_credits = float(subject.get('credits', 0))
                if new_credits > 0 or current_credits == 0:
                    subject['credits'] = new_credits
            except ValueError: 
                pass
            
        if hasattr(r, 'subject_ng') and r.subject_ng:
            try: subject['grade_point'] = float(r.subject_ng)
            except ValueError: pass
            
        if hasattr(r, 'subject_gp') and r.subject_gp:
            try: subject['total_gp'] = float(r.subject_gp)
            except ValueError: pass
            
        # Dynamically calculate subject_total_mark by summing ESE and CIA
        def to_float(val):
            if not val or str(val).strip().upper() in ('AB', 'ABSENT', '--'): return 0.0
            try: return float(val)
            except (ValueError, TypeError): return 0.0

        if isinstance(subject.get('ese'), dict) and isinstance(subject.get('cia'), dict):
            ese_obj = subject['ese']
            cia_obj = subject['cia']
            ese_marks = to_float(ese_obj.get('marks_obtained'))
            cia_marks = to_float(cia_obj.get('marks_obtained'))
            total = ese_marks + cia_marks
            subject['subject_total_mark'] = total
            
            # Recalculate Grade and NG based on total (out of 100)
            percentage = total # Since full marks is 100
            if percentage >= 91: gp_val, letter = 10, 'O'
            elif percentage >= 81: gp_val, letter = 9, 'A++'
            elif percentage >= 71: gp_val, letter = 8, 'A+'
            elif percentage >= 61: gp_val, letter = 7, 'A'
            elif percentage >= 51: gp_val, letter = 6, 'B+'
            elif percentage >= 45: gp_val, letter = 5, 'B'
            elif percentage >= 40: gp_val, letter = 4, 'C'
            else: gp_val, letter = 0, 'F'
            
            # Check for absent or below pass marks (45)
            # Ensure we are checking strings correctly
            ese_ob_str = str(ese_obj.get('marks_obtained', '')).strip().upper()
            cia_ob_str = str(cia_obj.get('marks_obtained', '')).strip().upper()
            has_absent = (ese_ob_str in ('AB', 'ABSENT') or cia_ob_str in ('AB', 'ABSENT'))
            
            if has_absent or percentage < 45:
                gp_val, letter = 0, 'F'
                
            subject['final_grade'] = letter
            subject['grade_point'] = float(gp_val)
            # Ensure credits is float
            curr_credits = float(subject.get('credits', 5.0))
            subject['total_gp'] = float(gp_val) * curr_credits
            
        if hasattr(r, 'max_total_mark') and r.max_total_mark:
            try: subject['total_max_marks'] = float(r.max_total_mark)
            except ValueError: pass

    combined_results = list(grouped_subjects.values())
    total_credits = 0.0
    total_grade_points = 0.0

    # Determine how many subjects count toward GPA (last subject excluded per university rule)
    _sem_num = (semester or '').replace('ST','').replace('ND','').replace('RD','').replace('TH','').strip()
    _is_music = any(
        r for r in results
        if (r.discipline_code or '').strip().upper() in ('M04', 'M05')
        or 'MUSIC' in (r.discipline_code or '').upper()
    )
    _max_gpa_subjects = 99  # default: all
    _excl_paper_code = None  # specific paper code to exclude from GPA
    if _is_music:
        if _sem_num == '1':            _max_gpa_subjects = 5   # excl. PG106
        elif _sem_num in ('2', '3'):   _max_gpa_subjects = 4   # excl. PG205/PG305
        elif _sem_num == '4':          _excl_paper_code = 'PG405'
    else:
        if _sem_num == '1':            _max_gpa_subjects = 4   # excl. PG105
        elif _sem_num in ('2', '3'):   _max_gpa_subjects = 5   # excl. PG206/PG306
        elif _sem_num == '4':          _excl_paper_code = 'PG403'

    _sorted_results = sorted(combined_results, key=lambda x: x.get('paper_code', ''))
    for _idx, subject in enumerate(_sorted_results):
        if _idx >= _max_gpa_subjects:
            break
        # Skip specific excluded paper for Sem 4
        if _excl_paper_code and (subject.get('paper_code') or '').strip().upper() == _excl_paper_code:
            continue
        credits_val = subject.get('credits')
        if credits_val:
            try: total_credits = float(total_credits) + float(credits_val)
            except (ValueError, TypeError): pass
            
        gp_val_item = subject.get('total_gp')
        if gp_val_item:
            try: total_grade_points = float(total_grade_points) + float(gp_val_item)
            except (ValueError, TypeError): pass
    
    # SEMESTER TOTAL CREDIT ADJUSTMENT
    # Prioritize 'total_ce' from the database as requested by the user
    first_result = results.first()
    db_total_ce = getattr(first_result, 'total_ce', None)
    
    if db_total_ce and str(db_total_ce).strip():
        # Handle numeric values for calculation, but display as is if possible
        clean_val = str(db_total_ce).strip().replace('.', '', 1)
        if clean_val.isdigit():
            try: total_credits = float(db_total_ce)
            except ValueError: pass
        else:
            # If it's a string that's not purely numeric, we still want to show it in template
            # but for calculations we might need a numeric fallback
            pass
    
    # Final sanity check removed: We now respect total_ce=0 for failing students.
    
    try:
        # Prefer SGPA saved by recalculate_pgo_sgpa (correct, uses all carry-forward papers)
        db_gpa = getattr(results.first(), 'gpa', None) if results.exists() else None
        if db_gpa and str(db_gpa).strip():
            sgpa_val = float(db_gpa)
        elif float(total_credits) > 0:
            sgpa_val = float(total_grade_points) / float(total_credits)
        else:
            sgpa_val = 0.0
    except Exception:
        if float(total_credits) > 0:
            sgpa_val = float(total_grade_points) / float(total_credits)
        else:
            sgpa_val = 0.0
    
    first_result = results.first()

    # Get center name if possible
    center_name = ''
    if first_result and first_result.institute_code:
        from pgoldresult.models import PGCenterInstituteMap
        center_map = PGCenterInstituteMap.objects.filter(institute_code=first_result.institute_code).first()
        if center_map:
            center_name = center_map.center_name or ''

    # Always read final_result from the REQUESTED session's records (not effective_session which may be carry-forward)
    # This ensures session-specific marksheets show the correct PASS/FAIL status for that session
    requested_session = session  # Use the session parameter passed to this function
    current_session_result = all_res.filter(session_code=requested_session).first() if requested_session else first_result
    final_result_status = (current_session_result.final_result if current_session_result else '') or ''

    semester_result = {
        'status':  final_result_status,
        'status_text': final_result_status,
    }
    student_info = {
        'registration_no': profile.registration_no,
        'roll_no': profile.roll_no,
        'name': profile.first_name or '',
        'fathers_name': profile.fathers_name or '',
        'mothers_name': profile.mothers_name or '',
        'batch': profile.batch_code or '',
        'college': profile.college.name if profile.college else '',
        'center': center_name,
        'degree': profile.pg_degree or '',
        'faculty': profile.pg_faculty or '',
        'program': profile.pg_program or '',
        'semester': semester,
    }

    # Get exam info from PGExamMasterDump for dynamic header
    exam_info = {}

    if first_result:
        from pgoldresult.models import PGExamMasterDump
        # Match by batch + semester + session (if available) to get the exact exam
        kwargs = {
            'course_code': 'PG',
            'batch_code': first_result.batch_code,
            'semester_code': semester,
        }
        if session:
            kwargs['session_code'] = session
            
        exam_record = PGExamMasterDump.objects.filter(**kwargs).first()
        
        # If not found by batch+semester+session, fallback to session+semester
        if not exam_record and session:
            exam_record = PGExamMasterDump.objects.filter(
                course_code='PG',
                session_code=session,
                semester_code=semester,
            ).first()
        if exam_record:
            exam_info = {
                'exam_name': exam_record.exam_name or '',
                'exam_month': exam_record.exam_month or '',
                'exam_year': exam_record.exam_year or '',
                'year': exam_record.year or '',
                'exam_name_year': f"{exam_record.exam_name or ''} {exam_record.exam_year or ''}",
                'actual_exam_month': exam_record.actual_exam_month or '',
                'exam_start_date': exam_record.exam_start_date or '',
                'exam_end_date': exam_record.exam_end_date or '',
                'batch_code': exam_record.batch_code or '',
                'session_code': exam_record.session_code or '',
                'semester_code': exam_record.semester_code or '',
                "pub_date": exam_record.publish_date or '',
            }

    result_date = (
        exam_info.get('exam_start_date') or
        exam_info.get('exam_month')  
    )

    # Handle Semester 4 CGPA Data
    cgpa_data = None
    if semester == '4TH':
        cgpa_data = get_pg_cgpa_data(registration_no, roll_no)

    return {
        'student_info': student_info,
        'semester': semester,
        'session': session,
        'combined_results': combined_results,
        'sgpa_data': {
            'total_credits': total_credits if final_result_status == 'PASS' else '',
            'total_grade_points': total_grade_points if final_result_status == 'PASS' else '',
            'sgpa': round(float(sgpa_val), 2) if final_result_status == 'PASS' else '',
        },
        'semester_result': semester_result,
        'total_subjects': len(combined_results),
        'exam_info': exam_info,
        'result_date': result_date,
        'cgpa_data': cgpa_data,
    }


def get_pg_cgpa_data(registration_no=None, roll_no=None):
    """
    Fetch SGPA and Credit Earned for all 4 semesters and calculate CGPA.
    """
    from pgoldresult.models import PGOldResult, PGOldStudentProfile
    
    if registration_no:
        profile = PGOldStudentProfile.objects.filter(registration_no=registration_no).first()
    else:
        profile = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
        
    if not profile:
        return None
        
    semesters = ['1ST', '2ND', '3RD', '4TH']
    sem_data = {}
    
    total_gp = 0.0
    total_cr = 0.0
    
    for sem in semesters:
        # Get the latest result for this semester
        res = PGOldResult.objects.filter(student_profile=profile, semester_code=sem).order_by('-id').first()
        
        gpa = 0.0
        credits = 0.0
        
        if res:
            # We need to find the SGPA and Total Credits for this semester.
            # In our schema, gpa is often stored in the profile, but that's for the 'current' sem.
            # Let's try to get it from the results themselves or recalculate.
            try:
                # Get all unique papers for this semester and session
                latest_session = res.session_code
                sem_results = PGOldResult.objects.filter(
                    student_profile=profile, 
                    semester_code=sem,
                    session_code=latest_session
                )
                
                # Credits earned is stored in total_ce (calculated by recalculate_pgo_sgpa)
                try: credits = float(res.total_ce or 0)
                except: credits = 0.0
                
                # SGPA calculation: Sum(GP * Credits) / Sum(Credits)
                # But wait, we store subject_gp (which is GP * Credits already in our recalculation logic)
                gp_sum = 0.0
                cr_sum = 0.0
                
                # To be accurate, we should probably just use the stored subject_gp
                is_music = 'MUSIC' in (res.discipline_code or '').upper() or (res.discipline_code or '').strip().upper() in ('M04', 'M05')
                
                for r in sem_results:
                    try:
                        # NEW RULE: Exclude DSE-1 and GE-1 for Semester 4 (Except Music)
                        # For Music (M04), exclude PG405
                        p_code = (r.paper_code or '').strip().upper()
                        if sem == '4TH':
                            if is_music:
                                if p_code == 'PG405': continue
                            else:
                                if p_code in ('DSE-1', 'GE-1'): continue

                        gp_sum += float(r.subject_gp or 0)
                        # Derive credits from subject_ca if possible (which we use as credits)
                        try: cVal = float(r.subject_ca or 5.0)
                        except: cVal = 5.0
                        cr_sum += cVal
                    except: pass
                
                # Semester 4 Hardcoded Credits Override
                if sem == '4TH':
                    if cr_sum > 0:
                        gpa = round(gp_sum / cr_sum, 2)
                    else:
                        gpa = 0.0
                    
                    if is_music:
                        credits = 24.0
                    else:
                        credits = 10.0
                    
                    # Update cr_sum and gp_sum for CGPA consistency
                    cr_sum = credits
                    gp_sum = gpa * cr_sum
                else:
                    if cr_sum > 0:
                        gpa = round(gp_sum / cr_sum, 2)
                    else:
                        gpa = 0.0
                
                # If credits is 0 (failed students), we still want to show the GPA they earned for passed subjects?
                # Actually, the marksheet image shows the GPA even if it's 6.25, 6.4, etc.
                # If they failed a semester, the GPA might be lower or 0.
            except Exception as e:
                print(f"Error fetching CGPA data for {sem}: {e}")
        
        # Override with profile GPA if this is the 'current' semester from profile's perspective
        # Actually, let's just stick to the calculation.
        
        sem_data[sem] = {
            'gpa': gpa,
            'credits': credits or cr_sum # Fallback to sum of credits if total_ce is 0
        }
        
        total_gp += gp_sum if 'gp_sum' in locals() else 0.0
        total_cr += cr_sum if 'cr_sum' in locals() else 0.0

    cgpa = round(total_gp / total_cr, 2) if total_cr > 0 else 0.0
    
    # Grading for CGPA with description
    if cgpa >= 9.0: letter, numerical, desc = 'O', 10, 'Outstanding'
    elif cgpa >= 8.0: letter, numerical, desc = 'A++', 9, 'Excellent'
    elif cgpa >= 7.0: letter, numerical, desc = 'A+', 8, 'Very Good'
    elif cgpa >= 6.0: letter, numerical, desc = 'A', 7, 'Good'
    elif cgpa >= 5.0: letter, numerical, desc = 'B+', 6, 'Average'
    elif cgpa >= 4.5: letter, numerical, desc = 'B', 5, 'Satisfactory'
    elif cgpa >= 4.0: letter, numerical, desc = 'C', 4, 'Pass'
    else: letter, numerical, desc = 'F', 0, 'Fail'

    # Save grade description to dsc_grad field for Sem 4 records
    if profile:
        PGOldResult.objects.filter(
            student_profile=profile,
            semester_code='4TH'
        ).update(
            dsc_grad=desc,
            cgpa=str(cgpa),
            let_grad=letter,
            numrical_let_grad=str(numerical)
        )

    return {
        'sem1': sem_data['1ST'],
        'sem2': sem_data['2ND'],
        'sem3': sem_data['3RD'],
        'sem4': sem_data['4TH'],
        'cgpa': cgpa,
        'letter_grade': letter,
        'numerical_grade': numerical,
        'grade_description': desc
    }



def recalculate_pgo_sgpa(registration_no: str, semester: str, session: str) -> Dict:
    """
    Recalculate SGPA for a student from their PGOldResult records and update their PGOldStudentProfile.
    """
    from pgoldresult.models import PGOldStudentProfile, PGOldResult
    
    # 1. Fetch ALL results for this student and semester (across all sessions)
    all_res = PGOldResult.objects.filter(
        student_profile__registration_no=registration_no,
        semester_code=semester
    )
    
    if not all_res.exists():
        return {'error': 'No results found to recalculate'}
        
    results = all_res.filter(session_code=session) if session else all_res
    
    total_credits = 0.0
    total_grade_points = 0.0
    failed_subjects = int(0)
    total_subjects = int(0)
    
    # 2. Group by paper_code with Carry-Forward Logic
    # We want to pick the latest/best attempt for each subject
    # Priority: target session > latest available session
    records_by_paper = {} # paper_code -> [PGOldResult, ...]
    
    # First, collect all papers and their sessions
    papers_history = {} # paper_code -> Set[session_code]
    for r in all_res:
        code = r.paper_code
        if code not in papers_history: papers_history[code] = set()
        papers_history[code].add(r.session_code)
        
    for p_code, sessions in papers_history.items():
        # Determine which session's records to use for this paper
        if session in sessions:
            target_p_session = session
        else:
            # Pick the latest session available (alphabetical sort)
            target_p_session = sorted(list(sessions), reverse=True)[0]
            
        records_by_paper[p_code] = list(all_res.filter(paper_code=p_code, session_code=target_p_session))

    semester_total_credits = 0.0
    any_subject_failed = False

    # Detect Music department
    is_music_dept = any(
        r for r in all_res
        if (r.discipline_code or '').strip().upper() in ('M04', 'M05')
        or 'MUSIC' in (r.discipline_code or '').upper()
    )

    # Subjects that count toward GPA (last subject excluded per university rule)
    sorted_paper_codes = sorted(records_by_paper.keys())
    sem_num = semester.replace('ST', '').replace('ND', '').replace('RD', '').replace('TH', '').strip()
    max_subjects_to_sum = 99  # Default to all
    if is_music_dept:
        if sem_num == '1':   max_subjects_to_sum = 5  # excl. PG106
        elif sem_num in ('2', '3'): max_subjects_to_sum = 4  # excl. PG205/PG305
        elif sem_num == '4': max_subjects_to_sum = 5
    else:
        if sem_num == '1':   max_subjects_to_sum = 4  # excl. PG105
        elif sem_num in ('2', '3'): max_subjects_to_sum = 5  # excl. PG206/PG306
        elif sem_num == '4': max_subjects_to_sum = 5
            
    for idx, paper_code in enumerate(sorted_paper_codes):
        records = records_by_paper[paper_code]
        total_subjects = int(total_subjects) + 1
        try:
            # We pick one record as the "primary" to update, but sum marks from all
            primary_r = records[0]
            # Preference for records that already have credits/GP data if possible
            for rec in records:
                if rec.subject_ca and float(rec.subject_ca) > 0:
                    primary_r = rec
                    break
            
            # Robust credit determination
            credits = 5.0
            if primary_r.subject_ca:
                try: 
                    c_val = float(primary_r.subject_ca)
                    if c_val > 0: credits = c_val
                except ValueError: 
                    credits = 5.0
            
            if credits == 0:
                credits = 5.0
            
            # Track marks by status to avoid duplicates
            status_marks = {} # normalized_status -> mark
            has_absent = False
            total_max = 0.0
            total_secured = 0.0
            subj_component_failed = False
            cia_failed = False  # Rule: if ANY mid-term fails → subject FAIL
            
            for r in records:
                # Normalize status
                stat = (r.status or '').strip().upper()
                if stat in ('MID_TERM', 'CIA', 'MID', 'INTERNAL'):
                    norm_stat = 'CIA'
                elif stat in ('END_TERM', 'ESE', 'END', 'EXTERNAL'):
                    norm_stat = 'ESE'
                else:
                    norm_stat = stat
                
                max_m = float(r.maximum_mark) if r.maximum_mark else 0
                pass_m = float(r.pass_mark) if r.pass_mark else 0
                # Fallback: if pass_mark not set, use 45% of max as minimum
                if pass_m == 0 and max_m > 0:
                    pass_m = max_m * 0.45
                sec_m = 0
                if r.mark_secured:
                    secured_upper = r.mark_secured.strip().upper()
                    if secured_upper in ('AB', 'ABSENT', '--'):
                        sec_m = 0
                        has_absent = True
                    else:
                        try: sec_m = float(r.mark_secured)
                        except ValueError: sec_m = 0
                
                # Check component level passing
                if sec_m < pass_m:
                    subj_component_failed = True
                    if norm_stat == 'CIA':
                        cia_failed = True  # Explicit CIA fail
                
                # If we have duplicate records for same normalized status, take the latest one (higher ID)
                if norm_stat not in status_marks or r.id > status_marks[norm_stat]['id']:
                    status_marks[norm_stat] = {'sec_m': sec_m, 'max_m': max_m, 'id': r.id}
            
            for s_data in status_marks.values():
                m_max = float(s_data.get('max_m') or 0.0)
                m_sec = float(s_data.get('sec_m') or 0.0)
                total_max = float(total_max) + m_max
                total_secured = float(total_secured) + m_sec
            
            if float(total_max) > 0:
                percentage = (float(total_secured) / float(total_max)) * 100.0
                
                # Grading logic (O=10, A++=9, A+=8, A=7, B+=6, B=5, C=4, F=0)
                if percentage >= 91: gp_val, letter = 10, 'O'
                elif percentage >= 81: gp_val, letter = 9, 'A++'
                elif percentage >= 71: gp_val, letter = 8, 'A+'
                elif percentage >= 61: gp_val, letter = 7, 'A'
                elif percentage >= 51: gp_val, letter = 6, 'B+'
                elif percentage >= 45: gp_val, letter = 5, 'B'
                elif percentage >= 40: gp_val, letter = 4, 'C'
                else: gp_val, letter = 0, 'F'
                
                subj_final_status = 'PASS'
                if percentage < 45 or has_absent or subj_component_failed or cia_failed:
                    gp_val, letter = 0, 'F'
                    subj_final_status = 'FAIL'
                    any_subject_failed = True
                
                for r in records:
                    r.subject_gp = str(float(gp_val) * float(credits))
                    r.let_grad_sub = letter
                    r.subject_ng = str(gp_val)
                    r.numrical_let_grad = str(gp_val)
                    r.subject_result = subj_final_status
                    r.subject_total_mark = str(int(total_secured))
                    r.save(update_fields=['subject_gp', 'let_grad_sub', 'subject_ng', 'numrical_let_grad', 'subject_result', 'subject_total_mark'])
            
            gp = float(primary_r.subject_gp) if primary_r.subject_gp else 0.0

            # ONLY add to semester total if within the limit requested by user
            # Sem4 Music: exclude PG405 from GPA, Sem4 Non-Music: exclude PG403 from GPA
            is_excluded = False
            if sem_num == '4':
                p_code = (paper_code or '').strip().upper()
                if is_music_dept:
                    if p_code == 'PG405': is_excluded = True
                else:
                    if p_code == 'PG403': is_excluded = True

            # Credit earned exclusion for Music dept (different from GPA exclusion)
            # Music: Sem1=PG105, Sem2=PG205, Sem3=PG305, Sem4=PG405
            if is_music_dept:
                _p = (paper_code or '').strip().upper()
                _credit_excl_map = {'1': 'PG105', '2': 'PG205', '3': 'PG305', '4': 'PG405'}
                is_excluded_from_credits = (_p == _credit_excl_map.get(sem_num, ''))
            else:
                is_excluded_from_credits = is_excluded  # Same as GPA for non-music

            if idx < max_subjects_to_sum and not is_excluded:
                total_credits = float(total_credits) + float(credits)
                total_grade_points = float(total_grade_points) + float(gp)
            if idx < max_subjects_to_sum and not is_excluded_from_credits:
                semester_total_credits += credits
                
            if primary_r.subject_result and 'FAIL' in str(primary_r.subject_result).upper():
                failed_subjects = int(failed_subjects) + 1
        except Exception as e:
            print(f"Error processing paper {paper_code}: {e}")

    # 3. Save the calculated total credit to the total_ce field of all records
    # If any subject was failed, the semester total credit earned is 0
    if any_subject_failed:
        semester_total_credits = 0.0
    
    # Semester 4 Hardcoded Credits RULE
    if sem_num == '4' and semester_total_credits > 0:
        is_music = False
        sample_r = results.first()
        if sample_r and ((sample_r.discipline_code or '').strip().upper() in ('M04', 'M05') or 'MUSIC' in (sample_r.discipline_code or '').upper()):
            is_music = True
        
        if is_music:
            semester_total_credits = 24.0
        else:
            semester_total_credits = 10.0
        
    results.update(total_ce=str(int(semester_total_credits)))

    # 4. Calculate SGPA and save to gpa field
    sgpa = round(float(total_grade_points) / float(total_credits), 2) if total_credits > 0 else 0.0
    
    # NEW RULE: If any subject is failed, SGPA is 0.0
    if any_subject_failed:
        sgpa = 0.0
    
    results.update(gpa=str(sgpa))

    # 3. Determine status
    # Sem 4 special rule: Only PASS/FAIL (no PROMOTED)
    # Sem 1/2/3: minimum 3 subjects must be passed for PROMOTED
    # Sem 1 (5 subjects): pass 3, fail at most 2
    # Sem 2/3 (6 subjects): pass 3, fail at most 3
    # Music dept (5 subjects all sems): pass 3, fail at most 2
    
    if sem_num == '4':
        # Sem 4: Only PASS or FAIL (all subjects must pass)
        if failed_subjects == 0:
            status = 'PASS'
        else:
            status = 'FAIL'
    else:
        # Sem 1/2/3: PASS, PROMOTED, or FAIL
        passed_subjects = int(total_subjects) - int(failed_subjects)
        MIN_PASS_REQUIRED = 3
        if failed_subjects == 0:
            status = 'PASS'
        elif passed_subjects >= MIN_PASS_REQUIRED:
            status = 'PROMOTED'
        else:
            status = 'FAIL'
        
    # 4. Save semester status to PGOldResult.final_result for all current-session records
    results.update(final_result=status)

    # 5. Carry-forward check: if student was PROMOTED in a prior session,
    #    determine the resolved status (QUALIFIED / PARTIALLY_QUALIFIED / DISQUALIFIED)
    #    BUT: Skip if current session is a fresh attempt (all semester papers given)
    #    ALSO: Skip for Sem 4 (only PASS/FAIL allowed)
    
    # Detect if current session is a fresh attempt (not just back papers)
    # Count ONLY papers actually given in the current session (before carry-forward)
    current_session_papers = set(all_res.filter(session_code=session).values_list('paper_code', flat=True))
    current_papers_count = len(current_session_papers)
    expected_total_papers = 5 if (is_music_dept or sem_num == '1') else 6
    is_fresh_attempt = (current_papers_count >= expected_total_papers)
    
    prior_sessions = (
        PGOldResult.objects
        .filter(student_profile__registration_no=registration_no, semester_code=semester)
        .exclude(session_code=session)
        .values_list('session_code', flat=True)
        .distinct()
    )
    prior_promoted_session = None
    
    if not is_fresh_attempt and sem_num != '4':  # Only check carry-forward if NOT a fresh attempt AND NOT Sem 4
        # Find the EARLIEST (oldest) PROMOTED session to track carry-forward from
        for prior_sess in sorted(prior_sessions):
            if prior_sess < session:
                # Check if this session had failures (PROMOTED status)
                had_fails = PGOldResult.objects.filter(
                    student_profile__registration_no=registration_no,
                    semester_code=semester,
                    session_code=prior_sess,
                    subject_result__in=['F', 'FAIL']
                ).exists()
                if had_fails:
                    prior_promoted_session = prior_sess
                    break  # Take the earliest one

        if prior_promoted_session:
            carry = check_final_status(registration_no, semester, prior_promoted_session)
            if carry['total_back_papers'] > 0:
                status = carry['status']
                # Persist the resolved carry-forward status in current session records
                results.update(final_result=status)

    return {
        'success': True,
        'sgpa': sgpa,
        'total_credits': total_credits,
        'total_grade_points': total_grade_points,
        'status': status,
        'failed_subjects': failed_subjects
    }


def check_final_status(registration_no: str, semester: str, promoted_session: str) -> Dict:
    """
    When a student was PROMOTED in `promoted_session`, determine their resolved status
    based on how they performed in subsequent sessions for the same semester.

    Rules:
    - ALL back papers passed in later session  -> PASS
    - SOME back papers passed, some still fail -> PARTIALLY_QUALIFIED
    - NONE of the back papers passed           -> FAIL
    """
    from pgoldresult.models import PGOldResult

    all_results = PGOldResult.objects.filter(
        student_profile__registration_no=registration_no,
        semester_code=semester
    )

    def _is_fail(val):
        return str(val or '').strip().upper() in ('F', 'FAIL')

    def _is_pass(val):
        return str(val or '').strip().upper() in ('P', 'PASS')

    # Step 1: Identify papers the student failed in the promoted session
    # A paper is failed if ANY component (CIA/ESE) has a fail result
    failed_papers = set()
    for r in all_results.filter(session_code=promoted_session):
        if r.paper_code and _is_fail(r.subject_result):
            failed_papers.add(r.paper_code.strip().upper())

    if not failed_papers:
        return {'status': 'PASS', 'cleared': 0, 'pending': 0, 'total_back_papers': 0}

    # Step 2: Check if those papers were passed in ALL components in any later session
    later_results = all_results.exclude(session_code=promoted_session)

    cleared_papers = set()
    for paper_code in failed_papers:
        paper_records = list(later_results.filter(paper_code__iexact=paper_code))
        # Group by session: paper is cleared if ALL components pass in ANY single later session
        sessions_map = {}
        for r in paper_records:
            sessions_map.setdefault(r.session_code, []).append(r.subject_result)
        if any(all(_is_pass(v) for v in vals) for vals in sessions_map.values()):
            cleared_papers.add(paper_code)

    cleared = len(cleared_papers)
    total_back = len(failed_papers)
    pending = total_back - cleared

    if cleared == total_back:
        final_status = 'QUALIFIED'
    elif cleared == 0:
        final_status = 'DISQUALIFIED'
    else:
        final_status = 'PARTIALLY_QUALIFIED'

    return {
        'status': final_status,
        'cleared': cleared,
        'pending': pending,
        'total_back_papers': total_back,
        'failed_papers': list(failed_papers),
        'cleared_papers': list(cleared_papers),
    }