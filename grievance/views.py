from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Grievance, GrievanceComment
from .serializers import (
    GrievanceListSerializer,
    GrievanceDetailSerializer,
    GrievanceCreateSerializer,
    GrievanceUpdateSerializer,
    GrievanceCommentSerializer,
    GrievanceCommentCreateSerializer,
    GrievanceEscalateSerializer,
    GrievanceAttachmentUploadSerializer,
    GrievanceAttachmentSerializer,
)
from .utils.format_error import get_first_serializer_error
from pup_umis_backend.utils.pagination import DefaultPagination

class GrievanceListCreateView(APIView):
    """
    GET: List all grievances (filtered by user role)
    POST: Create a new grievance (students only)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all grievances. Students see their own, college staff see their college's, university admin see all.",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by status (for staff)",
                type=openapi.TYPE_STRING,
                enum=['open', 'in_progress', 'resolved', 'closed', 'canceled', 'escalated']
            ),
            openapi.Parameter(
                'is_resolved',
                openapi.IN_QUERY,
                description="Filter by resolution status (true/false, for students/all)",
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Filter by category UID (UUID string)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'scope',
                openapi.IN_QUERY,
                description="Filter by scope: 'college' or 'university'. Only relevant for University Admin to see specific buckets.",
                type=openapi.TYPE_STRING,
                enum=['college', 'university']
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Number of results to return per page",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'college',
                openapi.IN_QUERY,
                description="Filter by College UID (for University Admins only)",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={200: GrievanceListSerializer(many=True)},
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        """List grievances based on user role with pagination and filtering"""
        user = request.user
        
        # Filter based on user type
        if user.user_type == 'student':
            # Students see only their own grievances
            queryset = Grievance.objects.filter(user=user, is_deleted=False)
        
        elif user.user_type == 'college_user':
            # College staff see grievances assigned to their college AND currently at college level
            college = user.get_college()
            if not college:
                return Response(
                    {'error': 'College association not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            queryset = Grievance.objects.filter(
                assigned_to_college=college, 
                is_assigned_to_college=True,
                is_deleted=False
            )
        
        elif user.user_type == 'university_admin':
            # University admin sees all (excluding deleted)
            queryset = Grievance.objects.filter(is_deleted=False)
            
            # Allow University to filter by scope
            scope = request.query_params.get('scope')
            if scope == 'university':
                queryset = queryset.filter(is_assigned_to_university=True)
            elif scope == 'college':
                queryset = queryset.filter(is_assigned_to_college=True)
        
        else:
            return Response(
                {'error': 'Unauthorized user type'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter and user.user_type in ['college_user', 'university_admin']:
            queryset = queryset.filter(status=status_filter)
            
        is_resolved_filter = request.query_params.get('is_resolved')
        if is_resolved_filter is not None:
            # Handle boolean conversion
            is_resolved_bool = is_resolved_filter.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_grievance_resolved=is_resolved_bool)
        
        category_filter = request.query_params.get('category')
        if category_filter:
            # Filter by category UID (more secure than ID)
            queryset = queryset.filter(category__uid=category_filter)

        # University Admin can filter by specific college
        college_filter = request.query_params.get('college')
        if college_filter and user.user_type == 'university_admin':
            queryset = queryset.filter(assigned_to_college__uid=college_filter)
        
        queryset = queryset.order_by('-submitted_at')
        
        paginator = DefaultPagination()
        result_page = paginator.paginate_queryset(queryset, request)

        if result_page is not None:
            serializer = GrievanceListSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = GrievanceListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @swagger_auto_schema(
        operation_description="""Submit a new grievance (students only).
        
        **Workflow:**
        1. Upload attachments using `/api/grievances/upload-attachment/` (optional)
        2. Collect the attachment UIDs from upload responses
        3. Submit grievance with attachment UIDs
        
        **Example:**
        ```json
        {
          "contact_person_name": "John Doe",
          "contact_person_phone_number": "9876543210",
          "category_uid": "category-uuid-here",
          "college_uid": "college-uuid-here",
          "active_profile": "ug_profile",
          "subject": "Name Correction in Marksheet",
          "description": "I need to correct my name spelling in the marksheet",
          "attachment_uids": ["uuid-1", "uuid-2"]
        }
        ```
        """,
        request_body=GrievanceCreateSerializer,
        responses={
            201: GrievanceDetailSerializer,
            400: 'Validation error',
            403: 'Only students can submit grievances'
        },
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        """Create a new grievance (students only)"""
        if request.user.user_type != 'student':
            return Response(
                {'error': 'Only students can submit grievances'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = GrievanceCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            grievance = serializer.save()
            response_serializer = GrievanceDetailSerializer(grievance)
            return Response(
                {
                    'message': 'Grievance submitted successfully',
                    'grievance': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        # Use utility to format errors to {error: "message"}
        error_msg = get_first_serializer_error(serializer.errors)
        return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)


class GrievanceDetailView(APIView):
    """
    GET: Retrieve a single grievance
    PATCH: Update grievance status/priority (college/university staff only)
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, identifier, user):
        """Get grievance by ID or grievance_number with permission check"""
        try:
            if identifier.isdigit():
                grievance = Grievance.objects.get(id=identifier)
            else:
                grievance = Grievance.objects.get(grievance_number=identifier)
        except Grievance.DoesNotExist:
            return None
        
        # Check permissions
        if user.user_type == 'student':
            if grievance.user != user:
                return None
        elif user.user_type == 'college_user':
            college = user.get_college()
            if not college or grievance.assigned_to_college != college:
                return None
        # University admin can see all
        
        return grievance

    @swagger_auto_schema(
        operation_description="Get grievance details by ID or grievance number",
        responses={200: GrievanceDetailSerializer, 404: 'Grievance not found'},
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def get(self, request, identifier):
        """Retrieve grievance details"""
        grievance = self.get_object(identifier, request.user)
        if not grievance:
            return Response(
                {'error': 'Grievance not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = GrievanceDetailSerializer(grievance, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="""Update grievance status or assign to staff member.
        
        **Examples:**
        
        Update status only:
        ```json
        {"status": "in_progress"}
        ```
        
        Assign to staff member:
        ```json
        {"handled_by_uid": "abc-123-def-456"}
        ```
        
        Update multiple fields:
        ```json
        {
          "status": "in_progress",
          "handled_by_uid": "abc-123-def-456"
        }
        ```
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Update grievance status',
                    enum=['open', 'in_progress', 'resolved', 'closed', 'escalated']
                ),
                'handled_by_uid': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='uuid',
                    description='UID of staff member to assign (use null to unassign)',
                    nullable=True
                ),
            },
            example={
                'status': 'in_progress',
                'handled_by_uid': 'abc-123-def-456'
            }
        ),
        responses={
            200: GrievanceDetailSerializer,
            400: 'Validation error',
            403: 'Permission denied',
            404: 'Grievance not found'
        },
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def patch(self, request, identifier):
        """Update grievance (college/university staff only)"""
        if request.user.user_type not in ['college_user', 'university_admin']:
            return Response(
                {'error': 'Only college/university staff can update grievances'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        grievance = self.get_object(identifier, request.user)
        if not grievance:
            return Response(
                {'error': 'Grievance not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = GrievanceUpdateSerializer(
            grievance,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            response_serializer = GrievanceDetailSerializer(grievance)
            return Response(
                {
                    'message': 'Grievance updated successfully',
                    'grievance': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        # Use utility to format errors to {error: "message"}
        error_msg = get_first_serializer_error(serializer.errors)
        return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)



class GrievanceCommentListView(APIView):
    """
    GET: Get all comments for a specific grievance (Staff only).
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all comments for a specific grievance (Staff only).",
        responses={200: GrievanceCommentSerializer(many=True), 404: 'Grievance not found', 403: 'Permission denied'},
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def get(self, request, identifier):
        """Get all comments for a specific grievance"""
        # Get grievance
        try:
            if identifier.isdigit():
                grievance = Grievance.objects.get(id=identifier)
            else:
                grievance = Grievance.objects.get(grievance_number=identifier)
        except Grievance.DoesNotExist:
            return Response(
                {'error': 'Grievance not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - Students cannot see comments
        user = request.user
        if user.user_type == 'student':
            return Response(
                {'error': 'Access denied. Students cannot view comments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif user.user_type == 'college_user':
            college = user.get_college()
            if not college or grievance.assigned_to_college != college:
                return Response(
                    {'error': 'You can only view comments for grievances assigned to your college'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        comments = grievance.comments.all().order_by('created_at')
        serializer = GrievanceCommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GrievanceCommentCreateView(APIView):
    """
    POST: Add a comment to a grievance or update its status/assignment
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""Add a comment to a grievance or update its status/assignment.
        
        **Functional details:**
        - Comment is mandatory IF no status/assignment changes are provided.
        - If status or assignment changes are provided, the comment is optional.
        - All status/assignment changes are automatically logged as comments.
        
        **Workflow:**
        1. Upload attachments using `/api/grievances/upload-attachment/` (optional)
        2. Collect the attachment UIDs from upload responses
        3. Submit comment/update with attachment UIDs
        
        **Example (Comment only):**
        ```json
        {
          "comment": "Please look into this",
          "is_internal": false
        }
        ```
        
        **Example (Status & Assignment Update):**
        ```json
        {
          "new_status": "in_progress",
          "is_assigned_to_university": true,
          "is_assigned_to_college": false,
          "comment": "Moving this to university level"
        }
        ```
        """,
        request_body=GrievanceCommentCreateSerializer,
        responses={
            201: GrievanceCommentSerializer, 
            400: 'Validation error',
            403: 'Permission denied'
        },
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def post(self, request, identifier):
        """Add comment to grievance with optional attachments"""
        # Get grievance
        try:
            if identifier.isdigit():
                grievance = Grievance.objects.get(id=identifier)
            else:
                grievance = Grievance.objects.get(grievance_number=identifier)
        except Grievance.DoesNotExist:
            return Response(
                {'error': 'Grievance not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        user = request.user
        if user.user_type == 'student':
            return Response(
                {'error': 'Students cannot add comments. Please submit a new grievance for updates.'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif user.user_type == 'college_user':
            college = user.get_college()
            if not college or grievance.assigned_to_college != college:
                return Response(
                    {'error': 'You can only comment on grievances assigned to your college'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Create comment with attachments
        serializer = GrievanceCommentCreateSerializer(
            data=request.data,
            context={
                'request': request,
                'grievance': grievance
            }
        )
        
        if serializer.is_valid():
            comment = serializer.save(grievance=grievance)
            response_serializer = GrievanceCommentSerializer(
                comment,
                context={'request': request}
            )
            return Response(
                {
                    'message': 'Comment added successfully',
                    'comment': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        # Use utility to format errors to {error: "message"}
        error_msg = get_first_serializer_error(serializer.errors)
        return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

class GrievanceStatsView(APIView):
    """
    GET: Get grievance statistics
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get grievance statistics based on user role",
        responses={200: 'Statistics data'},
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        """Get grievance statistics"""
        from django.db.models import Count
        
        user = request.user
        
        # Filter based on user type (exclude deleted)
        if user.user_type == 'student':
            queryset = Grievance.objects.filter(user=user, is_deleted=False)
        elif user.user_type == 'college_user':
            college = user.get_college()
            if not college:
                return Response({'error': 'College association not found'}, status=status.HTTP_404_NOT_FOUND)
            queryset = Grievance.objects.filter(assigned_to_college=college, is_deleted=False)
        else:
            queryset = Grievance.objects.filter(is_deleted=False)
        
        # Calculate stats
        total_grievances = queryset.count()
        by_status = queryset.values('status').annotate(count=Count('id'))
        by_category = queryset.values('category').annotate(count=Count('id'))
        
        return Response(
            {
                'total_grievances': total_grievances,
                'by_status': list(by_status),
                'by_category': list(by_category),
            },
            status=status.HTTP_200_OK
        )

class GrievanceCategoryListView(APIView):
    """
    GET: List all active grievance categories
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get list of all active grievance categories for dropdown/selection",
        responses={200: 'List of categories'},
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        """List all active categories"""
        from .models import GrievanceCategory
        from .serializers import GrievanceCategorySerializer
        
        categories = GrievanceCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        serializer = GrievanceCategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GrievanceAttachmentUploadView(APIView):
    """
    POST: Upload attachment before creating grievance
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="""Upload attachment file before creating grievance.
        
        Returns attachment UID which can be used when creating the grievance.
        
        **Usage:**
        1. Upload files using this endpoint
        2. Collect the returned UIDs
        3. Pass the UIDs array when creating the grievance
        """,
        request_body=GrievanceAttachmentUploadSerializer,
        responses={
            201: GrievanceAttachmentSerializer,
            400: 'Validation error'
        },
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        """Upload attachment"""
        serializer = GrievanceAttachmentUploadSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            attachment = serializer.save()
            # Return full attachment details including UID
            response_serializer = GrievanceAttachmentSerializer(attachment, context={'request': request})
            return Response(
                {
                    'message': 'Attachment uploaded successfully',
                    'attachment': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        # Use utility to format errors to {error: "message"}
        error_msg = get_first_serializer_error(serializer.errors)
        return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
