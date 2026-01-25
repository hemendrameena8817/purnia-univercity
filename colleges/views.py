from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import College
from .serializers import (
    CollegeSerializer,
    CollegeCreateUpdateSerializer,
    CollegeBulkUploadSerializer
)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="List all colleges with pagination and filtering",
    manual_parameters=[
        openapi.Parameter('university_id', openapi.IN_QUERY, description="Filter by university ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('college_code', openapi.IN_QUERY, description="Filter by college code", type=openapi.TYPE_STRING),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search by college name", type=openapi.TYPE_STRING),
    ],
    responses={
        200: CollegeSerializer(many=True),
    },
    tags=['Colleges'],
    security=[{'Bearer': []}]
))
class CollegeListView(generics.ListAPIView):
    """
    GET: List all colleges with pagination and filtering
    """
    permission_classes = [AllowAny]
    queryset = College.objects.all().select_related('university')
    serializer_class = CollegeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by university
        university_id = self.request.query_params.get('university_id')
        if university_id:
            queryset = queryset.filter(university_id=university_id)
        
        # Filter by college code
        college_code = self.request.query_params.get('college_code')
        if college_code:
            queryset = queryset.filter(college_code__icontains=college_code)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-created_at')


class CollegeCreateView(APIView):
    """
    POST: Create a new college
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new college",
        request_body=CollegeCreateUpdateSerializer,
        responses={
            201: openapi.Response(
                description="College created successfully",
                schema=CollegeSerializer,
                examples={
                    "application/json": {
                        "message": "College created successfully",
                        "college": {
                            "id": 1,
                            "uid": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Sample College",
                            "short_name": "SC",
                            "college_code": "SC001"
                        }
                    }
                }
            ),
            400: 'Validation error'
        },
        tags=['Colleges'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        """Create a new college."""
        serializer = CollegeCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            college = serializer.save()
            response_serializer = CollegeSerializer(college, context={'request': request})
            return Response(
                {
                    'message': 'College created successfully',
                    'college': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CollegeDetailView(APIView):
    """
    GET: Retrieve a single college by ID or UID
    PUT: Update a college
    PATCH: Partially update a college
    DELETE: Delete a college
    """
    permission_classes = [AllowAny]
    
    identifier_param = openapi.Parameter(
        'identifier',
        openapi.IN_PATH,
        description="College ID (integer) or UID (UUID string)",
        type=openapi.TYPE_STRING,
        required=True
    )

    def get_object(self, identifier):
        """Get college by ID or UID."""
        try:
            # Try to get by ID first
            if identifier.isdigit():
                return College.objects.select_related('university').get(id=identifier)
            # Otherwise try by UID
            return College.objects.select_related('university').get(uid=identifier)
        except College.DoesNotExist:
            return None

    @swagger_auto_schema(
        operation_description="Get college details by ID or UID",
        responses={
            200: CollegeSerializer,
            404: 'College not found'
        },
        tags=['Colleges'],
        security=[{'Bearer': []}]
    )
    def get(self, request, identifier):
        """Retrieve college details."""
        college = self.get_object(identifier)
        if not college:
            return Response(
                {'error': 'College not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CollegeSerializer(college, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Update all fields of a college",
        request_body=CollegeCreateUpdateSerializer,
        responses={
            200: CollegeSerializer,
            400: 'Validation error',
            404: 'College not found'
        },
        tags=['Colleges'],
        security=[{'Bearer': []}]
    )
    def put(self, request, identifier):
        """Update college (full update)."""
        college = self.get_object(identifier)
        if not college:
            return Response(
                {'error': 'College not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CollegeCreateUpdateSerializer(college, data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_serializer = CollegeSerializer(college, context={'request': request})
            return Response(
                {
                    'message': 'College updated successfully',
                    'college': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Partially update college fields",
        request_body=CollegeCreateUpdateSerializer,
        responses={
            200: CollegeSerializer,
            400: 'Validation error',
            404: 'College not found'
        },
        tags=['Colleges'],
        security=[{'Bearer': []}]
    )
    def patch(self, request, identifier):
        """Partially update college."""
        college = self.get_object(identifier)
        if not college:
            return Response(
                {'error': 'College not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CollegeCreateUpdateSerializer(college, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = CollegeSerializer(college, context={'request': request})
            return Response(
                {
                    'message': 'College updated successfully',
                    'college': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete a college",
        responses={
            200: 'College deleted successfully',
            404: 'College not found'
        },
        tags=['Colleges'],
        security=[{'Bearer': []}]
    )
    def delete(self, request, identifier):
        """Delete a college."""
        college = self.get_object(identifier)
        if not college:
            return Response(
                {'error': 'College not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        college_name = college.name
        college.delete()
        
        return Response(
            {
                'message': f'College "{college_name}" deleted successfully'
            },
            status=status.HTTP_200_OK
        )


class CollegeBulkUploadView(APIView):
    """
    POST: Upload CSV file to create multiple colleges at once
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Bulk upload colleges via CSV file",
        request_body=CollegeBulkUploadSerializer,
        responses={
            201: openapi.Response(
                description="Bulk upload completed",
                examples={
                    "application/json": {
                        "message": "Bulk upload completed",
                        "total_rows": 10,
                        "created_count": 8,
                        "error_count": 2,
                        "errors": [{"row": 3, "error": "College code already exists"}]
                    }
                }
            ),
            400: 'Invalid CSV file'
        },
        tags=['Colleges'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        """
        Upload CSV file with college data.
        Expected CSV columns: name, short_name, college_code, address, principal,
                             contact_no, email, founded, website, university_id
        """
        serializer = CollegeBulkUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            result = serializer.create_colleges_from_csv()
            
            response_data = {
                'message': 'Bulk upload completed',
                'total_rows': result['total_rows'],
                'created_count': result['created_count'],
                'error_count': len(result['errors']),
            }
            
            if result['errors']:
                response_data['errors'] = result['errors']
            
            if result['created_colleges']:
                response_data['created_colleges'] = CollegeSerializer(
                    result['created_colleges'],
                    many=True,
                    context={'request': request}
                ).data
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CollegeStatsView(APIView):
    """
    GET: Get statistics about colleges
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get statistics about colleges",
        responses={
            200: openapi.Response(
                description="College statistics",
                examples={
                    "application/json": {
                        "total_colleges": 25,
                        "colleges_by_university": [
                            {"university__name": "Purnea University", "count": 15}
                        ]
                    }
                }
            )
        },
        tags=['Colleges'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        """Get college statistics."""
        from django.db.models import Count
        
        total_colleges = College.objects.count()
        colleges_by_university = College.objects.values(
            'university__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response(
            {
                'total_colleges': total_colleges,
                'colleges_by_university': list(colleges_by_university),
            },
            status=status.HTTP_200_OK
        )
