"""
Dashboard Service - Business logic for student dashboards
"""
import logging
from typing import Dict, Optional
from django.core.exceptions import ObjectDoesNotExist

from ug.models import UGStudentProfile
from ug.services.semester_registration_service import SemesterRegistrationService
from pg.models import PGStudentProfile

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for fetching dashboard data based on profile type"""
    
    @classmethod
    def get_dashboard_data(cls, user, profile_type: str) -> Dict:
        """
        Get dashboard data for user based on profile type.
        
        Args:
            user: UserAccount instance
            profile_type: One of 'ug', 'pg', 'mca_sem', 'plw'
            
        Returns:
            Dict with student_info and registration data
        """
        handlers = {
            'ug': cls._get_ug_data,
            'pg': cls._get_pg_data,
            'mca_sem': cls._get_mca_data,
            'plw': cls._get_plw_data,
        }
        
        handler = handlers.get(profile_type)
        if handler:
            return handler(user)
        
        return {
            'student_info': None,
            'registration': {
                'eligible': False,
                'reason': f'{profile_type.upper()} dashboard not yet implemented',
                'registration_open': False,
            }
        }
    
    @classmethod
    def _get_ug_data(cls, user) -> Dict:
        """Get UG student dashboard data"""
        student = UGStudentProfile.objects.select_related(
            'program', 'department', 'college'
        ).get(user=user)
        
        return {
            # 'student_info': {
            #     'registration_no': student.registration_no,
            #     'roll_no': student.roll_no,
            #     'name': f"{student.first_name or ''} {student.last_name or ''}".strip(),
            #     'program': student.program.name if student.program else None,
            #     'department': student.department.name if student.department else None,
            #     'college': student.college.name if student.college else None,
            #     'batch': student.batch,
            #     'current_semester': student.current_semester,
            #     'session': student.session,
            # },
            'registration': SemesterRegistrationService.check_registration_eligibility(student)
        }
    
    @classmethod
    def _get_pg_data(cls, user) -> Dict:
        """Get PG student dashboard data"""
        student = PGStudentProfile.objects.select_related(
            'program', 'college'
        ).get(user=user)
        
        return {
            'student_info': {
                'registration_no': getattr(student, 'registration_no', None),
                'name': f"{getattr(student, 'first_name', '') or ''} {getattr(student, 'last_name', '') or ''}".strip(),
                'program': student.program.name if student.program else None,
                'college': student.college.name if student.college else None,
                'current_semester': getattr(student, 'current_semester', None),
            },
            'registration': {
                'eligible': False,
                'reason': 'PG registration service not yet implemented',
                'registration_open': False,
            }
        }
    
    @classmethod
    def _get_mca_data(cls, user) -> Dict:
        """Get MCA student dashboard data"""
        return {
            'student_info': None,
            'registration': {
                'eligible': False,
                'reason': 'MCA registration service not yet implemented',
                'registration_open': False,
            }
        }
    
    @classmethod
    def _get_plw_data(cls, user) -> Dict:
        """Get Pre-Law student dashboard data"""
        return {
            'student_info': None,
            'registration': {
                'eligible': False,
                'reason': 'Pre-Law registration service not yet implemented',
                'registration_open': False,
            }
        }
