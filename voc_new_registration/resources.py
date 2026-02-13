from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateTimeWidget, BooleanWidget
from .models import NewRegistration, NewRegistrationCourse, NewRegistrationBatch, NewRegistrationSession
from colleges.models import College


class NewRegistrationResource(resources.ModelResource):
    """
    Resource class for exporting NewRegistration data with all related fields.
    Supports filtering by date, course, college, and registration status.
    """
    
    # Custom fields with better formatting
    uid = fields.Field(attribute='uid', column_name='UID')
    student_name = fields.Field(attribute='student_name', column_name='Student Name')
    student_name_hindi = fields.Field(attribute='student_name_hindi', column_name='Student Name (Hindi)')
    father_name = fields.Field(attribute='father_name', column_name='Father Name')
    mother_name = fields.Field(attribute='mother_name', column_name='Mother Name')
    
    # Foreign Key fields with readable names
    course = fields.Field(
        column_name='Course',
        attribute='course',
        widget=ForeignKeyWidget(NewRegistrationCourse, 'name')
    )
    course_code = fields.Field(
        column_name='Course Code',
        attribute='course__code'
    )
    
    batch = fields.Field(
        column_name='Batch',
        attribute='batch',
        widget=ForeignKeyWidget(NewRegistrationBatch, 'name')
    )
    
    session = fields.Field(
        column_name='Session',
        attribute='session',
        widget=ForeignKeyWidget(NewRegistrationSession, 'name')
    )
    
    college = fields.Field(
        column_name='College',
        attribute='college',
        widget=ForeignKeyWidget(College, 'name')
    )
    college_code = fields.Field(
        column_name='College Code',
        attribute='college__college_code'
    )
    
    # Personal Information
    date_of_birth = fields.Field(attribute='date_of_birth', column_name='Date of Birth')
    gender = fields.Field(attribute='gender', column_name='Gender')
    caste = fields.Field(attribute='caste', column_name='Caste')
    religion = fields.Field(attribute='religion', column_name='Religion')
    nationality = fields.Field(attribute='nationality', column_name='Nationality')
    
    # Contact Information
    mobile_no = fields.Field(attribute='mobile_no', column_name='Mobile Number')
    aadhaar_no = fields.Field(attribute='aadhaar_no', column_name='Aadhaar Number')
    apaar_no = fields.Field(attribute='apaar_no', column_name='APAAR Number')
    email = fields.Field(attribute='email', column_name='Email')
    
    # Address
    address = fields.Field(attribute='address', column_name='Address')
    city = fields.Field(attribute='city', column_name='City')
    state = fields.Field(attribute='state', column_name='State')
    pincode = fields.Field(attribute='pincode', column_name='Pincode')
    
    # Registration Details
    registration_number = fields.Field(attribute='registration_number', column_name='Registration Number')
    sr_no = fields.Field(attribute='sr_no', column_name='Serial Number')
    old_registration_no = fields.Field(attribute='old_registration_no', column_name='Old Registration Number')
    
    # Migration Details
    migrated_from_other_university = fields.Field(
        attribute='migrated_from_other_university',
        column_name='Migrated from Other University',
        widget=BooleanWidget()
    )
    last_attended_university = fields.Field(attribute='last_attended_university', column_name='Last Attended University')
    migration_submitted = fields.Field(
        attribute='migration_submitted',
        column_name='Migration Certificate Submitted',
        widget=BooleanWidget()
    )
    
    # Status Fields
    is_account_created = fields.Field(
        attribute='is_account_created',
        column_name='Account Created',
        widget=BooleanWidget()
    )
    is_registration_completed = fields.Field(
        attribute='is_registration_completed',
        column_name='Registration Completed',
        widget=BooleanWidget()
    )
    is_deleted = fields.Field(
        attribute='is_deleted',
        column_name='Deleted',
        widget=BooleanWidget()
    )
    
    # Timestamps
    registration_at = fields.Field(
        attribute='registration_at',
        column_name='Registration Date & Time',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )
    created_at = fields.Field(
        attribute='created_at',
        column_name='Created At',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )
    updated_at = fields.Field(
        attribute='updated_at',
        column_name='Updated At',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )
    
    class Meta:
        model = NewRegistration
        # Define which fields to export
        fields = (
            'uid',
            'student_name',
            'student_name_hindi',
            'father_name',
            'mother_name',
            'date_of_birth',
            'gender',
            'caste',
            'religion',
            'nationality',
            'mobile_no',
            'aadhaar_no',
            'apaar_no',
            'email',
            'address',
            'city',
            'state',
            'pincode',
            'course',
            'course_code',
            'batch',
            'session',
            'college',
            'college_code',
            'registration_number',
            'sr_no',
            'old_registration_no',
            'migrated_from_other_university',
            'last_attended_university',
            'migration_submitted',
            'is_account_created',
            'is_registration_completed',
            'is_deleted',
            'registration_at',
            'created_at',
            'updated_at',
        )
        export_order = fields  # Export in the order defined above
        
    def dehydrate_gender(self, registration):
        """Convert gender code to readable format"""
        return registration.get_gender_display() if registration.gender else ''
    
    def dehydrate_caste(self, registration):
        """Convert caste code to readable format"""
        return registration.get_caste_display() if registration.caste else ''


class NewRegistrationCourseResource(resources.ModelResource):
    """Resource class for exporting Course data"""
    
    class Meta:
        model = NewRegistrationCourse
        fields = ('uid', 'code', 'name', 'registration_fee', 'registration_start_datetime', 
                  'registration_end_datetime', 'is_active', 'created_at', 'updated_at')
        export_order = fields


class NewRegistrationBatchResource(resources.ModelResource):
    """Resource class for exporting Batch data"""
    
    class Meta:
        model = NewRegistrationBatch
        fields = ('uid', 'name', 'is_active', 'created_at', 'updated_at')
        export_order = fields


class NewRegistrationSessionResource(resources.ModelResource):
    """Resource class for exporting Session data"""
    
    class Meta:
        model = NewRegistrationSession
        fields = ('uid', 'name', 'is_active', 'created_at', 'updated_at')
        export_order = fields
