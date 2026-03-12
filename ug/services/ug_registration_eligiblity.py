from django.utils import timezone
from ug.models import ExamRegistration

def check_ug_registration_eligibility(student, semester=None):
    """
    Check if a UG student is eligible for exam registration.
    Returns a dictionary with eligibility status and registration info.
    NOTE: registration_window and serialization are handled by the caller (view).
          Raw registration object is returned under '_registration' key.
    """

    # ── Semester number → text ─────────────────────────────────────────────
    SEM_NUM_TO_TEXT = {
        1: '1ST', 0: '1ST', 2: '2ND', 3: '3RD', 4: '4TH',
        5: '5TH', 6: '6TH', 7: '7TH', 8: '8TH'
    }

    # ── Get the latest exam registration for this student ──────────────────
    registrations = ExamRegistration.objects.filter(student=student)
    if semester:
        registrations = registrations.filter(sem=semester)

    registration = registrations.order_by('-sem', '-created_at').first()

    if not registration:
        return {
            'eligible': False,
            'reason': 'No exam registration record found. Please contact admin.',
            'current_semester': student.current_semester,
        }

    current_sem = registration.sem
    semester_name = SEM_NUM_TO_TEXT.get(current_sem, str(current_sem)) if current_sem else '-'

    # ── Date window check ──────────────────────────────────────────────────
    now = timezone.now()
    date_valid = True
    if registration.start_date and now < registration.start_date:
        date_valid = False
    if registration.end_date and now > registration.end_date:
        date_valid = False

    def fmt_date(dt):
        return timezone.localtime(dt).strftime('%d %b %Y, %I:%M %p') if dt else None

    registration_window = {
        'start_date': fmt_date(registration.start_date),
        'end_date': fmt_date(registration.end_date),
        'status': registration.status
    }

    # ── Already registered ─────────────────────────────────────────────────
    if registration.status == 'REGISTERED':
        return {
            'eligible': True,
            'already_registered': True,
            'current_semester': (current_sem - 1) if current_sem else None,
            'next_semester': current_sem,
            'registration_open': False,
            'exam_type': registration.exam_type,
            'session': registration.session,
            'message': f'You are already registered for Semester {semester_name}',
            'reason': f'Already registered for Semester {semester_name}',
            'registration_window': registration_window,
            '_registration': registration,
        }

    # ── Registration open & within date window ─────────────────────────────
    if registration.status == 'OPEN' and date_valid:
        return {
            'eligible': True,
            'already_registered': False,
            'current_semester': (current_sem - 1) if current_sem else None,
            'next_semester': current_sem,
            'registration_open': True,
            'exam_type': registration.exam_type,
            'session': registration.session,
            'message': f'You are eligible to register for Semester {semester_name}',
            'registration_window': registration_window,
            '_registration': registration,
        }

    # ── Registration exists but not open ───────────────────────────────────
    return {
        'eligible': True,
        'already_registered': False,
        'registration_open': False,
        'current_semester': (current_sem - 1) if current_sem else None,
        'next_semester': current_sem,
        'exam_type': registration.exam_type,
        'session': registration.session,
        'reason': f'Registration window is currently {registration.status}',
        'registration_window': registration_window,
        '_registration': registration,
    }
