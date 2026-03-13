from django.contrib import admin
from django.utils.html import format_html
from .models import GrievanceCategory, GrievanceSubCategory, Grievance, GrievanceComment, GrievanceAttachment, GrievancePayment


class GrievanceSubCategoryInline(admin.TabularInline):
    model = GrievanceSubCategory
    extra = 0
    readonly_fields = ['uid', 'created_at', 'updated_at']
    fields = ['uid', 'name', 'code', 'description', 'price', 'is_active', 'display_order', 'created_at', 'updated_at']


@admin.register(GrievanceCategory)
class GrievanceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'display_order']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['uid', 'created_at', 'updated_at']
    inlines = [GrievanceSubCategoryInline]
    raw_id_fields = []  # No foreign keys to optimize
    fieldsets = (
        ('Category Information', {
            'fields': ('uid', 'name', 'code', 'description', 'is_active', 'is_assigned_to_college', 'is_assigned_to_university')
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
        'subcategory',
        'subject',
        'status',
        'is_payment_completed',
        'is_assigned_to_college',
        'is_assigned_to_university',
        'is_grievance_resolved',
        'submitted_date',
    ]
    list_filter = [
        'status',
        'category',
        'subcategory',
        'is_deleted',
        'assigned_to_college',
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
    raw_id_fields = [
        'user',
        'category',
        'subcategory',
        'assigned_to_college',
        'assigned_to_university',
        'modified_by',
        'deleted_by',
    ]
    list_select_related = [
        'user',
        'category',
        'subcategory',
        'assigned_to_college',
        'assigned_to_university',
        'modified_by',
        'deleted_by',
    ]
    list_prefetch_related = []  # No prefetch needed for basic list
    show_full_result_count = False  # Faster loading for large datasets
    fieldsets = (
        ('Grievance Information', {
            'fields': ('uid', 'grievance_number', 'user', 'contact_person_name', 'contact_person_phone_number')
        }),
        ('Payment Information', {
            'fields': ('is_payment_completed', 'payment_amount')
        }),
        ('Details', {
            'fields': ('category', 'subcategory', 'subject', 'description')
        }),
        ('Status & Assignment', {
            'fields': (
                'status',
                'is_assigned_to_college',
                'is_assigned_to_university',
                'assigned_to_college',
                'assigned_to_university',
            )
        }),
        ('Resolution', {
            'fields': ('is_grievance_resolved', 'final_remark')
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
   


@admin.register(GrievanceAttachment)
class GrievanceAttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'grievance', 'comment', 'file_size', 'file_type', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'grievance__grievance_number', 'description']
    readonly_fields = ['uid', 'file_name', 'file_size', 'file_type', 'uploaded_at']
    raw_id_fields = ['grievance', 'comment', 'uploaded_by']
    list_select_related = ['grievance', 'comment', 'uploaded_by']
    show_full_result_count = False
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
    
    def attachments(self, obj):
        attachments = obj.attachments.all()
        if not attachments.exists():
            return "No Attachments"
        
        links = []
        for att in attachments:
            if att.file:
                links.append(format_html('<a href="{}" target="_blank">{}</a>', att.file.url, att.file_name))
            else:
                links.append(att.file_name)
        
        return format_html("<br>".join(links))
    attachments.short_description = 'Attachments'

    list_display = [
        'grievance',
        'commented_by',
        'comment_type',
        'attachments',
        'previous_status',
        'new_status',
        'is_internal',
        'comment_date',
    ]
    list_filter = [
        'comment_type',
        'is_internal',
    ]
    search_fields = [
        'grievance__grievance_number',
        'comment',
        'commented_by__username',
    ]
    readonly_fields = ['uid', 'created_at', 'updated_at', 'attachments']
    raw_id_fields = ['grievance', 'commented_by']
    list_select_related = ['grievance', 'commented_by']
    list_prefetch_related = ['attachments']
    show_full_result_count = False
    fieldsets = (
        ('Comment Information', {
            'fields': ('uid', 'grievance', 'commented_by', 'comment_type')
        }),
        ('Content', {
            'fields': ('comment', 'attachments', 'is_internal')
        }),
        ('Status Change', {
            'fields': ('previous_status', 'new_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(GrievancePayment)
class GrievancePaymentAdmin(admin.ModelAdmin):
    
    def payment_status_badge(self, obj):
        """Display payment status with color coding"""
        colors = {
            'SUCCESS': '#28a745',
            'PENDING': '#ffc107',
            'FAILED': '#dc3545',
            'ABORTED': '#6c757d',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.payment_status
        )
    payment_status_badge.short_description = 'Payment Status'
    
    def payment_date(self, obj):
        """Display payment date without timezone conversion"""
        if obj.created_at:
            try:
                return obj.created_at.strftime('%Y-%m-%d %H:%M')
            except (ValueError, AttributeError):
                return str(obj.created_at)
        return '-'
    payment_date.short_description = 'Created'
    
    list_display = [
        'order_id',
        'grievance',
        'amount',
        'payment_status_badge',
        'payment_mode',
        'tracking_id',
        'payment_date',
    ]
    list_filter = [
        'payment_status',
        'payment_mode',
    ]
    search_fields = [
        'order_id',
        'tracking_id',
        'bank_ref_no',
        'grievance__grievance_number',
        'grievance__contact_person_name',
    ]
    readonly_fields = [
        'order_id',
        'tracking_id',
        'bank_ref_no',
        'payment_mode',
        'card_name',
        'raw_response',
        'created_at',
        'updated_at',
    ]
    raw_id_fields = ['grievance']
    list_select_related = ['grievance']
    show_full_result_count = False
    fieldsets = (
        ('Payment Information', {
            'fields': ('grievance', 'order_id', 'amount', 'payment_status')
        }),
        ('Transaction Details', {
            'fields': ('tracking_id', 'bank_ref_no', 'payment_mode', 'card_name')
        }),
        ('Raw Response', {
            'fields': ('raw_response',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    ordering = ['-created_at']


@admin.register(GrievanceSubCategory)
class GrievanceSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'code', 'price', 'is_active', 'display_order']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['uid', 'created_at', 'updated_at']
    list_select_related = ['category']
    raw_id_fields = ['category']
    fieldsets = (
        ('SubCategory Information', {
            'fields': ('uid', 'category', 'name', 'code', 'description', 'price', 'is_active')
        }),
        ('Display Settings', {
            'fields': ('display_order',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    ordering = ['category__display_order', 'display_order', 'name']
