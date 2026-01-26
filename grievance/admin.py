from django.contrib import admin
from django.contrib import admin
from .models import GrievanceCategory, Grievance, GrievanceComment, GrievanceAttachment


@admin.register(GrievanceCategory)
class GrievanceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'display_order']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['uid', 'created_at', 'updated_at']
    fieldsets = (
        ('Category Information', {
            'fields': ('uid', 'name', 'code', 'description', 'is_active')
        }),
        ('Display Settings', {
            'fields': ('display_order',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    ordering = ['display_order', 'name']


class GrievanceCommentInline(admin.TabularInline):
    model = GrievanceComment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class GrievanceAttachmentInline(admin.TabularInline):
    model = GrievanceAttachment
    extra = 0
    readonly_fields = ['uid', 'file_name', 'file_size', 'file_type', 'uploaded_by', 'uploaded_at']
    fields = ['file', 'description', 'comment', 'uploaded_by', 'uploaded_at']


@admin.register(Grievance)
class GrievanceAdmin(admin.ModelAdmin):
    
    def submitted_date(self, obj):
        """Display submitted date without timezone conversion"""
        return obj.submitted_at.strftime('%Y-%m-%d %H:%M') if obj.submitted_at else '-'
    submitted_date.short_description = 'Submitted'
    
    list_display = [
        'grievance_number',
        'contact_person_name',
        'category',
        'subject',
        'status',
        'assigned_to_college',
        'escalated_to_university',
        'is_deleted',
        'submitted_date',
    ]
    list_filter = [
        'status',
        'category',
        'escalated_to_university',
        'is_deleted',
        'assigned_to_college',
        # 'submitted_at',  # Removed due to MySQL timezone issue
    ]
    search_fields = [
        'grievance_number',
        'contact_person_name',
        'subject',
        'description',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
    ]
    readonly_fields = [
        'uid',
        'grievance_number',
        'submitted_at',
        'updated_at',
        'resolved_at',
        'closed_at',
        'deleted_at',
    ]
    fieldsets = (
        ('Grievance Information', {
            'fields': ('uid', 'grievance_number', 'user', 'contact_person_name', 'contact_person_phone_number')
        }),
        ('Details', {
            'fields': ('category', 'subject', 'description')
        }),
        ('Status & Assignment', {
            'fields': (
                'status',
                'assigned_to_college',
                'escalated_to_university',
                'assigned_to_university',
            )
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at', 'modified_by', 'resolved_at', 'closed_at')
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
    )
    inlines = [GrievanceAttachmentInline, GrievanceCommentInline]
    # date_hierarchy = 'submitted_at'  # Removed due to MySQL timezone issue


@admin.register(GrievanceAttachment)
class GrievanceAttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'grievance', 'comment', 'file_size', 'file_type', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'grievance__grievance_number', 'description']
    readonly_fields = ['uid', 'file_name', 'file_size', 'file_type', 'uploaded_at']
    fieldsets = (
        ('Attachment Information', {
            'fields': ('uid', 'file', 'file_name', 'file_size', 'file_type', 'description')
        }),
        ('Links', {
            'fields': ('grievance', 'comment')
        }),
        ('Upload Info', {
            'fields': ('uploaded_by', 'uploaded_at')
        }),
    )


@admin.register(GrievanceComment)
class GrievanceCommentAdmin(admin.ModelAdmin):
    
    def comment_date(self, obj):
        """Display comment date without timezone conversion"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
    comment_date.short_description = 'Created'
    
    list_display = [
        'grievance',
        'commented_by',
        'comment_type',
        'previous_status',
        'new_status',
        'is_internal',
        'comment_date',
    ]
    list_filter = [
        'comment_type',
        'is_internal',
        # 'created_at',  # Removed due to MySQL timezone issue
    ]
    search_fields = [
        'grievance__grievance_number',
        'comment',
        'commented_by__username',
    ]
    readonly_fields = ['uid', 'created_at', 'updated_at']
    fieldsets = (
        ('Comment Information', {
            'fields': ('uid', 'grievance', 'commented_by', 'comment_type')
        }),
        ('Content', {
            'fields': ('comment', 'attachment', 'is_internal')
        }),
        ('Status Change', {
            'fields': ('previous_status', 'new_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    date_hierarchy = 'created_at'
