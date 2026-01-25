import uuid
from django.db import models


class StagingInstituteMaster(models.Model):
    """
    Staging table for institute_master.csv data.
    All fields are nullable strings to accept raw CSV data.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # CSV columns (all nullable text fields)
    institute_id = models.CharField(max_length=255, null=True, blank=True)
    institute_code = models.CharField(max_length=255, null=True, blank=True)
    institute_name = models.CharField(max_length=500, null=True, blank=True)
    institute_type = models.CharField(max_length=255, null=True, blank=True)
    website_address = models.CharField(max_length=500, null=True, blank=True)
    contact_number = models.CharField(max_length=255, null=True, blank=True)
    institute_address = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    logo_url = models.CharField(max_length=500, null=True, blank=True)
    image_url = models.CharField(max_length=500, null=True, blank=True)
    enrollment_process = models.TextField(null=True, blank=True)
    admin_name = models.CharField(max_length=255, null=True, blank=True)
    admin_user_name = models.CharField(max_length=255, null=True, blank=True)
    affiliated_year = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_on = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    updated_on = models.CharField(max_length=255, null=True, blank=True)
    record_status = models.CharField(max_length=255, null=True, blank=True)
    last_update = models.CharField(max_length=255, null=True, blank=True)
    
    # Meta fields
    is_migrated = models.BooleanField(default=False, help_text="Has this record been migrated to College table?")
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Staging - Institute Master'
        verbose_name_plural = 'Staging - Institute Master'
        
    def __str__(self):
        return f"{self.institute_code} - {self.institute_name}"


class StagingApplicantMaster(models.Model):
    """
    Staging table for ApplicantMaster CSV data.
    All fields are nullable TextField to accept raw CSV data and avoid MySQL row size limits.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    csv_id = models.TextField(null=True, blank=True, help_text='id')
    reg_user_id = models.TextField(null=True, blank=True, help_text='reg_user_id')
    center = models.TextField(null=True, blank=True, help_text='center')
    applied_program = models.TextField(null=True, blank=True, help_text='applied_program')
    first_name = models.TextField(null=True, blank=True, help_text='first_name')
    mid_name = models.TextField(null=True, blank=True, help_text='mid_name')
    last_name = models.TextField(null=True, blank=True, help_text='last_name')
    full_name = models.TextField(null=True, blank=True, help_text='full_name')
    applied_class = models.TextField(null=True, blank=True, help_text='applied_class')
    exam_center_code = models.TextField(null=True, blank=True, help_text='exam_center_code')
    gender = models.TextField(null=True, blank=True, help_text='gender')
    nationality = models.TextField(null=True, blank=True, help_text='nationality')
    dob = models.TextField(null=True, blank=True, help_text='dob')
    dob_in_word = models.TextField(null=True, blank=True, help_text='dob_in_word')
    blood_group = models.TextField(null=True, blank=True, help_text='blood_group')
    caste = models.TextField(null=True, blank=True, help_text='caste')
    second_language = models.TextField(null=True, blank=True, help_text='second_language')
    univ_regn_no = models.TextField(null=True, blank=True, help_text='univ_regn_no')
    category = models.TextField(null=True, blank=True, help_text='category')
    is_general = models.TextField(null=True, blank=True, help_text='is_general')
    is_physically_challanged = models.TextField(null=True, blank=True, help_text='is_physically_challanged')
    instruction_mode = models.TextField(null=True, blank=True, help_text='instruction_mode')
    last_grade = models.TextField(null=True, blank=True, help_text='last_grade')
    last_board = models.TextField(null=True, blank=True, help_text='last_board')
    present_status = models.TextField(null=True, blank=True, help_text='present_status')
    employer_address = models.TextField(null=True, blank=True, help_text='employer_address')
    comm_address_ref_id = models.TextField(null=True, blank=True, help_text='comm_address_ref_id')
    perm_address_ref_id = models.TextField(null=True, blank=True, help_text='perm_address_ref_id')
    institute_code = models.TextField(null=True, blank=True, help_text='institute_code')
    created_on = models.TextField(null=True, blank=True, help_text='created_on')
    updated_by = models.TextField(null=True, blank=True, help_text='updated_by')
    updated_on = models.TextField(null=True, blank=True, help_text='updated_on')
    religion = models.TextField(null=True, blank=True, help_text='religion')
    applicant_email = models.TextField(null=True, blank=True, help_text='applicant_email')
    applicant_landline = models.TextField(null=True, blank=True, help_text='applicant_landline')
    applicant_mobile = models.TextField(null=True, blank=True, help_text='applicant_mobile')
    highest_qualification = models.TextField(null=True, blank=True, help_text='highest_qualification')
    secured_mark = models.TextField(null=True, blank=True, help_text='secured_mark')
    guardian_name = models.TextField(null=True, blank=True, help_text='guardian_name')
    marital_status = models.TextField(null=True, blank=True, help_text='marital_status')
    created_by = models.TextField(null=True, blank=True, help_text='created_by')
    record_status = models.TextField(null=True, blank=True, help_text='record_status')
    last_updated = models.TextField(null=True, blank=True, help_text='last_updated')
    discipline_code = models.TextField(null=True, blank=True, help_text='discipline_code')
    aadhar_no = models.TextField(null=True, blank=True, help_text='aadhar_no')
    medium = models.TextField(null=True, blank=True, help_text='medium')
    applied = models.TextField(null=True, blank=True, help_text='applied')
    applied_details = models.TextField(null=True, blank=True, help_text='applied_details')
    application_status = models.TextField(null=True, blank=True, help_text='application_status')
    differently_abled = models.TextField(null=True, blank=True, help_text='differently_abled')

    # Meta fields
    is_migrated = models.BooleanField(default=False, help_text="Has this record been migrated?")
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Staging - Applicant Master'
        verbose_name_plural = 'Staging - Applicant Master'
        
    def __str__(self):
        return f"{self.full_name} - {self.applied_program}"


class ApplicantRegMaster(models.Model):
    """
    Staging table for applicant_reg_master.csv data.
    All fields are nullable TextField to accept raw CSV data.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    csv_id = models.TextField(null=True, blank=True, help_text='id')
    reg_user_id = models.TextField(null=True, blank=True, help_text='reg_user_id')
    first_name = models.TextField(null=True, blank=True, help_text='first_name')
    mid_name = models.TextField(null=True, blank=True, help_text='mid_name')
    last_name = models.TextField(null=True, blank=True, help_text='last_name')
    dob = models.TextField(null=True, blank=True, help_text='dob')
    communication_flag = models.TextField(null=True, blank=True, help_text='communication_flag')
    email_id = models.TextField(null=True, blank=True, help_text='email_id')
    mobile = models.TextField(null=True, blank=True, help_text='mobile')
    pin = models.TextField(null=True, blank=True, help_text='pin')
    applied_program = models.TextField(null=True, blank=True, help_text='applied_program')
    applied_date = models.TextField(null=True, blank=True, help_text='applied_date')
    reg_mode = models.TextField(null=True, blank=True, help_text='reg_mode')
    scrutiny_status = models.TextField(null=True, blank=True, help_text='scrutiny_status')
    scrutiny_remark = models.TextField(null=True, blank=True, help_text='scrutiny_remark')
    reg_status = models.TextField(null=True, blank=True, help_text='reg_status')
    institute_code = models.TextField(null=True, blank=True, help_text='institute_code')
    created_by = models.TextField(null=True, blank=True, help_text='created_by')
    created_on = models.TextField(null=True, blank=True, help_text='created_on')
    updated_by = models.TextField(null=True, blank=True, help_text='updated_by')
    updated_on = models.TextField(null=True, blank=True, help_text='updated_on')
    status = models.TextField(null=True, blank=True, help_text='status')
    last_updated = models.TextField(null=True, blank=True, help_text='last_updated')
    dob1 = models.TextField(null=True, blank=True, help_text='dob1')
    mode = models.TextField(null=True, blank=True, help_text='mode')

    # Meta fields
    is_migrated = models.BooleanField(default=False, help_text="Has this record been migrated?")
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Applicant Reg Master'
        verbose_name_plural = 'Applicant Reg Master'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.applied_program}"


class SubjectMaster(models.Model):
    """Staging table for subject_master.csv"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    csv_id = models.TextField(null=True, blank=True, help_text='id')
    subject_code = models.TextField(null=True, blank=True, help_text='subject_code')
    subject_name = models.TextField(null=True, blank=True, help_text='subject_name')
    syllabus_code = models.TextField(null=True, blank=True, help_text='syllabus_code')
    semester_code = models.TextField(null=True, blank=True, help_text='semester_code')
    mdc_subject_name = models.TextField(null=True, blank=True, help_text='mdc_subject_name')
    institute_code = models.TextField(null=True, blank=True, help_text='institute_code')
    created_by = models.TextField(null=True, blank=True, help_text='created_by')
    created_on = models.TextField(null=True, blank=True, help_text='created_on')
    updated_by = models.TextField(null=True, blank=True, help_text='updated_by')
    updated_on = models.TextField(null=True, blank=True, help_text='updated_on')
    record_status = models.TextField(null=True, blank=True, help_text='record_status')
    last_updated = models.TextField(null=True, blank=True, help_text='last_updated')

    is_migrated = models.BooleanField(default=False)
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Subject Master'
        verbose_name_plural = 'Subject Master'
        
    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"


class PaperSubjectMapping(models.Model):
    """Staging table for paper_subject_mapping.csv"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    csv_id = models.TextField(null=True, blank=True, help_text='id')
    scdsp_code = models.TextField(null=True, blank=True, help_text='scdsp_code')
    paper_code = models.TextField(null=True, blank=True, help_text='paper_code')
    subject_code = models.TextField(null=True, blank=True, help_text='subject_code')
    discipline_code = models.TextField(null=True, blank=True, help_text='discipline_code')
    institute_code = models.TextField(null=True, blank=True, help_text='institute_code')
    status = models.TextField(null=True, blank=True, help_text='status')
    created_by = models.TextField(null=True, blank=True, help_text='created_by')
    created_on = models.TextField(null=True, blank=True, help_text='created_on')
    updated_by = models.TextField(null=True, blank=True, help_text='updated_by')
    updated_on = models.TextField(null=True, blank=True, help_text='updated_on')
    record_status = models.TextField(null=True, blank=True, help_text='record_status')
    last_updated = models.TextField(null=True, blank=True, help_text='last_updated')

    is_migrated = models.BooleanField(default=False)
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Paper Subject Mapping'
        verbose_name_plural = 'Paper Subject Mapping'
        
    def __str__(self):
        return f"{self.paper_code} - {self.subject_code}"


class DisciplineMaster(models.Model):
    """Staging table for discipline_master.csv"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    csv_id = models.TextField(null=True, blank=True, help_text='id')
    discipline_code = models.TextField(null=True, blank=True, help_text='discipline_code')
    discipline = models.TextField(null=True, blank=True, help_text='discipline')
    discipline_name = models.TextField(null=True, blank=True, help_text='discipline_name')
    discipline_name_new = models.TextField(null=True, blank=True, help_text='discipline_name_new')
    subject_name = models.TextField(null=True, blank=True, help_text='subject_name')
    institute_code = models.TextField(null=True, blank=True, help_text='institute_code')
    created_by = models.TextField(null=True, blank=True, help_text='created_by')
    created_on = models.TextField(null=True, blank=True, help_text='created_on')
    updated_by = models.TextField(null=True, blank=True, help_text='updated_by')
    updated_on = models.TextField(null=True, blank=True, help_text='updated_on')
    record_status = models.TextField(null=True, blank=True, help_text='record_status')
    last_updated = models.TextField(null=True, blank=True, help_text='last_updated')
    discipline_name_hindi = models.TextField(null=True, blank=True, help_text='discipline_name_hindi')

    is_migrated = models.BooleanField(default=False)
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Discipline Master'
        verbose_name_plural = 'Discipline Master'
        
    def __str__(self):
        return f"{self.discipline_code} - {self.discipline_name}"


class CourseDisciplineSemPaperMapping(models.Model):
    """Staging table for course_discipline_sem_paper_mapping.csv"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    csv_id = models.TextField(null=True, blank=True, help_text='id')
    scdsp_code = models.TextField(null=True, blank=True, help_text='scdsp_code')
    syllabus_code = models.TextField(null=True, blank=True, help_text='syllabus_code')
    course_code = models.TextField(null=True, blank=True, help_text='course_code')
    discipline_code = models.TextField(null=True, blank=True, help_text='discipline_code')
    semester_code = models.TextField(null=True, blank=True, help_text='semester_code')
    paper_code = models.TextField(null=True, blank=True, help_text='paper_code')
    paper_type = models.TextField(null=True, blank=True, help_text='paper_type')
    subject_type = models.TextField(null=True, blank=True, help_text='subject_type')
    paper_ge = models.TextField(null=True, blank=True, help_text='paper_ge')
    paper_credit = models.TextField(null=True, blank=True, help_text='paper_credit')
    institute_code = models.TextField(null=True, blank=True, help_text='institute_code')
    created_by = models.TextField(null=True, blank=True, help_text='created_by')
    created_on = models.TextField(null=True, blank=True, help_text='created_on')
    updated_by = models.TextField(null=True, blank=True, help_text='updated_by')
    update_on = models.TextField(null=True, blank=True, help_text='update_on')
    record_status = models.TextField(null=True, blank=True, help_text='record_status')
    last_updated = models.TextField(null=True, blank=True, help_text='last_updated')

    is_migrated = models.BooleanField(default=False)
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Course Discipline Sem Paper Mapping'
        verbose_name_plural = 'Course Discipline Sem Paper Mapping'
        
    def __str__(self):
        return f"{self.course_code} - {self.paper_code}"


class RegisteredApplicantMaster(models.Model):
    """Staging table for registered_applicant_master.csv"""
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    csv_id = models.TextField(null=True, blank=True, help_text='id')
    reg_no = models.TextField(null=True, blank=True, help_text='reg_no')
    sams_id = models.TextField(null=True, blank=True, help_text='sams_id')
    college_roll_no = models.TextField(null=True, blank=True, help_text='college_roll_no')
    college_reg_no = models.TextField(null=True, blank=True, help_text='college_reg_no')
    center = models.TextField(null=True, blank=True, help_text='center')
    center2017_old = models.TextField(null=True, blank=True, help_text='3rdcenter2017_old')
    center2017 = models.TextField(null=True, blank=True, help_text='3rdcenter2017')
    roll_no = models.TextField(null=True, blank=True, help_text='roll_no')
    result = models.TextField(null=True, blank=True, help_text='result')
    exam_type_code = models.TextField(null=True, blank=True, help_text='exam_type_code')
    student_name = models.TextField(null=True, blank=True, help_text='student_name')
    fathers_name = models.TextField(null=True, blank=True, help_text='fathers_name')
    mothers_name = models.TextField(null=True, blank=True, help_text='mothers_name')
    appl_no = models.TextField(null=True, blank=True, help_text='appl_no')
    course_code = models.TextField(null=True, blank=True, help_text='course_code')
    discipline_code = models.TextField(null=True, blank=True, help_text='discipline_code')
    semester_code = models.TextField(null=True, blank=True, help_text='semester_code')
    batch_code = models.TextField(null=True, blank=True, help_text='batch_code')
    syllabus_year = models.TextField(null=True, blank=True, help_text='syllabus_year')
    institute_code = models.TextField(null=True, blank=True, help_text='institute_code')
    session_code = models.TextField(null=True, blank=True, help_text='session_code')
    phone = models.TextField(null=True, blank=True, help_text='phone')
    dob = models.TextField(null=True, blank=True, help_text='dob')
    gender = models.TextField(null=True, blank=True, help_text='gender')
    category = models.TextField(null=True, blank=True, help_text='category')
    approve = models.TextField(null=True, blank=True, help_text='Approve')
    full_address = models.TextField(null=True, blank=True, help_text='full_address')
    institute_pub_status = models.TextField(null=True, blank=True, help_text='institute_pub_status')
    student_pub_status = models.TextField(null=True, blank=True, help_text='student_pub_status')
    last_board = models.TextField(null=True, blank=True, help_text='last_board')
    aadhar_card_no = models.TextField(null=True, blank=True, help_text='aadhar_card_no')
    created_by = models.TextField(null=True, blank=True, help_text='created_by')
    created_on = models.TextField(null=True, blank=True, help_text='created_on')
    updated_by = models.TextField(null=True, blank=True, help_text='updated_by')
    updated_on = models.TextField(null=True, blank=True, help_text='updated_on')
    record_status = models.TextField(null=True, blank=True, help_text='record_status')
    last_updated = models.TextField(null=True, blank=True, help_text='last_updated')
    payment_status = models.TextField(null=True, blank=True, help_text='payment_status')
    is_sem = models.TextField(null=True, blank=True, help_text='is_sem')
    abc_id = models.TextField(null=True, blank=True, help_text='ABC_Id')
    addmision_date = models.TextField(null=True, blank=True, help_text='Addmision_date')
    api_status = models.TextField(null=True, blank=True, help_text='api_status')

    is_migrated = models.BooleanField(default=False)
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Registered Applicant Master'
        verbose_name_plural = 'Registered Applicant Master'
        
    def __str__(self):
        return f"{self.reg_no} - {self.student_name}"

class StagingApplicantQualificationDetail(models.Model):
    """
    Staging table for ApplicantQualificationDetail XLSX data.
    All fields are nullable strings to accept raw data.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    applied_class = models.TextField(null=True, blank=True, help_text='APPLIED_CLASS')
    applied_program = models.TextField(null=True, blank=True, help_text='APPLIED_PROGRAM')
    created_by = models.TextField(null=True, blank=True, help_text='CREATED_BY')
    created_on = models.TextField(null=True, blank=True, help_text='CREATED_ON')
    division_distinction = models.TextField(null=True, blank=True, help_text='DIVISION_DISTINCTION')
    exam_code = models.TextField(null=True, blank=True, help_text='EXAM_CODE')
    full_mark = models.TextField(null=True, blank=True, help_text='FULL_MARK')
    grade = models.TextField(null=True, blank=True, help_text='GRADE')
    grade_mark_flag = models.TextField(null=True, blank=True, help_text='GRADE_MARK_FLAG')
    csv_id = models.TextField(null=True, blank=True, help_text='ID')
    institute_code = models.TextField(null=True, blank=True, help_text='INSTITUTE_CODE')
    institute_name = models.TextField(null=True, blank=True, help_text='INSTITUTE_NAME')
    last_updated = models.TextField(null=True, blank=True, help_text='LAST_UPDATED')
    mark_secured = models.TextField(null=True, blank=True, help_text='MARK_SECURED')
    math_grade = models.TextField(null=True, blank=True, help_text='MATH_GRADE')
    math_mark = models.TextField(null=True, blank=True, help_text='MATH_MARK')
    percentage_mark = models.TextField(null=True, blank=True, help_text='PERCENTAGE_MARK')
    qual_desc_1 = models.TextField(null=True, blank=True, help_text='QUAL_DESC_1')
    qual_desc_2 = models.TextField(null=True, blank=True, help_text='QUAL_DESC_2')
    reg_user_id = models.TextField(null=True, blank=True, help_text='REG_USER_ID')
    roll_no = models.TextField(null=True, blank=True, help_text='ROLL_NO')
    status = models.TextField(null=True, blank=True, help_text='STATUS')
    subjects_offered = models.TextField(null=True, blank=True, help_text='SUBJECTS_OFFERED')
    university_board = models.TextField(null=True, blank=True, help_text='UNIVERSITY_BOARD')
    updated_by = models.TextField(null=True, blank=True, help_text='UPDATED_BY')
    updated_on = models.TextField(null=True, blank=True, help_text='UPDATED_ON')
    year_of_passing = models.TextField(null=True, blank=True, help_text='YEAR_OF_PASSING')

    # Meta fields
    is_migrated = models.BooleanField(default=False, help_text="Has this record been migrated?")
    migration_notes = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Staging - ApplicantQualificationDetail'
        verbose_name_plural = 'Staging - ApplicantQualificationDetail'
        
    def __str__(self):
        return f"{self.uid}"
