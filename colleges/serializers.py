from rest_framework import serializers
from .models import College
from django.contrib.auth import get_user_model
from pup_umis_backend.utils.file_utils import get_absolute_url
import csv
import io

User = get_user_model()


class CollegeSerializer(serializers.ModelSerializer):
    """
    Serializer for College model with all fields.
    """
    admin_user_email = serializers.EmailField(source='admin_user.email', read_only=True)
    university_name = serializers.CharField(source='university.name', read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = [
            'id',
            'uid',
            'admin_user',
            'admin_user_email',
            'name',
            'short_name',
            'college_code',
            'address',
            'principal',
            'contact_no',
            'email',
            'founded',
            'website',
            'logo',
            'logo_url',
            'university',
            'university_name',
            'json_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'uid', 'created_at', 'updated_at']

    def get_logo_url(self, obj):
        """Return full URL for logo if it exists."""
        return get_absolute_url(obj.logo, self.context.get('request'))


class CollegeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating colleges.
    """
    class Meta:
        model = College
        fields = [
            'admin_user',
            'name',
            'short_name',
            'college_code',
            'address',
            'principal',
            'contact_no',
            'email',
            'founded',
            'website',
            'logo',
            'university',
            'json_data',
        ]

    def validate_college_code(self, value):
        """Ensure college code is unique."""
        instance = self.instance
        if instance and instance.college_code == value:
            return value
        
        if College.objects.filter(college_code=value).exists():
            raise serializers.ValidationError("College with this code already exists.")
        return value

    def validate_email(self, value):
        """Ensure email is unique."""
        instance = self.instance
        if instance and instance.email == value:
            return value
        
        if College.objects.filter(email=value).exists():
            raise serializers.ValidationError("College with this email already exists.")
        return value


class CollegeBulkUploadSerializer(serializers.Serializer):
    """
    Serializer for bulk CSV upload of colleges.
    Expected CSV columns: name, short_name, college_code, address, principal, 
                         contact_no, email, founded, website, university_id
    """
    csv_file = serializers.FileField()

    def validate_csv_file(self, value):
        """Validate that the uploaded file is a CSV."""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are allowed.")
        return value

    def create_colleges_from_csv(self):
        """Parse CSV and create college records."""
        csv_file = self.validated_data['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        created_colleges = []
        errors = []
        row_number = 1

        required_fields = [
            'name', 'short_name', 'college_code', 'address', 
            'principal', 'contact_no', 'email', 'founded', 'university_id'
        ]

        for row in reader:
            row_number += 1
            try:
                # Validate required fields
                missing_fields = [field for field in required_fields if not row.get(field)]
                if missing_fields:
                    errors.append({
                        'row': row_number,
                        'error': f"Missing required fields: {', '.join(missing_fields)}"
                    })
                    continue

                # Check if college_code already exists
                if College.objects.filter(college_code=row['college_code']).exists():
                    errors.append({
                        'row': row_number,
                        'error': f"College code '{row['college_code']}' already exists."
                    })
                    continue

                # Create college
                college_data = {
                    'name': row['name'],
                    'short_name': row['short_name'],
                    'college_code': row['college_code'],
                    'address': row['address'],
                    'principal': row['principal'],
                    'contact_no': row['contact_no'],
                    'email': row['email'],
                    'founded': row['founded'],
                    'website': row.get('website', ''),
                    'university_id': row['university_id'],
                }

                # Optional admin_user
                if row.get('admin_user_id'):
                    college_data['admin_user_id'] = row['admin_user_id']

                college = College.objects.create(**college_data)
                created_colleges.append(college)

            except Exception as e:
                errors.append({
                    'row': row_number,
                    'error': str(e)
                })

        return {
            'created_count': len(created_colleges),
            'created_colleges': created_colleges,
            'errors': errors,
            'total_rows': row_number - 1
        }
