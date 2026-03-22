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
from pgoldresult.models import PGOldResult, PGOldStudentProfile


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
                'total_marks_obtained': total_marks,
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
        
        # Determine result status
        if failed_subjects == 0:
            status = 'PASS'
            status_text = 'PASSED - All subjects cleared'
        elif failed_subjects <= 2:  # Allow up to 2 back papers
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


def get_pg_old_result_for_pdf(registration_no: str, roll_no: str, semester: str, session: str) -> Dict:
    """
    Fetch data directly from PGOldResult and format it for the marksheet template.
    """
    from pgoldresult.models import PGOldStudentProfile, PGOldResult
    
    if registration_no:
        profile = PGOldStudentProfile.objects.filter(registration_no=registration_no).first()
    else:
        profile = PGOldStudentProfile.objects.filter(roll_no=roll_no).first()
    if not profile:
        return {'error': 'Student profile not found'}
        
    results = PGOldResult.objects.filter(
        student_profile=profile,
        semester_code=semester
    ).order_by('paper_code', '-maximum_mark')
    
    # Try filtering by session if exists
    if session and results.filter(session_code=session).exists():
        results = results.filter(session_code=session)
    
    if not results.exists():
        return {'error': 'No subjects found for this result in old database'}
        
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
                'total_marks_obtained': 0,
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
        if hasattr(r, 'subject_ca') and r.subject_ca:
            try: subject['credits'] = float(r.subject_ca)
            except ValueError: pass
            
        if hasattr(r, 'subject_ng') and r.subject_ng:
            try: subject['grade_point'] = float(r.subject_ng)
            except ValueError: pass
            
        if hasattr(r, 'subject_gp') and r.subject_gp:
            try: subject['total_gp'] = float(r.subject_gp)
            except ValueError: pass
            
        if hasattr(r, 'subject_total_mark') and r.subject_total_mark:
            try: subject['total_marks_obtained'] = float(r.subject_total_mark)
            except ValueError: pass
            
        if hasattr(r, 'max_total_mark') and r.max_total_mark:
            try: subject['total_max_marks'] = float(r.max_total_mark)
            except ValueError: pass

    combined_results = list(grouped_subjects.values())
    total_credits = 0.0
    total_grade_points = 0.0
    
    for subject in combined_results:
        credits_val = subject.get('credits')
        if credits_val:
            try: total_credits = float(total_credits) + float(credits_val)
            except (ValueError, TypeError): pass
            
        gp_val_item = subject.get('total_gp')
        if gp_val_item:
            try: total_grade_points = float(total_grade_points) + float(gp_val_item)
            except (ValueError, TypeError): pass
        
    try:
        cur_sgpa = getattr(profile, 'sgpa', None)
        if cur_sgpa and str(cur_sgpa).strip():
            sgpa_val = float(cur_sgpa)
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

    semester_result = {
        'status': profile.final_result or first_result.final_result or 'PASS',
        'status_text': profile.final_result or first_result.final_result or 'PASS',
    }

    student_info = {
        'registration_no': profile.registration_no,
        'roll_no': profile.roll_no,
        'name': profile.student_name or '',
        'fathers_name': profile.fathers_name or '',
        'mothers_name': profile.mothers_name or '',
        'batch': profile.batch_code or '',
        'college': profile.college.name if profile.college else '',
        'center': center_name,
        'department': profile.pg_department or '',
        'faculty': profile.pg_faculty or '',
        'program': profile.pg_program or '',
        'semester': semester,
    }

    # Get exam info from PGExamMasterDump for dynamic header
    exam_info = {}

    if first_result:
        from pgoldresult.models import PGExamMasterDump
        exam_record = PGExamMasterDump.objects.filter(
            course_code='PG',
            batch_code=first_result.batch_code,
            semester_code=semester,
        ).first()
        # If not found by batch+semester, fallback to session+semester
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
                'exam_start_date': exam_record.exam_start_date or '',
                'exam_end_date': exam_record.exam_end_date or '',
                'batch_code': exam_record.batch_code or '',
                'session_code': exam_record.session_code or '',
                'semester_code': exam_record.semester_code or '',
            }

    result_date = (
        exam_info.get('exam_start_date') or
        exam_info.get('exam_month') or
        '05-11-2023'
    )

    return {
        'student_info': student_info,
        'semester': semester,
        'session': session,
        'combined_results': combined_results,
        'sgpa_data': {
            'total_credits': total_credits,
            'total_grade_points': total_grade_points,
            'sgpa': round(float(sgpa_val), 2)
        },
        'semester_result': semester_result,
        'total_subjects': len(combined_results),
        'exam_info': exam_info,
        'result_date': result_date,
    }



def recalculate_pgo_sgpa(registration_no: str, semester: str, session: str) -> Dict:
    """
    Recalculate SGPA for a student from their PGOldResult records and update their PGOldStudentProfile.
    """
    from pgoldresult.models import PGOldStudentProfile, PGOldResult
    
    # 1. Fetch all unique results for this semester/session
    results = PGOldResult.objects.filter(
        college_reg_no=registration_no,
        semester_code=semester,
        session_code=session
    )
    
    if not results.exists():
        return {'error': 'No results found to recalculate'}
        
    total_credits = 0.0
    total_grade_points = 0.0
    failed_subjects = int(0)
    total_subjects = int(0)
    
    # 2. Group by paper_code and sum components
    paper_groups = {}
    for r in results:
        paper_code = r.paper_code
        if paper_code not in paper_groups:
            paper_groups[paper_code] = []
        paper_groups[paper_code].append(r)
            
    for paper_code, records in paper_groups.items():
        total_subjects = int(total_subjects) + 1
        try:
            # We pick one record as the "primary" to update, but sum marks from all
            primary_r = records[0]
            # Preference for records that already have credits/GP data if possible
            for rec in records:
                if rec.subject_ca and float(rec.subject_ca) > 0:
                    primary_r = rec
                    break
            
            credits = float(primary_r.subject_ca) if primary_r.subject_ca else 5.0
            
            # Track marks by status to avoid duplicates
            status_marks = {} # normalized_status -> mark
            has_absent = False
            total_max = 0.0
            total_secured = 0.0
            
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
                sec_m = 0
                if r.mark_secured:
                    secured_upper = r.mark_secured.strip().upper()
                    if secured_upper in ('AB', 'ABSENT', '--'):
                        sec_m = 0
                        has_absent = True
                    else:
                        try: sec_m = float(r.mark_secured)
                        except ValueError: sec_m = 0
                
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
                
                # FAIL overrides: if percentage below 45% OR if student was Absent in any component
                subj_final_status = 'PASS'
                if percentage < 45 or has_absent:
                    gp_val, letter = 0, 'F'
                    subj_final_status = 'FAIL'
                
                # Update all records in the group for consistency
                for r in records:
                    r.subject_gp = str(float(gp_val) * float(credits))
                    r.let_grad_sub = letter
                    r.subject_ng = str(gp_val)
                    r.numrical_let_grad = str(gp_val)
                    r.subject_result = subj_final_status
                    r.subject_total_mark = str(int(total_secured))
                    r.save(update_fields=['subject_gp', 'let_grad_sub', 'subject_ng', 'numrical_let_grad', 'subject_result', 'subject_total_mark'])
            
            gp = float(primary_r.subject_gp) if primary_r.subject_gp else 0.0
            
            total_credits = float(total_credits) + float(credits)
            total_grade_points = float(total_grade_points) + float(gp)
            
            if primary_r.subject_result and 'FAIL' in str(primary_r.subject_result).upper():
                failed_subjects = int(failed_subjects) + 1
        except (ValueError, TypeError):
            continue

    # 2. Calculate SGPA
    sgpa = round(float(total_grade_points) / float(total_credits), 2) if total_credits > 0 else 0.0
    
    # 3. Determine status
    if failed_subjects == 0:
        status = 'PASS'
    elif failed_subjects <= 2:
        status = 'PROMOTED'
    else:
        status = 'FAIL'
        
    # 4. Update Profile
    profile = PGOldStudentProfile.objects.filter(registration_no=registration_no).first()
    if profile:
        profile.gpa = str(sgpa)
        profile.final_result = status
        profile.save()
        
    return {
        'success': True,
        'sgpa': sgpa,
        'total_credits': total_credits,
        'total_grade_points': total_grade_points,
        'status': status,
        'failed_subjects': failed_subjects
    }
