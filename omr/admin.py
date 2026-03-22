from django.contrib import admin
from .models import OMRScan


@admin.register(OMRScan)
class OMRScanAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "uid",
        "part",
        "mode",
        "status",
        "barcode",
        "roll_number",
        "course_code",
        "center_code",
        "uploaded_at",
        "processed_at",
    ]
    list_filter = ["part", "mode", "status", "uploaded_at", "processed_at"]
    search_fields = ["uid", "barcode", "roll_number", "course_code", "center_code"]
    readonly_fields = [
        "uid",
        "json_result",
        "processed_at",
        "created_at",
        "updated_at",
        "uploaded_at",
    ]
    ordering = ["-uploaded_at"]
    list_per_page = 50
    fieldsets = [
        (None, {"fields": ["uid", "image", "part", "mode", "status", "error_msg"]}),
        ("Common Fields", {"fields": ["barcode", "center_code", "course_code"]}),
        ("Part D Fields", {"fields": ["roll_number", "year", "sem", "session", "exam_type", "sitting"]}),
        ("Part C Fields", {"fields": ["ug_old", "ug_new", "pg_sem", "faculty", "marks_obtained", "total_marks"]}),
        ("Processing Data", {"fields": ["json_result", "uploaded_at", "processed_at", "created_at", "updated_at"]}),
    ]
