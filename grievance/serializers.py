from rest_framework import serializers
from .models import GrievanceCategory, Grievance, GrievanceComment, GrievanceAttachment
from pup_umis_backend.utils.file_utils import get_absolute_url, format_file_size
from .utils.profile_utils import verify_student_college_profile
from .utils.format_error import format_django_validation_error


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

    category_display = serializers.CharField(source='category.name', read_only=True)
    categories = GrievanceCategorySerializer(many=True, read_only=True)
    
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
            'college_name',
            'submitted_at',
            'updated_at',
            'resolved_at',
            'closed_at',
            'final_remark',
            'categories',
            'is_grievance_resolved'
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
    comments = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    # -------------------------
    # Helper methods
    # -------------------------

    def get_comments(self, obj):
        comments = obj.comments.all()
        return GrievanceCommentSerializer(
            comments,
            many=True,
            context=self.context
        ).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.user_type == 'student':
            representation.pop('comments', None)
        return representation

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
            'university_details',
            'modified_by_details',
            'is_grievance_resolved',
            'final_remark',
            'submitted_at',
            'updated_at',
            'resolved_at',
            'closed_at',
            'is_assigned_to_college',
            'is_assigned_to_university',
            'comments',
        ]

        read_only_fields = [
            'uid',
            'grievance_number',
            'submitted_at',
            'updated_at'
            'resolved_at',
            'closed_at',
            'assigned_to_college',
            'assigned_to_university',
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
    college_uid = serializers.UUIDField(write_only=True, help_text="College UID where grievance is to be submitted")
    active_profile = serializers.CharField(write_only=True, help_text="Active profile Type to verify the college")
    
    class Meta:
        model = Grievance
        fields = [
            'uid',
            'grievance_number',
            'contact_person_name',
            'contact_person_phone_number',
            'category_uid',
            'college_uid',
            'active_profile',
            'subject',
            'description',
            'attachment_uids',
            'submitted_at',
        ]
        read_only_fields = ['uid', 'grievance_number', 'submitted_at']

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
            raise serializers.ValidationError({"error": "Invalid or inactive category"})
        
        college_uid = validated_data.pop('college_uid')
        active_profile = validated_data.pop('active_profile')
        try:
            college = verify_student_college_profile(user, college_uid, active_profile)
            validated_data['assigned_to_college'] = college
        except Exception as e:
            message = format_django_validation_error(e)
            raise serializers.ValidationError({"error": message})
        
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
            'is_assigned_to_college',
            'is_assigned_to_university',
            'is_grievance_resolved',
            'final_remark',
        ]
        extra_kwargs = {
            'status': {'required': False},
            'is_assigned_to_college': {'required': False},
            'is_assigned_to_university': {'required': False},
            'is_grievance_resolved': {'required': False},
            'final_remark': {'required': False},
        }
    
    def validate_status(self, value):
        """Validate status transitions"""
        request = self.context.get('request')
        
        # Only college/university staff can update status
        if request and request.user.user_type not in ['college_user', 'university_admin']:
            raise serializers.ValidationError("You don't have permission to update status")
        
        return value
    
    def update(self, instance, validated_data):
        """Update grievance and auto-track as a comment log"""
        request = self.context.get('request')
        user = request.user
        
        # Track changes for audit log
        changes = []
        user_name = user.get_full_name() or user.username
        old_status = instance.status
        
        if 'status' in validated_data and instance.status != validated_data['status']:
            changes.append(f"changed status from '{instance.status}' to '{validated_data['status']}'")
            
        if 'is_assigned_to_college' in validated_data and instance.is_assigned_to_college != validated_data['is_assigned_to_college']:
            if validated_data['is_assigned_to_college']:
                changes.append("assigned this to college")
            else:
                changes.append("unassigned from college")
                 
        if 'is_assigned_to_university' in validated_data and instance.is_assigned_to_university != validated_data['is_assigned_to_university']:
            if validated_data['is_assigned_to_university']:
                changes.append("transferred this assigned to university")
            else:
                changes.append("unassigned from university")

        if 'is_grievance_resolved' in validated_data and instance.is_grievance_resolved != validated_data['is_grievance_resolved']:
            if validated_data['is_grievance_resolved']:
                remark = validated_data.get('final_remark', instance.final_remark)
                msg = "resolved this grievance"
                if remark:
                    msg += f" with remark: {remark}"
                changes.append(msg)
            else:
                changes.append("marked this grievance as unresolved")

        # Perform the actual update
        validated_data['modified_by'] = user
        instance = super().update(instance, validated_data)
        
        # Create comment log if changes occurred
        if changes:
            log_text = f"{user_name} " + " and ".join(changes)
            GrievanceComment.objects.create(
                grievance=instance,
                commented_by=user,
                comment_type='action_update',
                comment=log_text,
                previous_status=old_status,
                new_status=instance.status,
                is_internal=True
            )
        
        return instance


# In grievance/serializers.py

class GrievanceCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments with attachments"""
    attachment_uids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text="List of attachment UIDs to link to this comment"
    )

    new_status = serializers.CharField(required=False, write_only=True)
    is_assigned_to_college = serializers.BooleanField(required=False, write_only=True)
    is_assigned_to_university = serializers.BooleanField(required=False, write_only=True)
    is_grievance_resolved = serializers.BooleanField(required=False, write_only=True)
    final_remark = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = GrievanceComment
        fields = [
            'comment',
            'is_internal',
            'attachment_uids',
            'new_status',
            'is_assigned_to_college',
            'is_assigned_to_university',
            'is_grievance_resolved',
            'final_remark',
        ]
        extra_kwargs = {
            'comment': {'required': False, 'allow_blank': True},
            'is_internal': {'default': False, 'required': False}
        }

    def create(self, validated_data):
        # Get user and grievance
        request = self.context.get('request')
        grievance = self.context.get('grievance')
        user = request.user
        
        if not request or not grievance:
            raise serializers.ValidationError("Required context missing")
        
        # Pop attachment_uids and grievance update fields
        attachment_uids = validated_data.pop('attachment_uids', [])
        
        # We check for presence in validated_data because they were write_only fields
        # Note: .pop() removes them, so we capture them here
        status_update = validated_data.pop('new_status', None)
        transfer_college = validated_data.pop('is_assigned_to_college', None)
        transfer_university = validated_data.pop('is_assigned_to_university', None)
        resolve_update = validated_data.pop('is_grievance_resolved', None)
        remark_update = validated_data.pop('final_remark', None)
        
        # Track if ANY update flags were provided, even if value remains the same
        update_fields_provided = status_update or transfer_college is not None or transfer_university is not None or resolve_update is not None or remark_update is not None
        
        # Track changes for audit log
        changes = []
        user_name = user.get_full_name() or user.username
        old_status = grievance.status
        
        # Apply updates and record detailed changes
        if status_update:
            if grievance.status != status_update:
                changes.append(f"changed status from '{grievance.status}' to '{status_update}'")
                grievance.status = status_update
            else:
                changes.append(f"re-asserted status as '{status_update}'")
            
        if transfer_college is not None:
            if grievance.is_assigned_to_college != transfer_college:
                grievance.is_assigned_to_college = transfer_college
                changes.append("assigned this to college" if transfer_college else "unassigned from college")
            else:
                 changes.append("confirmed assignment to college" if transfer_college else "confirmed assignment away from college")
                 
        if transfer_university is not None:
            if grievance.is_assigned_to_university != transfer_university:
                grievance.is_assigned_to_university = transfer_university
                changes.append("transferred this assigned to university" if transfer_university else "unassigned from university")
            else:
                changes.append("confirmed assignment to university" if transfer_university else "confirmed assignment away from university")

        if resolve_update is not None:
            if grievance.is_grievance_resolved != resolve_update:
                grievance.is_grievance_resolved = resolve_update
                if resolve_update:
                    remark = remark_update or grievance.final_remark
                    msg = "resolved this grievance"
                    if remark:
                        msg += f" with remark: {remark}"
                    changes.append(msg)
                else:
                    changes.append("marked this grievance as unresolved")
            else:
                changes.append("confirmed resolution status")

        if remark_update is not None:
            if grievance.final_remark != remark_update:
                grievance.final_remark = remark_update
                if resolve_update is not True:
                    changes.append(f"updated final remark: {remark_update}")

        # Save grievance if modified or re-asserted
        if update_fields_provided:
            grievance.modified_by = user
            grievance.save()
            
        # Build final comment text
        system_log = f"{user_name} " + " and ".join(changes) if changes else ""
        user_comment = validated_data.get('comment', '').strip()
        
        if user_comment and system_log:
            validated_data['comment'] = f"{system_log}. Note: {user_comment}"
        elif system_log and not user_comment:
            validated_data['comment'] = system_log
        elif not system_log and not user_comment:
            # If neither, we need at least one if it's a manual comment post
            if not update_fields_provided:
                 raise serializers.ValidationError({"comment": "This field is required if no status changes are made."})
            validated_data['comment'] = f"{user_name} updated the grievance"

        # Set metadata
        validated_data['commented_by'] = user
        validated_data['comment_type'] = 'action_update' if update_fields_provided else 'comment'
        validated_data['previous_status'] = old_status
        validated_data['new_status'] = grievance.status
        
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
        if grievance and grievance.is_assigned_to_university:
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
