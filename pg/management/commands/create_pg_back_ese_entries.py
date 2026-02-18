from django.core.management.base import BaseCommand
from pg.models import PGExamRegistration, PGStudentCourseAssessment, PGStudentProfile
# python manage.py create_pg_back_ese_entries 3 "2024-26" --dry-run
class Command(BaseCommand):
    help = 'Create blank ESE entries for PG Back students'

    def add_arguments(self, parser):
        parser.add_argument('sem', type=int, help='Semester (e.g., 3)')
        parser.add_argument('session', type=str, help='Session for Back Exam (e.g., 2024-26)')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate execution without creating database entries',
        )

    def handle(self, *args, **options):
        sem = options['sem']
        target_session = options['session']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("RUNNING IN DRY-RUN MODE. NO CHANGES WILL BE SAVED."))

        # 1. Get Back Registrations for the semester and session
        registrations = PGExamRegistration.objects.filter(
            sem=sem,
            session=target_session,
            exam_type='BACK' 
        )

        if not registrations.exists():
            self.stdout.write(self.style.WARNING(f"No BACK registrations found for Sem {sem}, Session {target_session}"))
            return

        self.stdout.write(f"Found {registrations.count()} BACK registrations.")

        for reg in registrations:
            student = reg.student
            # self.stdout.write(f"Processing student: {student.registration_no}")

            # Map sem int to string (1 -> 1ST, 2 -> 2ND, etc.) matching DB typical values
            sem_map = {1: '1ST', 2: '2ND', 3: '3RD', 4: '4TH'}
            sem_str = sem_map.get(sem, str(sem)) 
            
            # Find ALL assessments for this semester (Regular + existing Backs) to check historical status
            all_sem_assessments = PGStudentCourseAssessment.objects.filter(
                student=student,
                semester=sem_str
            )

            if not all_sem_assessments.exists():
                 # Try alternative semester formats
                suffix_map = {1: 'st', 2: 'nd', 3: 'rd', 4: 'th'}
                sem_str_alt = f"{sem}{suffix_map.get(sem, 'th')}"
                all_sem_assessments = PGStudentCourseAssessment.objects.filter(
                    student=student,
                    semester__iexact=sem_str_alt
                )
            
            # 1. Identify Passed Subjects (Paper Codes)
            # We ONLY care if they passed the ESE component if we are creating back for ESE.
            # Passing CIA does NOT mean they passed ESE.
            passed_ese_paper_codes = set()
            for assessment in all_sem_assessments:
                 # Check if passed ESE
                if 'ESE' in assessment.label.upper():
                    is_pass = False
                    if assessment.ind_is_pass:
                        is_pass = True
                    elif assessment.ind_marks_obtained is not None and assessment.ind_pass_marks is not None:
                         if assessment.ind_marks_obtained >= assessment.ind_pass_marks:
                             is_pass = True
                             
                    if is_pass:
                        passed_ese_paper_codes.add(assessment.paper_code)

            # 2. Identify Subjects that need Back Entry
            assessments_by_code = {}
            for assessment in all_sem_assessments:
                if assessment.paper_code not in assessments_by_code:
                    assessments_by_code[assessment.paper_code] = []
                assessments_by_code[assessment.paper_code].append(assessment)
            
            for paper_code, assessments in assessments_by_code.items():
                if paper_code in passed_ese_paper_codes:
                    # They already passed the ESE for this paper code in some attempt.
                    continue 
                
                # Look for an ESE assessment in the list.
                ese_assessment = None
                for assessment in assessments:
                    if 'ESE' in assessment.label.upper():
                        # We take the LATEST ESE attempt to check failure on?
                        # Or just find ANY ESE attempt?
                        # Usually latest is best to copy metadata from.
                        # Assuming iterating gives order or just take one.
                        ese_assessment = assessment
                        # Don't break immediately if we want to find specific fail?
                        # But we checked passed_ese_paper_codes above. So if they haven't passed, 
                        # any ESE record is a candidate for checking failure.
                        break 
                
                if ese_assessment:
                    # Specific check requested: "ind is pass the is false"
                    if ese_assessment.ind_is_pass is False:
                         self.create_back_entry(ese_assessment, target_session, reg.exam_type, dry_run)

    def create_back_entry(self, prev_assessment, target_session, exam_type, dry_run):
        # Check if already exists
        exists = PGStudentCourseAssessment.objects.filter(
            student=prev_assessment.student,
            semester=prev_assessment.semester,
            paper_code=prev_assessment.paper_code,
            label=prev_assessment.label,
            session=target_session,
            exam_type='BACK'
        ).exists()

        if exists:
            # self.stdout.write(f"  - Skipping {prev_assessment.course_name} (Already exists)")
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY RUN] Would create Back Entry for: {prev_assessment.student.registration_no} - {prev_assessment.course_name} ({prev_assessment.paper_code})"))
            return

        # Create new entry
        PGStudentCourseAssessment.objects.create(
            student=prev_assessment.student,
            course_name=prev_assessment.course_name,
            course_short_name=prev_assessment.course_short_name,
            course_type=prev_assessment.course_type,
            course_code=prev_assessment.course_code,
            paper_code=prev_assessment.paper_code,
            semester=prev_assessment.semester,
            label=prev_assessment.label,
            department=prev_assessment.department,
            degree=prev_assessment.degree,
            batch=prev_assessment.batch, 
            college_code=prev_assessment.college_code,
            
            session=target_session,
            exam_type='BACK',
            
            ind_max_marks=prev_assessment.ind_max_marks,
            ind_pass_marks=prev_assessment.ind_pass_marks,
            ind_marks_obtained=None, 
            ind_is_absent=False, 
            ind_is_pass=None,
            
            is_cia_fill=False,
            is_ese_fill=False,
        )
        self.stdout.write(self.style.SUCCESS(f"  + Created Back Entry: {prev_assessment.course_name}"))
