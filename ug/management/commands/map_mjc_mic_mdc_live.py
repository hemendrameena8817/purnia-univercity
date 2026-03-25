"""
Management command to map MJC, MIC, MDC departments onto LOCAL UGStudentProfile
for specific students (by registration number).

Logic (1st semester assessments only):
  - paper_code ends with 1001 → look up course_name in MJC_COURSE_MAP → set major_course
  - paper_code ends with 1002 → look up course_name in MIC_COURSE_MAP → set minor_course
  - paper_code ends with 1005 → look up course_name in MDC_COURSE_MAP → set mdc_course

Departments are matched by code on local DB where is_publish=True.

Usage:
    python manage.py map_mjc_mic_mdc_live --file /path/to/reg_nos.txt
    python manage.py map_mjc_mic_mdc_live --reg-nos 2313B100096
    python manage.py map_mjc_mic_mdc_live --file /path/to/reg_nos.txt --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

MJC_COURSE_MAP = {
    "Inorganic and Organic Chemistry": "CHEM",
    "Phycology and Microbiology": "BOT",
    "Diversity of Non-Chordates": "ZOO",
    "Introduction to Mathematical Physics & Classical Mechaincs": "PHY",
    "Physics around us": "PHY",
    "Algebra": "MATH",
    "Descriptive Statistics": "STAT",
    "Introductory Microeconomics": "ECO",
    "Principles of Economics": "RECO",
    "Introduction to Sociology - I": "SOC",
    "The Idea of Bharat": "HIST",
    "Understanding Political Theory": "POL",
    "Introduction to General Psychology": "PSY",
    "Geomorphology": "GEOG",
    "Food and Nutrition": "HSC",
    "NGO Management": "HSC",
    "Political History of India (From Indus Valley Civilization to 319 A.D)": "AIH",
    "Political History of India (From Indus Valley Civilization to 319 A.D 1206 A.D.)": "AIH",
    "Industrial Relations": "LSW",
    "An Introduction to Genral Anthropology": "ANTH",
    "Foundation of Agriculture Farm": "RECO",
    "Gandhi`s Life Journey (From Birth to 1914)": "GTV",
    "History of Hindi Literature: From Aadikaal to Reetikaal": "HIN",
    "History of Hindi Literature": "HIN",
    "हिंदी साहित्य का इतिहास": "HIN",
    "Indian Classical Literature": "ENG",
    "Indian Classical Literaure": "ENG",
    "Deductive Logic": "PHI",
    "Study of Urdu Fiction": "URD",
    "Sanskrit Vyakaran": "SNK",
    "Maithili Sahityik Aadikaal Evan Madhyakaal": "ML",
    "Maithili Sahityik Aadikaal  Evan Madhyakaal": "ML",
    "Bangla Sahityer ltihas-Prachin-o-Madhya Jug": "BEN",
    "Fundamentals of Indian Music": "MUS",
    "Applied Persian Grammar & Translation": "PER",
    "Introduction Elementary Persian Language": "PER",
    "MIL - Urdu": "URD",
    "Principles & Functions of Marketing": "Marketing",
    "Fundamentals of HRM": "HRM",
    "Fandamentals of HRM": "HRM",
    "Accounting & Finance": "AC",
}

MIC_COURSE_MAP = {
    "Food and Nutrition": "HSC",
    "Geomorphology": "GEOG",
    "The Idea of Bharat": "HIST",
    "Understanding Political Theory": "POL",
    "Introduction to General Psychology": "PSY",
    "Introductory Microeconomics": "ECO",
    "Introduction to Sociology - I": "SOC",
    "History of Hindi Literature: From Aadikaal to Reetikaal": "HIN",
    "History of Hindi Literature": "HIN",
    "Indian Classical Literature": "ENG",
    "Deductive Logic": "PHI",
    "Maithili Sahityik Aadikaal  Evan Madhyakaal": "ML",
    "Maithili Sahityik Aadikaal Evan Madhyakaal": "ML",
    "Study of Urdu Fiction": "URD",
    "Fundamentals of Indian Music": "MUS",
    "Political History of India (From Indus Valley Civilization to 319 A.D)": "AIH",
    "Political History of India (From Indus Valley Civilization to 319 A.D 1206 A.D.)": "AIH",
    "Algebra": "MATH",
    "Sanskrit Vyakaran": "SNK",
    "Industrial Relations": "LSW",
    "Applied Persian Grammar & Translation": "PER",
    "Introduction Elementary Persian Language": "PER",
    "BUILDING SCIENCE": "BEN",
    "Gandhi`s Life Journey (From Birth to 1914)": "GTV",
    "An Introduction to Genral Anthropology": "ANTH",
    "Foundation of Agriculture Farm": "RECO",
    "Diversity of Non-Chordates": "ZOO",
    "Inorganic and Organic Chemistry": "CHEM",
    "Introduction to Mathematical Physics & Classical Mechaincs": "PHY",
    "Phycology and Microbiology": "BOT",
    "Descriptive Statistics": "STAT",
    "Principles & Functions of Marketing": "Marketing",
    "Fundamentals of HRM": "HRM",
    "Fandamentals of HRM": "HRM",
    "Accounting & Finance": "AC",
}

MDC_COURSE_MAP = {
    "Fundamentals of Indian Music": "MUS",
    "Indian Classical Literaure": "ENG",
    "Indian Classical Literature": "ENG",
    "Deductive Logic": "PHI",
    "Maithili Sahityik Aadikaal Evan Madhyakaal": "ML",
    "Maithili Sahityik Aadikaal  Evan Madhyakaal": "ML",
    "हिंदी साहित्य का इतिहास": "HIN",
    "History of Hindi Literature": "HIN",
    "Introduction to General Psychology": "PSY",
    "The Idea of Bharat": "HIST",
    "NGO Management": "HSC",
    "Understanding Political Theory": "POL",
    "Geomorphology": "GEOG",
    "Introductory Microeconomics": "ECO",
    "Introduction to Sociology - I": "SOC",
    "Principles & Functions of Marketing": "Marketing",
    "Fundamentals of HRM": "HRM",
    "Fandamentals of HRM": "HRM",
    "Introduction Elementary Persian Language": "PER",
    "Inorganic and Organic Chemistry": "CHEM",
    "Diversity of Non-Chordates": "ZOO",
    "Phycology and Microbiology": "BOT",
    "Physics around us": "PHY",
    "Algebra": "MATH",
    "Bangla Sahityer ltihas-Prachin-o-Madhya Jug": "BEN",
    "Study of Urdu Fiction": "URD",
    "Sanskrit Vyakaran": "SNK",
    "MIL - Urdu": "URD",
    "Accounting & Finance": "AC",
}


class Command(BaseCommand):
    help = 'Map MJC/MIC/MDC onto LOCAL UGStudentProfile via 1st sem paper_code + course name'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--reg-nos', nargs='+', type=str)
        group.add_argument('--file', type=str)
        group.add_argument('--batch-name', type=str)
        parser.add_argument('--only-missing', action='store_true', default=False)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if options['reg_nos']:
            reg_nos = [r.strip().upper() for r in options['reg_nos'] if r.strip()]
        else:
            if options['file']:
                try:
                    with open(options['file'], 'r') as f:
                        reg_nos = [line.strip().upper() for line in f if line.strip()]
                except FileNotFoundError:
                    raise CommandError(f"File not found: {options['file']}")
            else:
                from ug.models import UGStudentProfile

                profile_qs = UGStudentProfile.objects.filter(batch__name=options['batch_name'])
                if options['only_missing']:
                    profile_qs = profile_qs.filter(
                        Q(major_course__isnull=True) |
                        Q(minor_course__isnull=True) |
                        Q(mdc_course__isnull=True)
                    )
                reg_nos = list(
                    profile_qs.exclude(registration_no__isnull=True)
                    .exclude(registration_no='')
                    .values_list('registration_no', flat=True)
                    .distinct()
                )

        if not reg_nos:
            raise CommandError("No registration numbers provided.")

        self.stdout.write(f"📋 {len(reg_nos)} registration number(s) | LOCAL DB")
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN"))

        from ug.models import UGStudentProfile, UGDepartment, StudentCourseAssessment

        # Load local published departments: code → obj
        dept_map = {
            d.code.upper(): d
            for d in UGDepartment.objects.filter(is_publish=True)
            if d.code
        }
        self.stdout.write(f"  ✓ {len(dept_map)} published departments loaded\n")

        stats = {'updated': 0, 'skipped': 0, 'errors': 0}

        for reg_no in reg_nos:
            self.stdout.write(f"── {reg_no}")
            try:
                profile = UGStudentProfile.objects.select_related(
                    'major_course', 'minor_course', 'mdc_course'
                ).get(registration_no=reg_no)
            except UGStudentProfile.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"  ✗ Not found in local DB"))
                stats['errors'] += 1
                continue

            assessments = StudentCourseAssessment.objects.filter(
                student=profile,
                semester='1ST',
            ).only('paper_code', 'course_name')

            mjc_dept = mic_dept = mdc_dept = None

            for a in assessments:
                pc = (a.paper_code or '').strip()
                cn = (a.course_name or '').strip()
                if not pc or not cn:
                    continue
                suffix = pc[-4:]

                if suffix == '1001' and mjc_dept is None:
                    code = MJC_COURSE_MAP.get(cn)
                    if code:
                        mjc_dept = dept_map.get(code.upper())

                elif suffix == '1002' and mic_dept is None:
                    code = MIC_COURSE_MAP.get(cn)
                    if code:
                        mic_dept = dept_map.get(code.upper())

                elif suffix == '1005' and mdc_dept is None:
                    code = MDC_COURSE_MAP.get(cn)
                    if code:
                        mdc_dept = dept_map.get(code.upper())

            update_fields = []
            if mjc_dept and profile.major_course_id != mjc_dept.id:
                profile.major_course = mjc_dept
                update_fields.append('major_course')
            if mic_dept and profile.minor_course_id != mic_dept.id:
                profile.minor_course = mic_dept
                update_fields.append('minor_course')
            if mdc_dept and profile.mdc_course_id != mdc_dept.id:
                profile.mdc_course = mdc_dept
                update_fields.append('mdc_course')

            if not update_fields:
                self.stdout.write(
                    f"  ⏭  No changes "
                    f"(found: MJC={mjc_dept}, MIC={mic_dept}, MDC={mdc_dept})"
                )
                stats['skipped'] += 1
                continue

            self.stdout.write(self.style.SUCCESS(
                f"  ✓ MJC={mjc_dept}  MIC={mic_dept}  MDC={mdc_dept}  [{', '.join(update_fields)}]"
            ))
            if not dry_run:
                profile.save(update_fields=update_fields)
            stats['updated'] += 1

        self.stdout.write("\n" + "═" * 50)
        self.stdout.write(f"✅ Updated: {stats['updated']}")
        self.stdout.write(f"⏭  Skipped: {stats['skipped']}")
        self.stdout.write(f"❌ Errors:  {stats['errors']}")
        self.stdout.write("═" * 50)
