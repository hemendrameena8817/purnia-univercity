from import_export import resources, fields
from pgoldresult.models import PGOldStudentProfile, College
from accounts.models import UserAccount

class PGOldStudentProfileResource(resources.ModelResource):
    # Handle different CSV column names
    student_registration_no = fields.Field(
        attribute='registration_no',
        column_name='student_registration_no'
    )
    student_roll_no = fields.Field(
        attribute='roll_no', 
        column_name='student_roll_no'
    )
    student_batch = fields.Field(
        attribute='batch_code',
        column_name='student_batch'
    )
    student_name = fields.Field(
        attribute='first_name',
        column_name='student_name'
    )
    student_name_hindi = fields.Field(
        attribute='hindi_name',
        column_name='student_name_hindi'
    )
    
    class Meta:
        model = PGOldStudentProfile
        fields = (
            'user', 'uid', 'registration_no', 'student_registration_no', 'roll_no', 'student_roll_no',
            'first_name', 'student_name', 'hindi_name', 'student_name_hindi', 'fathers_name', 'mothers_name', 
            'gender', 'dob', 'date_of_birth',
            'college', 'course_code', 'discipline_code', 'batch_code', 'student_batch', 'current_semester',
            'pg_faculty', 'pg_department', 'pg_degree', 'pg_program',
            'final_result', 'gpa', 'cgpa', 'total_percentage',
            'profile_image', 'signature', 'address', 'admission_date', 'caste', 'enrollment_date', 
            'religion', 'nationality', 'medium_of_student',
            'source_user_id', 'is_active', 'created_at', 'updated_at'
        )
        import_id_fields = ('registration_no', 'roll_no')
        skip_unchanged = True
        report_skipped = True
        
    def before_import(self, dataset, **kwargs):
        """Handle college and user relationships before import"""
        # Map college codes to IDs
        college_mapping = {}
        colleges = College.objects.all()
        for college in colleges:
            college_mapping[college.college_code] = college.id
            college_mapping[college.name] = college.id
        
        # Map registration numbers to user IDs
        user_mapping = {}
        users = UserAccount.objects.all()
        for user in users:
            user_mapping[user.username] = user.id
        
        # Replace college codes/names with IDs and link users
        for i, row in enumerate(dataset):
            row_list = list(row)
            
            # Handle user field (index 0)
            if len(row_list) > 0:  # user field exists
                registration_no = row_list[2] if len(row_list) > 2 else None  # registration_no is at index 2
                first_name = row_list[4] if len(row_list) > 4 else None  # first_name is at index 4
                
                if registration_no:
                    if registration_no in user_mapping:
                        row_list[0] = user_mapping[registration_no]  # Set existing user ID
                    else:
                        # Create new user account
                        try:
                            new_user = UserAccount.objects.create_user(
                                username=registration_no,
                                email=f"{registration_no}@student.local",
                                first_name=first_name.split()[0] if first_name else '',
                                last_name=' '.join(first_name.split()[1:]) if first_name and len(first_name.split()) > 1 else ''
                            )
                            user_mapping[registration_no] = new_user.id
                            row_list[0] = new_user.id
                        except Exception as e:
                            print(f"Could not create user for {registration_no}: {e}")
                            row_list[0] = None
            
            # Handle college field (index 9 now since user is at 0)
            if len(row_list) > 9:  # college field exists
                college_value = row_list[9]
                if college_value in college_mapping:
                    row_list[9] = college_mapping[college_value]
            
            dataset[i] = tuple(row_list)
        
        return dataset
