from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import UGSemResultCurrent
from .serializers import UGSemResultUpdateSerializer
from django.db import transaction
from django.utils import timezone
from accounts.permissions import IsUniversityAdmin

class UGSemResultUpdateView(APIView):
    """
    API to search and update UGSemResultCurrent entries.
    
    GET: Search by semester, roll_no, or reg_no.
    PUT: Update a list of entries by ID.
    """
    authentication_classes = [JWTAuthentication] # Enforce JWT Authentication
    permission_classes = [IsAuthenticated, IsUniversityAdmin] # Require authentication and University Admin role

    def get(self, request):
        semester = request.query_params.get('semester')
        roll_no = request.query_params.get('roll_no')
        reg_no = request.query_params.get('reg_no')

        # Enforce Semester AND (RollNo OR RegNo)
        if not semester or not (roll_no or reg_no):
            return Response(
                {"error": "You must provide 'semester' AND either 'roll_no' or 'reg_no'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Optimize for 800k rows: Fetch only fields used by the serializer
        fields = [
            'id', 'semester_code', 'college_roll_no', 'college_reg_no', 
            'paper_code', 'subject_code', 'subject_name', 'status',
            'mark_secured', 'maximum_mark', 'pass_mark','exam_type',
            'subject_total_mark', 'grand_total_mark',
            'total_secured_mark', 'final_result', 'is_migrated'
        ]
        queryset = UGSemResultCurrent.objects.only(*fields)

        queryset = queryset.filter(semester_code=semester)
        
        if roll_no:
            queryset = queryset.filter(college_roll_no=roll_no)
        if reg_no:
            queryset = queryset.filter(college_reg_no=reg_no)

        # Optimization: Limit results to avoid overload if query is too broad
        queryset = queryset[:100] 

        serializer = UGSemResultUpdateSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """
        Expects a list of objects with 'id' and fields to update.
        Example:
        [
            {"id": 1, "mark_secured": "85"},
            {"id": 2, "final_result": "PASS"}
        ]
        """
        data = request.data
        if not isinstance(data, list):
            return Response(
                {"error": "Expected a list of objects."},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_ids = []
        errors = []

        try:
            with transaction.atomic():
                for item in data:
                    item_id = item.get('id')
                    if not item_id:
                        errors.append({"error": "Missing ID", "data": item})
                        continue

                    try:
                        record = UGSemResultCurrent.objects.get(id=item_id)
                        serializer = UGSemResultUpdateSerializer(record, data=item, partial=True)
                        if serializer.is_valid():
                            serializer.save(
                                is_changed=True,
                                changed_at=timezone.now(),
                                changed_by=request.user  # the logged-in university admin
                            )
                            updated_ids.append(item_id)
                        else:
                            errors.append({"id": item_id, "errors": serializer.errors})
                    except UGSemResultCurrent.DoesNotExist:
                        errors.append({"id": item_id, "error": "Record not found"})

        except Exception as e:
             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "success": True,
            "updated_count": len(updated_ids),
            "updated_ids": updated_ids,
            "errors": errors
        }, status=status.HTTP_200_OK)
