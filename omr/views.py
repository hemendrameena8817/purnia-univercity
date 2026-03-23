import os
import tempfile
import traceback
import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination

from .models import OMRScan
from .serializers import (
    OMRBulkUploadSerializer,
    OMRUploadSerializer,
    OMRScanListSerializer,
    OMRScanDetailSerializer,
    OMRScanUpdateSerializer,
)
from .omr_processor.omr_reader import process_omr
from .omr_processor.ai_reader import process_omr_ai

logger = logging.getLogger(__name__)


def _process_scan_upload(image, part, mode, request):
    scan = OMRScan(part=part, mode=mode, image=image, status="processing")
    scan.save()

    suffix = os.path.splitext(image.name)[1] or ".jpg"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            image.seek(0)
            for chunk in image.chunks():
                tmp.write(chunk)
            tmp.flush()

            if mode == "ai":
                result = process_omr_ai(tmp.name, part=part)
            else:
                result = process_omr(tmp.name, part=part)

        scan.apply_result(result)
        scan.save()
        detail_serializer = OMRScanDetailSerializer(scan, context={"request": request})
        return scan, detail_serializer.data, None
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("OMR processing failed for scan #%s:\n%s", scan.pk, tb)
        scan.status = "error"
        scan.error_msg = str(exc)
        scan.save()
        detail_serializer = OMRScanDetailSerializer(scan, context={"request": request})
        return scan, detail_serializer.data, str(exc)


class OMRUploadView(APIView):
    """
    POST /api/omr/upload/

    Body (multipart/form-data):
        image : file (JPEG/PNG/TIFF/BMP)
        part  : "C" | "D"
        mode  : "cv" (default) | "ai"
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OMRUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        part = serializer.validated_data["part"]
        mode = serializer.validated_data["mode"]
        image = serializer.validated_data["image"]
        scan, result_data, error = _process_scan_upload(image, part, mode, request)
        if error:
            return Response(
                {"success": False, "uid": str(scan.uid), "error": f"Processing failed: {error}", "result": result_data},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"success": True, "uid": str(scan.uid), "result": result_data},
            status=status.HTTP_200_OK,
        )


class OMRBulkUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def post(self, request):
        images = request.FILES.getlist("images")
        serializer = OMRBulkUploadSerializer(
            data={
                "images": images,
                "part": request.data.get("part"),
                "mode": request.data.get("mode", "cv"),
            }
        )
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        part = serializer.validated_data["part"]
        mode = serializer.validated_data["mode"]
        images = serializer.validated_data["images"]

        results = []
        processed_count = 0
        failed_count = 0

        for image in images:
            scan, result_data, error = _process_scan_upload(image, part, mode, request)
            if error:
                failed_count += 1
            else:
                processed_count += 1
            results.append(
                {
                    "uid": str(scan.uid),
                    "filename": image.name,
                    "success": error is None,
                    "error": error,
                    "result": result_data,
                }
            )

        return Response(
            {
                "success": failed_count == 0,
                "part": part,
                "mode": mode,
                "total": len(images),
                "processed": processed_count,
                "failed": failed_count,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )


class OMRDetailView(APIView):
    """GET /api/omr/<uid>/"""

    permission_classes = [AllowAny]

    def get(self, request, uid):
        try:
            scan = OMRScan.objects.get(uid=uid)
        except OMRScan.DoesNotExist:
            return Response(
                {"success": False, "error": "Scan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = OMRScanDetailSerializer(scan, context={"request": request})
        return Response({"success": True, "result": serializer.data})


class OMRScanPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class OMRListView(APIView):
    """
    GET /api/omr/

    Query params: part=C|D, status=done|error, mode=cv|ai, page=1
    """

    permission_classes = [AllowAny]

    def get(self, request):
        qs = OMRScan.objects.all()

        part = request.query_params.get("part")
        if part in ("C", "D"):
            qs = qs.filter(part=part)

        scan_status = request.query_params.get("status")
        if scan_status:
            qs = qs.filter(status=scan_status)

        mode = request.query_params.get("mode")
        if mode in ("cv", "ai"):
            qs = qs.filter(mode=mode)

        paginator = OMRScanPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = OMRScanDetailSerializer(page, many=True, context={"request": request})

        return paginator.get_paginated_response(serializer.data)


class OMRUpdateView(APIView):
    """
    PATCH /api/omr/<uid>/update/
    PUT   /api/omr/<uid>/update/
    """

    permission_classes = [AllowAny]

    def _get_scan(self, uid):
        try:
            return OMRScan.objects.get(uid=uid)
        except OMRScan.DoesNotExist:
            return None

    def patch(self, request, uid):
        return self._update(request, uid, partial=True)

    def put(self, request, uid):
        return self._update(request, uid, partial=False)

    def _update(self, request, uid, partial: bool):
        scan = self._get_scan(uid)
        if scan is None:
            return Response(
                {"success": False, "error": "Scan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OMRScanUpdateSerializer(scan, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        detail_serializer = OMRScanDetailSerializer(scan, context={"request": request})
        return Response(
            {"success": True, "uid": str(scan.uid), "result": detail_serializer.data},
            status=status.HTTP_200_OK,
        )
