from django.contrib import admin
from django.utils.html import format_html
from .models import GrievanceCategory, GrievanceSubCategory, Grievance, GrievanceComment, GrievanceAttachment, GrievancePayment


class GrievanceCategoryFilter(admin.SimpleListFilter):
    """Lightweight filter that only loads category id/name instead of full objects."""
    title = 'Category'
    parameter_name = 'category__id__exact'

    def lookups(self, request, model_admin):
        return GrievanceCategory.objects.filter(is_active=True).values_list('id', 'name').order_by('display_order')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category_id=self.value())
        return queryset


class GrievanceSubCategoryFilter(admin.SimpleListFilter):
    """Lightweight filter that only loads subcategory id/name."""
    title = 'SubCategory'
    parameter_name = 'subcategory__id__exact'

    def lookups(self, request, model_admin):
        return GrievanceSubCategory.objects.filter(is_active=True).values_list('id', 'name').order_by('display_order')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(subcategory_id=self.value())
        return queryset


class AssignedCollegeFilter(admin.SimpleListFilter):
    """Lightweight filter using values_list to avoid loading full College objects."""
    title = 'Assigned College'
    parameter_name = 'assigned_to_college__id__exact'

    def lookups(self, request, model_admin):
        from colleges.models import College
        return College.objects.values_list('id', 'name').order_by('name')[:100]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(assigned_to_college_id=self.value())
        return queryset


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
    max_num = 10
    readonly_fields = ['created_at', 'updated_at']
    show_change_link = True


class GrievanceAttachmentInline(admin.TabularInline):
    model = GrievanceAttachment
    extra = 0
    max_num = 10
    readonly_fields = ['uid', 'file_name', 'file_size', 'file_type', 'uploaded_by', 'uploaded_at']
    fields = ['file', 'description', 'comment', 'uploaded_by', 'uploaded_at']
    show_change_link = True


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
    list_per_page = 25
    list_filter = [
        'status',
        GrievanceCategoryFilter,
        GrievanceSubCategoryFilter,
        'is_deleted',
        'is_payment_completed',
        AssignedCollegeFilter,
    ]
    search_fields = [
        'grievance_number',
        'contact_person_name',
        'subject',
        'user__username',
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
        'category',
        'subcategory',
    ]
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
    list_per_page = 25
    list_display = ['file_name', 'grievance', 'file_size', 'file_type', 'uploaded_at']
    list_filter = ['file_type']
    search_fields = ['file_name', 'grievance__grievance_number']
    readonly_fields = ['uid', 'file_name', 'file_size', 'file_type', 'uploaded_at']
    raw_id_fields = ['grievance', 'comment', 'uploaded_by']
    list_select_related = ['grievance']
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

    list_per_page = 25
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
    ]
    search_fields = [
        'grievance__grievance_number',
        'commented_by__username',
    ]
    readonly_fields = ['uid', 'created_at', 'updated_at', 'attachments']
    raw_id_fields = ['grievance', 'commented_by']
    list_select_related = ['grievance', 'commented_by']
    show_full_result_count = False

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('attachments')
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
    
    list_per_page = 25
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
    list_per_page = 25
    list_display = ['name', 'category', 'code', 'price', 'is_active', 'display_order']
    list_filter = ['is_active']
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
