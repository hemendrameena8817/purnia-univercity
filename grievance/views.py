from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import timedelta, datetime
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from decouple import config
import uuid

from .models import Grievance, GrievanceComment, GrievancePayment, GrievanceSubCategory
from .serializers import (
    GrievanceListSerializer,
    GrievanceDetailSerializer,
    GrievanceCreateSerializer,
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
                'is_assigned_to_university',
                openapi.IN_QUERY,
                description="Filter by university assignment status (true/false)",
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'is_assigned_to_college',
                openapi.IN_QUERY,
                description="Filter by college assignment status (true/false)",
                type=openapi.TYPE_BOOLEAN
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
            openapi.Parameter(
                'time_filter',
                openapi.IN_QUERY,
                description="Quick time filters",
                type=openapi.TYPE_STRING,
                enum=['last_7_days', 'older_than_7_days', 'older_than_month']
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Filter by specific date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Filter by start date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="Filter by end date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'is_payment_completed',
                openapi.IN_QUERY,
                description="Filter by payment completion status (true/false)",
                type=openapi.TYPE_BOOLEAN
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
            # Students see only their own grievances with completed payment
            queryset = Grievance.objects.filter(user=user, is_deleted=False, is_payment_completed=True)
        
        elif user.user_type == 'college_user':
            # College staff see grievances assigned to their college AND currently at college level with completed payment
            college = user.get_college()
            if not college:
                return Response(
                    {'error': 'College association not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            queryset = Grievance.objects.filter(
                assigned_to_college=college, 
                is_assigned_to_college=True,
                is_deleted=False,
                is_payment_completed=True
            )
        
        elif user.user_type == 'university_admin':
            # University admin sees all grievances with completed payment (excluding deleted)
            queryset = Grievance.objects.filter(is_deleted=False, is_payment_completed=True)
            
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

        is_assigned_to_university_filter = request.query_params.get('is_assigned_to_university')
        if is_assigned_to_university_filter is not None:
            val = is_assigned_to_university_filter.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_assigned_to_university=val)

        is_assigned_to_college_filter = request.query_params.get('is_assigned_to_college')
        if is_assigned_to_college_filter is not None:
            val = is_assigned_to_college_filter.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_assigned_to_college=val)

        is_payment_completed_filter = request.query_params.get('is_payment_completed')
        if is_payment_completed_filter is not None:
            val = is_payment_completed_filter.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_payment_completed=val)

        # University Admin can filter by specific college
        college_filter = request.query_params.get('college')
        if college_filter and user.user_type == 'university_admin':
            queryset = queryset.filter(assigned_to_college__uid=college_filter)
        
        # --- Time-based Filters ---
        time_filter = request.query_params.get('time_filter')
        now = timezone.now()
        
        if time_filter == 'last_7_days':
            seven_days_ago = now - timedelta(days=7)
            queryset = queryset.filter(submitted_at__gte=seven_days_ago)
        elif time_filter == 'older_than_7_days':
            seven_days_ago = now - timedelta(days=7)
            queryset = queryset.filter(submitted_at__lt=seven_days_ago)
        elif time_filter == 'older_than_month':
            one_month_ago = now - timedelta(days=30)
            queryset = queryset.filter(submitted_at__lt=one_month_ago)
            
        # Date-wise filters
        date_str = request.query_params.get('date')
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(submitted_at__date=filter_date)
            except ValueError:
                pass # Or return 400
                
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(submitted_at__date__gte=start_date)
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(submitted_at__date__lte=end_date)
            except ValueError:
                pass
        
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


class GrievancePaymentInitiateView(APIView):
    """
    POST: Initiate payment for grievance submission
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""Initiate payment for grievance submission.
        
        **Payment Flow:**
        1. Student creates a grievance draft (without payment)
        2. Student initiates payment using grievance UID
        3. Payment gateway processes payment
        4. On success, grievance number is generated and grievance is activated
        
        **Fixed Amount:** ₹100.00
        """,
        responses={
            200: openapi.Response(
                description="Payment initiated successfully",
                examples={
                    'application/json': {
                        'order_id': 'GRV_ABC123456789',
                        'enc_request': 'encrypted_data_string',
                        'access_code': 'AVXXX',
                        'production_url': 'https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction'
                    }
                }
            ),
            400: 'Bad request',
            404: 'Grievance not found'
        },
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def post(self, request, grievance_uid):
        """Initiate payment for grievance"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            grievance = Grievance.objects.select_related('category', 'assigned_to_college').get(
                uid=grievance_uid, 
                is_deleted=False
            )
        except Grievance.DoesNotExist:
            return Response({"error": "Grievance not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if user owns this grievance
        if grievance.user != request.user:
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

        # Check if payment already completed
        if grievance.is_payment_completed:
            return Response({"error": "Payment already completed for this grievance"}, status=status.HTTP_400_BAD_REQUEST)

        # Fixed amount
        amount = str(grievance.payment_amount)

        # Configuration
        merchant_id = config('CCAVENUE_MERCHANT_ID', default='')
        access_code = config('CCAVENUE_ACCESS_CODE', default='')
        working_key = config('CCAVENUE_WORKING_KEY', default='')
        redirect_url = config('CCAVENUE_REDIRECT_URL', default=f"{request.scheme}://{request.get_host()}/api/grievances/payment-response/")
        cancel_url = redirect_url
        
        order_id = f"GRV_{uuid.uuid4().hex[:12].upper()}"
        
        # Create payment record
        GrievancePayment.objects.create(
            grievance=grievance,
            order_id=order_id,
            amount=amount,
            payment_status='PENDING'
        )

        # Prepare payload for CC Avenue
        merchant_data = (
            f"merchant_id={merchant_id}&order_id={order_id}&"
            f"amount={amount}&currency=INR&"
            f"redirect_url={redirect_url}&cancel_url={cancel_url}&"
            f"language=EN&billing_name={grievance.contact_person_name or request.user.get_full_name()}&"
            f"billing_tel={grievance.contact_person_phone_number or ''}&"
            f"billing_email={request.user.email or ''}"
        )

        # Import encryption utility from voc_new_registration
        from voc_new_registration.utils.ccavenue_utils import encrypt
        encrypted_data = encrypt(merchant_data, working_key)
        
        ccavenue_url = config('CCAVENUE_URL', default='https://secure.ccavenue.com/transaction/transaction.do?command=initiateTransaction')
        
        logger.info(f"Payment initiated for grievance {grievance_uid}, order_id: {order_id}")
        
        return Response({
            "order_id": order_id,
            "enc_request": encrypted_data,
            "access_code": access_code,
            "production_url": ccavenue_url,
            "payment_details": {
                "amount": amount,
                "currency": "INR",
                "description": f"Grievance Payment - {grievance.subject}",
                "grievance_uid": str(grievance.uid),
                "grievance_subject": grievance.subject,
                "contact_person": grievance.contact_person_name
            }
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class GrievancePaymentResponseView(APIView):
    """
    POST: Handle CC Avenue payment response for grievance
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Grievance payment response received. Data: {request.data}")
        logger.info(f"Request headers: {request.headers}")
        
        # Check if this is a form submission or direct POST
        if request.content_type == 'application/x-www-form-urlencoded':
            enc_response = request.POST.get('encResp')
        else:
            enc_response = request.data.get('encResp')
            
        logger.info(f"Encrypted response: {enc_response}")
            
        if not enc_response:
            logger.error("No encResp parameter found in request")
            return Response(
                {"error": "Invalid response: Missing encResp parameter"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            working_key = config('CCAVENUE_WORKING_KEY')
            if not working_key:
                raise ValueError("CCAVENUE_WORKING_KEY not configured")
                
            logger.info(f"Decrypting response with working key")
            
            # Import decryption utilities from voc_new_registration
            from voc_new_registration.utils.ccavenue_utils import decrypt, parse_response
            decrypted_response = decrypt(enc_response, working_key)
            response_data = parse_response(decrypted_response)
            logger.info(f"Decrypted response data: {response_data}")
            
            order_id = response_data.get('order_id')
            auth_status = response_data.get('order_status', '').lower()
            
            if not order_id:
                raise ValueError("No order_id in decrypted response")
                
            logger.info(f"Processing payment for order_id: {order_id}, status: {auth_status}")
            
            try:
                payment = GrievancePayment.objects.select_related(
                    'grievance',
                    'grievance__category',
                    'grievance__assigned_to_college'
                ).get(order_id=order_id)
            except GrievancePayment.DoesNotExist:
                logger.error(f"Payment record not found for order_id: {order_id}")
                return Response(
                    {"error": "Payment record not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update payment details
            payment.tracking_id = response_data.get('tracking_id')
            payment.bank_ref_no = response_data.get('bank_ref_no')
            payment.payment_mode = response_data.get('payment_mode')
            payment.raw_response = response_data
            
            # Handle different payment statuses
            if auth_status == 'success':
                payment.payment_status = 'SUCCESS'
                grievance = payment.grievance
                
                try:
                    # Mark payment as completed and generate grievance number
                    grievance.is_payment_completed = True
                    grievance.save()  # This will trigger grievance_number generation in model's save method
                    
                    logger.info(f"Successfully generated grievance number: {grievance.grievance_number} for UID: {grievance.uid}")
                    
                except Exception as e:
                    logger.error(f"Error updating grievance: {str(e)}")
                    payment.payment_status = 'PENDING'
                    payment.save()
                    raise
                    
            elif auth_status == 'aborted':
                payment.payment_status = 'ABORTED'
                logger.info(f"Payment aborted for order_id: {order_id}")
            else:
                payment.payment_status = 'FAILED'
                logger.warning(f"Payment failed for order_id: {order_id}. Status: {auth_status}")
            
            payment.save()
            logger.info(f"Payment {payment.payment_status} for order_id: {order_id}")

            # Redirect to Frontend with all necessary parameters
            frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
            
            if hasattr(payment, 'grievance') and hasattr(payment.grievance, 'uid'):
                uid = str(payment.grievance.uid)
                
                redirect_url = (
                    f"{frontend_url}/grievance/status"
                    f"?uid={uid}"
                    f"&payment_status={payment.payment_status.lower()}"
                    f"&order_id={order_id}"
                )
                if payment.payment_status == 'SUCCESS' and payment.grievance.grievance_number:
                    redirect_url += f"&grievance_number={payment.grievance.grievance_number}"
            else:
                logger.error(f"Grievance or UID not found for payment {payment.id}")
                redirect_url = f"{frontend_url}/grievances/payment-status?error=grievance_not_found"

            logger.info(f"Redirecting to: {redirect_url}")
            return redirect(redirect_url)
            
        except Exception as e:
            logger.exception("Error processing grievance payment response")
            # Still redirect to frontend but with error status
            frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
            error_redirect = f"{frontend_url}/grievances/payment-status?error={str(e)[:100]}"
            return redirect(error_redirect)


class GrievanceStatusByUIDView(APIView):
    """
    GET: Retrieve grievance details by UID for payment status page
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="""Get grievance details by UID for payment status page.
        
        Returns complete grievance information including:
        - Grievance number (if payment completed)
        - Payment status and amount
        - Category, subject, description
        - Submission details
        
        **Use Case:** After payment redirect, frontend calls this endpoint with UID to display status.
        """,
        manual_parameters=[
            openapi.Parameter(
                'uid',
                openapi.IN_QUERY,
                description="Grievance UID (UUID)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Grievance details retrieved successfully",
                examples={
                    'application/json': {
                        'uid': 'abc-123-def-456',
                        'grievance_number': 'GRV000001',
                        'is_payment_completed': True,
                        'payment_amount': '100.00',
                        'payment_status': 'SUCCESS',
                        'category': 'Fee & Payment Issues',
                        'subject': 'My Issue',
                        'description': 'Details...',
                        'contact_person_name': 'John Doe',
                        'contact_person_phone_number': '9876543210',
                        'status': 'open',
                        'submitted_at': '2026-03-13T09:45:00Z',
                        'college_name': 'ABC College'
                    }
                }
            ),
            400: 'UID parameter required',
            404: 'Grievance not found'
        },
        tags=['Grievances']
    )
    def get(self, request):
        """Get grievance details by UID"""
        uid = request.query_params.get('uid')
        
        if not uid:
            return Response(
                {'error': 'UID parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            grievance = Grievance.objects.select_related(
                'category',
                'assigned_to_college',
                'user'
            ).prefetch_related('payments').get(uid=uid, is_deleted=False)
        except Grievance.DoesNotExist:
            return Response(
                {'error': 'Grievance not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get latest payment info
        latest_payment = grievance.payments.order_by('-created_at').first()
        
        response_data = {
            'uid': str(grievance.uid),
            'grievance_number': grievance.grievance_number,
            'is_payment_completed': grievance.is_payment_completed,
            'payment_amount': str(grievance.payment_amount),
            'category': grievance.category.name if grievance.category else None,
            'category_code': grievance.category.code if grievance.category else None,
            'subject': grievance.subject,
            'description': grievance.description,
            'contact_person_name': grievance.contact_person_name,
            'contact_person_phone_number': grievance.contact_person_phone_number,
            'status': grievance.status,
            'status_display': grievance.get_status_display(),
            'is_grievance_resolved': grievance.is_grievance_resolved,
            'submitted_at': grievance.submitted_at,
            'college_name': grievance.assigned_to_college.name if grievance.assigned_to_college else None,
            'college_code': grievance.assigned_to_college.college_code if grievance.assigned_to_college else None,
        }
        
        # Add payment details if exists
        if latest_payment:
            response_data['payment'] = {
                'order_id': latest_payment.order_id,
                'payment_status': latest_payment.payment_status,
                'tracking_id': latest_payment.tracking_id,
                'payment_mode': latest_payment.payment_mode,
                'amount': str(latest_payment.amount),
                'created_at': latest_payment.created_at,
            }
        else:
            response_data['payment'] = None
        
        return Response(response_data, status=status.HTTP_200_OK)


class GrievanceSubCategoriesByCategoryView(APIView):
    """
    GET: Retrieve subcategories for a specific category
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="""Get all active subcategories for a specific category.
        
        Returns list of subcategories with UID, name, code, and description.
        
        **Use Case:** Frontend calls this after user selects a category to show subcategory options.
        """,
        manual_parameters=[
            openapi.Parameter(
                'category_uid',
                openapi.IN_QUERY,
                description="Category UID (UUID)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Subcategories retrieved successfully",
                examples={
                    'application/json': {
                        'subcategories': [
                            {
                                'uid': 'abc-123-def-456',
                                'name': 'Marksheet Correction',
                                'code': 'marksheet_correction',
                                'description': 'Name spelling errors, incorrect subject marks...',
                                'display_order': 1
                            }
                        ]
                    }
                }
            ),
            400: 'Category UID parameter required',
            404: 'Category not found'
        },
        tags=['Grievances'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        """Get subcategories by category UID"""
        category_uid = request.query_params.get('category_uid')
        
        if not category_uid:
            return Response(
                {'error': 'Category UID parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            category = GrievanceCategory.objects.get(uid=category_uid, is_active=True)
        except GrievanceCategory.DoesNotExist:
            return Response(
                {'error': 'Category not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        subcategories = GrievanceSubCategory.objects.filter(
            category=category,
            is_active=True
        ).order_by('display_order', 'name')
        
        subcategory_data = []
        for subcat in subcategories:
            subcategory_data.append({
                'uid': str(subcat.uid),
                'name': subcat.name,
                'code': subcat.code,
                'description': subcat.description,
                'price': float(subcat.price),
                'display_order': subcat.display_order
            })
        
        return Response({
            'category': {
                'uid': str(category.uid),
                'name': category.name,
                'code': category.code
            },
            'subcategories': subcategory_data
        }, status=status.HTTP_200_OK)
