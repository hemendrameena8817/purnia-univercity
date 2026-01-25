from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q, Count

from .models import VocNewRegistration
from .serializers import (
    VocNewRegistrationGetSerializer,
    VocNewRegistrationListSerializer,
    VocNewRegistrationCreateSerializer,
    VocNewRegistrationUpdateSerializer,
)
from rest_framework.parsers import MultiPartParser, FormParser

from decouple import config
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import uuid
from .utils.ccavenue_utils import encrypt, decrypt, parse_response
from .models import VocNewRegistration, VocRegistrationPayment


class VocNewRegistrationListView(generics.ListAPIView):
    """
    API View to list all VOC new registrations.
    Supports search and filtering.
    """
    serializer_class = VocNewRegistrationListSerializer
    
    def get_queryset(self):
        # Only list records that are not soft-deleted
        queryset = VocNewRegistration.objects.filter(is_deleted=False).select_related('college')
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(student_name__icontains=search) |
                Q(father_name__icontains=search) |
                Q(mother_name__icontains=search)
            )
        
        # Filtering
        course = self.request.query_params.get('course', None)
        if course:
            queryset = queryset.filter(course__iexact=course)
        
        gender = self.request.query_params.get('gender', None)
        if gender:
            queryset = queryset.filter(gender=gender.upper())
        
        caste = self.request.query_params.get('caste', None)
        if caste:
            queryset = queryset.filter(caste=caste.upper())
        
        college = self.request.query_params.get('college', None)
        if college:
            queryset = queryset.filter(college__uid=college)
            
        return queryset

    @swagger_auto_schema(
        operation_summary="List all VOC new registrations",
        operation_description="Retrieve a list of all VOC new registration entries with pagination support",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description="Search by name", type=openapi.TYPE_STRING),
            openapi.Parameter('course', openapi.IN_QUERY, description="Filter by course", type=openapi.TYPE_STRING),
            openapi.Parameter('gender', openapi.IN_QUERY, description="Filter by gender", type=openapi.TYPE_STRING),
            openapi.Parameter('caste', openapi.IN_QUERY, description="Filter by caste", type=openapi.TYPE_STRING),
            openapi.Parameter('college', openapi.IN_QUERY, description="Filter by college UID", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VocNewRegistrationCreateView(generics.CreateAPIView):
    """
    API View to create a new VOC registration.
    """
    queryset = VocNewRegistration.objects.all()
    serializer_class = VocNewRegistrationCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Create a new VOC registration",
        operation_description="Create a new VOC registration entry."
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class VocNewRegistrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update or delete a specific registration.
    Lookup by Aadhaar Number.
    Supports multipart/form-data for image updates.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = (MultiPartParser, FormParser)
    lookup_field = 'aadhaar_no'
    lookup_url_kwarg = 'aadhaar_no'

    def get_queryset(self):
        # Prevent accessing soft-deleted records via detail view
        return VocNewRegistration.objects.filter(is_deleted=False).select_related('college')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return VocNewRegistrationUpdateSerializer
        return VocNewRegistrationGetSerializer

    @swagger_auto_schema(
        operation_summary="Retrieve a specific VOC registration",
        operation_description="Lookup by Aadhaar number."
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a VOC registration",
        operation_description="Updates registration data. Supports multipart/form-data for image uploads."
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Full update a VOC registration",
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Soft delete a VOC registration")
    def delete(self, request, *args, **kwargs):
        """Perform soft delete by setting is_deleted=True"""
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(
            {"message": "Registration soft-deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


class VocRegistrationStatusView(views.APIView):
    """
    API View to check the registration status of a student.
    Lookup by Aadhaar Number.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Check registration status",
        operation_description="Returns whether registration is completed, account created, and migration status."
    )
    def get(self, request, aadhaar_no):
        try:
            registration = VocNewRegistration.objects.get(aadhaar_no=aadhaar_no, is_deleted=False)
        except VocNewRegistration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get latest payment status if it exists
        latest_payment = registration.payments.order_by('-created_at').first()
        payment_status = latest_payment.payment_status if latest_payment else None

        return Response({
            "uid": registration.uid,
            "student_name": registration.student_name,
            "is_registration_completed": registration.is_registration_completed,
            "is_account_created": registration.is_account_created,
            "migrated_from_other_university": registration.migrated_from_other_university,
            "latest_payment_status": payment_status,
            "aadhaar_no": registration.aadhaar_no
        }, status=status.HTTP_200_OK)


class VocNewRegistrationBulkCreateView(views.APIView):
    """
    API View for bulk creation of registrations.
    """
    permission_classes = [permissions.AllowAny]
    @swagger_auto_schema(
        operation_summary="Bulk create VOC registrations",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'registrations': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT) 
                )
            }
        ),
        responses={201: "Created", 400: "Bad Request"}
    )
    def post(self, request):
        registrations_data = request.data.get('registrations', [])
        
        if not isinstance(registrations_data, list):
            return Response(
                {'error': 'registrations must be an array'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created = []
        errors = []
        
        for idx, registration_data in enumerate(registrations_data):
            serializer = VocNewRegistrationCreateSerializer(data=registration_data)
            if serializer.is_valid():
                try:
                    instance = serializer.save()
                    created.append(instance)
                except Exception as e:
                    errors.append({
                        'index': idx,
                        'data': registration_data,
                        'error': str(e)
                    })
            else:
                errors.append({
                    'index': idx,
                    'data': registration_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'success': len(created),
            'failed': len(errors),
            'errors': errors
        }, status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST)


class InitiatePaymentView(views.APIView):
    """
    API View to initiate CC Avenue payment.
    Requires migrated_from_other_university to be True.
    """
    permission_classes = [permissions.AllowAny]

    VOC_REGISTRATION_FEE=500.00

    @swagger_auto_schema(
        operation_summary="Initiate CC Avenue payment",
        responses={200: "Redirect Data"}
    )
    def post(self, request, aadhaar_no):
        try:
            registration = VocNewRegistration.objects.get(aadhaar_no=aadhaar_no, is_deleted=False)
        except VocNewRegistration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

        if not registration.migrated_from_other_university:
            return Response({"error": "Payment only required for migrated students"}, status=status.HTTP_400_BAD_USER)

        if registration.is_registration_completed:
            return Response({"error": "Registration already completed"}, status=status.HTTP_400_BAD_REQUST)

        # Configuration (should be in .env)
        merchant_id = config('CCAVENUE_MERCHANT_ID', default='')
        access_code = config('CCAVENUE_ACCESS_CODE', default='')
        working_key = config('CCAVENUE_WORKING_KEY', default='')
        redirect_url = config('CCAVENUE_REDIRECT_URL', default=f"{request.scheme}://{request.get_host()}/api/voc_new_registration/payment-response/")
        cancel_url = redirect_url
        amount = config('VOC_REGISTRATION_FEE', default=str(self.VOC_REGISTRATION_FEE))

        order_id = f"REG_{uuid.uuid4().hex[:12].upper()}"
        
        # Create payment record
        VocRegistrationPayment.objects.create(
            registration=registration,
            order_id=order_id,
            amount=amount,
            payment_status='PENDING'
        )

        # Prepare payload for CC Avenue
        merchant_data = (
            f"merchant_id={merchant_id}&order_id={order_id}&"
            f"amount={amount}&currency=INR&"
            f"redirect_url={redirect_url}&cancel_url={cancel_url}&"
            f"language=EN&billing_name={registration.student_name}&"
            f"billing_tel={registration.mobile_no or ''}&"
            f"billing_email={registration.email or ''}"
        )

        encrypted_data = encrypt(merchant_data, working_key)
        
        return Response({
            "enc_request": encrypted_data,
            "access_code": access_code,
            "production_url": "https://secure.ccavenue.com/transaction/transaction.do?command=initiateTransaction"
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentResponseView(views.APIView):
    """
    API View to handle CC Avenue payment response.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        enc_response = request.data.get('encResp')
        if not enc_response:
            return Response({"error": "Invalid response"}, status=status.HTTP_400_BAD_REQUEST)

        working_key = config('CCAVENUE_WORKING_KEY', default='')
        decrypted_response = decrypt(enc_response, working_key)
        response_data = parse_response(decrypted_response)

        order_id = response_data.get('order_id')
        auth_status = response_data.get('order_status')

        try:
            payment = VocRegistrationPayment.objects.get(order_id=order_id)
        except VocRegistrationPayment.DoesNotExist:
            return Response({"error": "Payment record not found"}, status=status.HTTP_404_NOT_FOUND)

        payment.tracking_id = response_data.get('tracking_id')
        payment.bank_ref_no = response_data.get('bank_ref_no')
        payment.payment_mode = response_data.get('payment_mode')
        payment.raw_response = response_data
        
        if auth_status == 'Success':
            payment.payment_status = 'SUCCESS'
            # Complete registration
            reg = payment.registration
            reg.is_registration_completed = True
            reg.save()
        elif auth_status == 'Aborted':
            payment.payment_status = 'ABORTED'
        else:
            payment.payment_status = 'FAILED'
        
        payment.save()

        # In a real app, you might redirect to a frontend success/fail page
        return Response({
            "status": payment.payment_status,
            "order_id": order_id
        }, status=status.HTTP_200_OK)


class VocRegistrationOptionsView(views.APIView):
    """
    API View to fetch gender and caste choices for VocNewRegistration.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Fetch gender and caste options",
        responses={
            200: openapi.Response(
                description="List of choices for gender and caste",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'gender': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'value': openapi.Schema(type=openapi.TYPE_STRING),
                                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                        'caste': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'value': openapi.Schema(type=openapi.TYPE_STRING),
                                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                    }
                )
            )
        }
    )
    def get(self, request):
        gender_choices = [
            {'value': code, 'label': label} for code, label in VocNewRegistration.GENDER_CHOICES
        ]
        caste_choices = [
            {'value': code, 'label': label} for code, label in VocNewRegistration.CASTE_CHOICES
        ]
        return Response({
            'gender': gender_choices,
            'caste': caste_choices
        }, status=status.HTTP_200_OK)
