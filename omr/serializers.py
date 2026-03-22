from rest_framework import serializers
from .models import OMRScan


class OMRUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    part = serializers.ChoiceField(choices=["C", "D", "c", "d"])
    mode = serializers.ChoiceField(choices=["cv", "ai"], default="cv")

    def validate_part(self, value):
        return value.upper()

    def validate_mode(self, value):
        return value.lower()


class OMRBulkUploadSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
        max_length=50,
    )
    part = serializers.ChoiceField(choices=["C", "D", "c", "d"])
    mode = serializers.ChoiceField(choices=["cv", "ai"], default="cv")

    def validate_part(self, value):
        return value.upper()

    def validate_mode(self, value):
        return value.lower()


class OMRScanListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OMRScan
        fields = [
            "id", "uid", "part", "mode", "status", "barcode",
            "center_code", "course_code", "uploaded_at", "processed_at",
        ]


class OMRScanUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OMRScan
        fields = [
            "part", "mode", "status", "error_msg",
            "barcode", "center_code", "course_code",
            "roll_number", "year", "sem", "session", "exam_type", "sitting",
            "ug_old", "ug_new", "pg_sem", "faculty", "marks_obtained", "total_marks",
            "json_result",
        ]


class OMRScanCVSerializer(serializers.ModelSerializer):
    """Flat field serializer for CV mode results."""
    class Meta:
        model = OMRScan
        fields = [
            "id", "uid", "part", "status", "barcode", "center_code", "course_code",
            "roll_number", "year", "sem", "session", "exam_type", "sitting",
            "ug_old", "ug_new", "pg_sem", "faculty",
            "marks_obtained", "total_marks",
            "uploaded_at", "processed_at", "error_msg",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Remove Part-D fields from Part-C response and vice versa
        if instance.part == "C":
            for f in ("roll_number", "year", "sem", "session", "exam_type", "sitting"):
                data.pop(f, None)
        elif instance.part == "D":
            for f in ("ug_old", "ug_new", "pg_sem", "faculty", "marks_obtained", "total_marks"):
                data.pop(f, None)
        # Replace empty strings with None
        return {k: (v if v != "" else None) for k, v in data.items()}


class OMRScanDetailSerializer(serializers.ModelSerializer):
    """Full detail with raw_result for individual scan retrieval."""
    data = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    verification = serializers.SerializerMethodField()
    flags = serializers.SerializerMethodField()
    error = serializers.CharField(source="error_msg", read_only=True)

    class Meta:
        model = OMRScan
        fields = [
            "id", "uid", "image_url", "part", "mode", "status",
            "barcode", "center_code", "course_code",
            "roll_number", "year", "sem", "session", "exam_type", "sitting",
            "ug_old", "ug_new", "pg_sem", "faculty", "marks_obtained", "total_marks",
            "uploaded_at", "processed_at", "error", "verification", "flags", "data",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in list(data.items()):
            if value == "":
                data[key] = None

        if instance.part == "C":
            for f in ("roll_number", "year", "sem", "session", "exam_type", "sitting"):
                data.pop(f, None)
        elif instance.part == "D":
            for f in ("ug_old", "ug_new", "pg_sem", "faculty", "marks_obtained", "total_marks"):
                data.pop(f, None)

        if instance.mode != "ai":
            data.pop("verification", None)
            data.pop("flags", None)

        if data.get("error") == "":
            data["error"] = None
        return data

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_data(self, obj):
        raw = obj.json_result or {}
        is_ai = raw.get("mode") == "ai"

        if is_ai:
            return _build_ai_data(obj, raw)
        return _build_cv_data(obj)

    def get_verification(self, obj):
        raw = obj.json_result or {}
        if raw.get("mode") != "ai":
            return None
        return raw.get("verification")

    def get_flags(self, obj):
        raw = obj.json_result or {}
        if raw.get("mode") != "ai":
            return []
        return raw.get("flags", [])


def _build_cv_data(scan: OMRScan) -> dict:
    data = {
        "barcode": scan.barcode or None,
        "center_code": scan.center_code or None,
        "course_code": scan.course_code or None,
    }
    if scan.part == "D":
        data.update({
            "roll_number": scan.roll_number or None,
            "year": scan.year or None,
            "sem": scan.sem or None,
            "session": scan.session or None,
            "exam_type": scan.exam_type or None,
            "sitting": scan.sitting or None,
        })
    elif scan.part == "C":
        data.update({
            "ug_old": scan.ug_old or None,
            "ug_new": scan.ug_new or None,
            "pg_sem": scan.pg_sem or None,
            "faculty": scan.faculty or None,
            "marks_obtained": scan.marks_obtained or None,
            "total_marks": scan.total_marks or None,
        })
    return data


def _build_ai_data(scan: OMRScan, raw: dict) -> dict:
    readings = raw.get("readings", {})
    ai_raw = raw.get("ai_raw", {})
    flags = raw.get("flags", [])
    verification = raw.get("verification")

    fields = {}

    # Barcode
    bc_readings = readings.get("barcode", {})
    fields["barcode"] = {
        "value": scan.barcode or None,
        "decoded": bc_readings.get("decoded"),
        "printed_digits": bc_readings.get("printed_digits"),
    }

    if scan.part == "D":
        for name in ("roll_number", "center_code", "course_code", "session"):
            fields[name] = _ai_grid_field(readings.get(name, {}), ai_raw.get(name, {}), getattr(scan, name, "") or None)

        year_reading = readings.get("year", {})
        sem_reading = readings.get("sem", {})
        fields["year"] = {"value": scan.year or None, "handwritten": year_reading.get("handwritten"), "bubble": year_reading.get("bubble")}
        fields["sem"] = {"value": scan.sem or None, "handwritten": sem_reading.get("handwritten"), "bubble": sem_reading.get("bubble")}

        for name in ("exam_type", "sitting"):
            src = ai_raw.get(name, {})
            fields[name] = {"value": getattr(scan, name, "") or None, "filled_bubbles": src.get("filled_bubbles", []) if isinstance(src, dict) else []}

        fields["name"] = raw.get("name")
        fields["father_name"] = raw.get("father_name")
        fields["paper_name"] = raw.get("paper_name")
        fields["date_of_exam"] = raw.get("date_of_exam")

    elif scan.part == "C":
        for name in ("ug_old", "ug_new", "pg_sem", "faculty"):
            src = ai_raw.get(name, {})
            fields[name] = {"value": getattr(scan, name, "") or None, "filled_bubbles": src.get("filled_bubbles", []) if isinstance(src, dict) else []}

        for name in ("course_code", "center_code", "marks_obtained", "total_marks"):
            fields[name] = _ai_grid_field(readings.get(name, {}), ai_raw.get(name, {}), getattr(scan, name, "") or None)

        fields["subject_text"] = raw.get("subject_text")
        fields["marks_in_words"] = raw.get("marks_in_words")

    return {"fields": fields}


def _ai_grid_field(readings: dict, src: dict, final_value) -> dict:
    field = {
        "value": final_value,
        "handwritten": readings.get("handwritten"),
        "bubble": readings.get("bubble"),
    }
    if isinstance(src, dict):
        if src.get("column_values"):
            field["column_values"] = src["column_values"]
        if src.get("multiple_filled"):
            field["multiple_filled"] = True
            field["columns_with_multiple"] = src.get("columns_with_multiple", [])
    return field
