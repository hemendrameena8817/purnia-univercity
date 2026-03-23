from import_export import resources
from pgoldresult.models import PGOldStudentProfile, College

class PGOldStudentProfileResource(resources.ModelResource):
    class Meta:
        model = PGOldStudentProfile
        fields = (
            'uid', 'registration_no', 'roll_no', 'student_name', 'student_name_hindi',
            'fathers_name', 'mothers_name', 'gender', 'dob',
            'college', 'course_code', 'discipline_code', 'batch_code', 'current_semester',
            'pg_faculty', 'pg_department', 'pg_degree', 'pg_program',
            'final_result', 'gpa', 'cgpa', 'total_percentage',
            'source_user_id', 'is_active', 'created_at', 'updated_at'
        )
        import_id_fields = ('registration_no', 'roll_no')
        skip_unchanged = True
        report_skipped = True
        
    def before_import(self, dataset, **kwargs):
        """Handle college relationships before import"""
        # Map college codes to IDs
        college_mapping = {}
        colleges = College.objects.all()
        for college in colleges:
            college_mapping[college.college_code] = college.id
            college_mapping[college.name] = college.id
        
        # Replace college codes/names with IDs
        for i, row in enumerate(dataset):
            if len(row) > 8:  # college field exists
                college_value = row[8]  # college field index
                if college_value in college_mapping:
                    row[8] = college_mapping[college_value]
        
        return dataset
