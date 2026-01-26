from rest_framework import serializers
from .models import GrievanceCategory, Grievance, GrievanceComment, GrievanceAttachment
from pup_umis_backend.utils.file_utils import get_absolute_url, format_file_size


class GrievanceAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for grievance attachments"""
    file_url = serializers.SerializerMethodField()
    file_size_formatted = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = GrievanceAttachment
        fields = [
            'uid',
            'file_url',
            'file_name',
            'file_size',
            'file_size_formatted',
            'file_type',
            'description',
            'uploaded_by_name',
            'uploaded_at',
        ]
        read_only_fields = ['uid', 'file_name', 'file_size', 'file_type', 'uploaded_at']
    
    def get_file_url(self, obj):
        """Get absolute URL for file"""
        return get_absolute_url(obj.file, self.context.get('request'))
    
    def get_file_size_formatted(self, obj):
        """Get human-readable file size"""
        return format_file_size(obj.file_size) if obj.file_size else None


class GrievanceCategorySerializer(serializers.ModelSerializer):
    """Serializer for grievance categories"""
    
    class Meta:
        model = GrievanceCategory
        fields = [
            'uid',
            'name',
            'code',
            'description',
            'is_active',
            'display_order',
        ]
        read_only_fields = ['uid']


class GrievanceCommentSerializer(serializers.ModelSerializer):
    """Serializer for grievance comments with attachments"""
    commented_by_name = serializers.CharField(source='commented_by.get_full_name', read_only=True)
    commented_by_username = serializers.CharField(source='commented_by.username', read_only=True)
    attachments = GrievanceAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = GrievanceComment
        fields = [
            'uid',
            'commented_by_name',
            'commented_by_username',
            'comment_type',
            'comment',
            'previous_status',
            'new_status',
            'is_internal',
            'created_at',
            'attachments',  # Include attachments in the response
        ]
        read_only_fields = ['uid', 'created_at']

class GrievanceListSerializer(serializers.ModelSerializer):
    """Serializer for listing grievances (minimal fields)"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    college_name = serializers.CharField(source='assigned_to_college.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Grievance
        fields = [
            'uid',
            'grievance_number',
            'contact_person_name',
            'contact_person_phone_number',
            'user_username',
            'category_display',
            'subject',
            'status',
            'status_display',
            'college_name',
            'escalated_to_university',
            'submitted_at',
            'updated_at',
        ]
        read_only_fields = ['uid', 'grievance_number', 'submitted_at', 'updated_at']


class GrievanceDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed grievance view with nested objects"""

    # Nested serializers
    user_details = serializers.SerializerMethodField()
    category_details = GrievanceCategorySerializer(source='category', read_only=True)
    college_details = serializers.SerializerMethodField()
    university_details = serializers.SerializerMethodField()
    modified_by_details = serializers.SerializerMethodField()

    # Display values
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # Related data
    comments = GrievanceCommentSerializer(many=True, read_only=True)
    attachments = serializers.SerializerMethodField()

    # -------------------------
    # Helper methods
    # -------------------------

    def get_attachments(self, obj):
        attachments = obj.attachments.all()
        return GrievanceAttachmentSerializer(
            attachments,
            many=True,
            context=self.context  # ✅ request passed correctly
        ).data

    def get_user_details(self, obj):
        user = obj.user
        if not user:
            return None

        return {
            'uid': str(user.uid),
            'username': user.username,
            'name': user.get_full_name(),
            'email': user.email,
        }

    def get_college_details(self, obj):
        college = obj.assigned_to_college
        if not college:
            return None

        return {
            'uid': str(college.uid),
            'name': college.name,
            'college_code': college.college_code,
            'short_name': college.short_name,
        }

    def get_university_details(self, obj):
        university = obj.assigned_to_university
        if not university:
            return None

        return {
            'uid': str(university.uid),
            'name': university.name,
        }

    def get_modified_by_details(self, obj):
        user = obj.modified_by
        if not user:
            return None

        return {
            'uid': str(user.uid),
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
        }

    # -------------------------
    # Meta
    # -------------------------

    class Meta:
        model = Grievance
        fields = [
            'uid',
            'grievance_number',

            'user_details',
            'contact_person_name',
            'contact_person_phone_number',

            'category_details',

            'subject',
            'description',
            'attachments',

            'status',
            'status_display',

            'college_details',
            'escalated_to_university',
            'university_details',
            'modified_by_details',

            'submitted_at',
            'updated_at',
            'resolved_at',
            'closed_at',

            'comments',
        ]

        read_only_fields = [
            'uid',
            'grievance_number',
            'submitted_at',
            'updated_at',
            'resolved_at',
            'closed_at',
            'assigned_to_college',
        ]


class GrievanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new grievance (student submission)"""
    category_uid = serializers.UUIDField(write_only=True, help_text="Category UID (not ID)")
    attachment_uids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="List of attachment UIDs to link to this grievance"
    )
    
    class Meta:
        model = Grievance
        fields = [
            'contact_person_name',
            'contact_person_phone_number',
            'category_uid',
            'subject',
            'description',
            'attachment_uids',
        ]
    
    def create(self, validated_data):
        # Get user from request context
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context required")
        
        user = request.user
        validated_data['user'] = user
        
        # Get category by UID (more secure than using ID)
        category_uid = validated_data.pop('category_uid')
        try:
            category = GrievanceCategory.objects.get(uid=category_uid, is_active=True)
            validated_data['category'] = category
        except GrievanceCategory.DoesNotExist:
            raise serializers.ValidationError({"category_uid": "Invalid or inactive category"})
        
        # Auto-assign to user's college
        if hasattr(user, 'get_college'):
            validated_data['assigned_to_college'] = user.get_college()
        
        # Extract attachment UIDs
        attachment_uids = validated_data.pop('attachment_uids', [])
        
        # Create grievance
        grievance = super().create(validated_data)
        
        # Link attachments to grievance
        if attachment_uids:
            updated_count = GrievanceAttachment.objects.filter(
                uid__in=attachment_uids,
                uploaded_by=request.user,
                grievance__isnull=True  # Only unlinked attachments
            ).update(grievance=grievance)
            
            # Log for debugging
            if updated_count != len(attachment_uids):
                print(f"Warning: Only {updated_count} of {len(attachment_uids)} attachments were linked")
        
        return grievance


class GrievanceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating grievance (college/university staff)"""
    
    class Meta:
        model = Grievance
        fields = [
            'status',
        ]
        extra_kwargs = {
            'status': {'required': False, 'help_text': 'Update grievance status'},
        }
    
    def validate_status(self, value):
        """Validate status transitions"""
        request = self.context.get('request')
        
        # Only college/university staff can update status
        if request and request.user.user_type not in ['college_user', 'university_admin']:
            raise serializers.ValidationError("You don't have permission to update status")
        
        return value
    
    def update(self, instance, validated_data):
        """Update grievance and auto-track who modified it"""
        # Auto-track who modified
        request = self.context.get('request')
        if request:
            validated_data['modified_by'] = request.user
        
        return super().update(instance, validated_data)


# In grievance/serializers.py

class GrievanceCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments with attachments"""
    attachment_uids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text="List of attachment UIDs to link to this comment"
    )

    class Meta:
        model = GrievanceComment
        fields = [
            'comment',
            'is_internal',
            'attachment_uids',  # Add this line
        ]
        extra_kwargs = {
            'is_internal': {'default': False, 'required': False}
        }

    def create(self, validated_data):
        # Get user from request context
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context required")
        
        # Extract attachment_uids
        attachment_uids = validated_data.pop('attachment_uids', [])
        
        # Set default values
        validated_data['commented_by'] = request.user
        validated_data['comment_type'] = 'comment'
        
        # Create comment
        comment = super().create(validated_data)
        
        # Link attachments to comment
        if attachment_uids:
            from .models import GrievanceAttachment
            updated_count = GrievanceAttachment.objects.filter(
                uid__in=attachment_uids,
                uploaded_by=request.user,
                comment__isnull=True  # Only unlinked attachments
            ).update(comment=comment)
            
            # Log for debugging
            if updated_count != len(attachment_uids):
                print(f"Warning: Only {updated_count} of {len(attachment_uids)} attachments were linked")
        
        return comment

class GrievanceEscalateSerializer(serializers.Serializer):
    """Serializer for escalating grievance to university"""
    comment = serializers.CharField(required=True)
    
    def validate(self, data):
        request = self.context.get('request')
        grievance = self.context.get('grievance')
        
        # Only college staff can escalate
        if request and request.user.user_type != 'college_user':
            raise serializers.ValidationError("Only college staff can escalate grievances")
        
        # Check if already escalated
        if grievance and grievance.escalated_to_university:
            raise serializers.ValidationError("Grievance is already escalated to university")
        
        return data


class GrievanceAttachmentUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading attachments before creating grievance"""
    
    class Meta:
        model = GrievanceAttachment
        fields = [
            'uid',
            'file',
            'description',
        ]
        read_only_fields = ['uid']
    
    def create(self, validated_data):
        # Get user from request context
        request = self.context.get('request')
        if request:
            validated_data['uploaded_by'] = request.user
        
        # Extract file metadata
        file_obj = validated_data.get('file')
        if file_obj:
            validated_data['file_name'] = file_obj.name
            validated_data['file_size'] = file_obj.size
            validated_data['file_type'] = file_obj.content_type
        
        return super().create(validated_data)
