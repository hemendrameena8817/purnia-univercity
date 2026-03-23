import os
import uuid
from django.db import models
from django.utils import timezone
from pup_umis_backend.storage_backends import OMRUploadStorage


def omr_upload_path(instance, filename):
    today = timezone.now().strftime("%Y/%m/%d/%H/%M/%S")
    return os.path.join(today, str(instance.uid), filename)


class OMRScan(models.Model):
    """Stores one uploaded OMR image and its processed result."""

    PART_CHOICES = [("C", "Part C — Evaluator"), ("D", "Part D — Student Info")]
    MODE_CHOICES = [("cv", "Computer Vision"), ("ai", "AI Vision")]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("error", "Error"),
    ]
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # ── Upload ───────────────────────────────────────────────────────────────
    image = models.ImageField(upload_to=omr_upload_path, storage=OMRUploadStorage())
    part = models.CharField(max_length=1, choices=PART_CHOICES)
    mode = models.CharField(max_length=2, choices=MODE_CHOICES, default="cv")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # ── Processing status ────────────────────────────────────────────────────
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    error_msg = models.TextField(blank=True)

    # ── Common decoded fields ─────────────────────────────────────────────────
    barcode = models.CharField(max_length=50, blank=True)
    center_code = models.CharField(max_length=10, blank=True)
    course_code = models.CharField(max_length=15, blank=True)

    # ── Part D specific ───────────────────────────────────────────────────────
    roll_number = models.CharField(max_length=15, blank=True)
    registration_no = models.CharField(max_length=30, blank=True)
    year = models.CharField(max_length=10, blank=True)
    sem = models.CharField(max_length=10, blank=True)
    session = models.CharField(max_length=10, blank=True)
    exam_type = models.CharField(max_length=20, blank=True)
    sitting = models.CharField(max_length=10, blank=True)

    # ── Part C specific ───────────────────────────────────────────────────────
    ug_old = models.CharField(max_length=10, blank=True)
    ug_new = models.CharField(max_length=10, blank=True)
    pg_sem = models.CharField(max_length=10, blank=True)
    faculty = models.CharField(max_length=20, blank=True)
    marks_obtained = models.CharField(max_length=5, blank=True)
    total_marks = models.CharField(max_length=5, blank=True)

    # ── Full raw JSON result ──────────────────────────────────────────────────
    json_result = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "OMR Scan"
        verbose_name_plural = "OMR Scans"

    def __str__(self):
        return f"OMRScan #{self.pk} | Part {self.part} | {self.barcode or 'no barcode'}"

    def apply_result(self, result: dict) -> None:
        """Populate fields from the processed result dict."""
        self.json_result = result
        self.barcode = result.get("barcode") or ""
        self.center_code = result.get("center_code") or ""
        self.course_code = result.get("course_code") or ""

        if self.part == "D":
            self.roll_number = result.get("roll_number") or ""
            self.registration_no = result.get("registration_no") or ""
            self.year = result.get("year") or ""
            self.sem = result.get("sem") or ""
            self.session = result.get("session") or ""
            self.exam_type = result.get("exam_type") or ""
            self.sitting = result.get("sitting") or ""

        elif self.part == "C":
            self.ug_old = result.get("ug_old") or ""
            self.ug_new = result.get("ug_new") or ""
            self.pg_sem = result.get("pg_sem") or ""
            self.faculty = result.get("faculty") or ""
            self.marks_obtained = result.get("marks_obtained") or ""
            self.total_marks = result.get("total_marks") or ""

        self.status = "done"
        self.processed_at = timezone.now()
