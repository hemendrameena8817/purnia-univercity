from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from django.shortcuts import redirect
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q, Count

from .models import (
    NewRegistration, 
    RegistrationPayment,
    NewRegistrationCourse,
    NewRegistrationBatch,
    NewRegistrationSession
)
from .utils.registration_logic import generate_registration_number
from .serializers import (
    CourseMinimalSerializer,
    BatchMinimalSerializer,
    SessionMinimalSerializer,
    NewRegistrationGetSerializer,
    NewRegistrationListSerializer,
    NewRegistrationCreateSerializer,
    NewRegistrationUpdateSerializer,
    RegistrationPaymentSerializer,
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from decouple import config
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import uuid
from .utils.ccavenue_utils import encrypt, decrypt, parse_response
from .utils.ccavenue_utils import encrypt, decrypt, parse_response


class NewRegistrationListView(generics.ListAPIView):
    """
    API View to list all new registrations.
    Supports search and filtering.
    """
    serializer_class = NewRegistrationListSerializer
    
    def get_queryset(self):
        # Only list records that are not soft-deleted
        queryset = NewRegistration.objects.filter(is_deleted=False).select_related('college', 'course', 'batch', 'session')
        
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
            queryset = queryset.filter(course__uid=course)
        
        batch = self.request.query_params.get('batch', None)
        if batch:
            queryset = queryset.filter(batch__uid=batch)
            
        session = self.request.query_params.get('session', None)
        if session:
            queryset = queryset.filter(session__uid=session)
        
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
        operation_summary="List all new registrations",
        operation_description="Retrieve a list of all new registration entries with pagination support",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description="Search by name", type=openapi.TYPE_STRING),
            openapi.Parameter('course', openapi.IN_QUERY, description="Filter by course UID", type=openapi.TYPE_STRING),
            openapi.Parameter('batch', openapi.IN_QUERY, description="Filter by batch UID", type=openapi.TYPE_STRING),
            openapi.Parameter('session', openapi.IN_QUERY, description="Filter by session UID", type=openapi.TYPE_STRING),
            openapi.Parameter('gender', openapi.IN_QUERY, description="Filter by gender", type=openapi.TYPE_STRING),
            openapi.Parameter('caste', openapi.IN_QUERY, description="Filter by caste", type=openapi.TYPE_STRING),
            openapi.Parameter('college', openapi.IN_QUERY, description="Filter by college UID", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class NewRegistrationCreateView(generics.CreateAPIView):
    """
    API View to create a new registration.
    """
    queryset = NewRegistration.objects.all()
    serializer_class = NewRegistrationCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Create a new registration",
        operation_description="Create a new registration entry."
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class NewRegistrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update or delete a specific registration.
    Lookup by Aadhaar Number.
    Supports multipart/form-data for image updates.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    lookup_field = 'aadhaar_no'
    lookup_url_kwarg = 'aadhaar_no'

    def get_queryset(self):
        # Prevent accessing soft-deleted records via detail view
        return NewRegistration.objects.filter(is_deleted=False).select_related('college', 'course', 'batch', 'session')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return NewRegistrationUpdateSerializer
        return NewRegistrationGetSerializer

    @swagger_auto_schema(
        operation_summary="Retrieve a specific registration",
        operation_description="Lookup by Aadhaar number. Requires captcha validation.",
        manual_parameters=[
            openapi.Parameter('captcha_key', openapi.IN_QUERY, description="Captcha Hash Key", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('captcha_value', openapi.IN_QUERY, description="Solved Captcha Text", type=openapi.TYPE_STRING, required=True),
        ]
    )
    def get(self, request, *args, **kwargs):
        captcha_key = request.query_params.get('captcha_key')
        captcha_value = request.query_params.get('captcha_value')
        
        if not captcha_key or not captcha_value:
            return Response({"error": "Captcha required for security"}, status=status.HTTP_400_BAD_REQUEST)
        
        from captcha.models import CaptchaStore
        try:
            CaptchaStore.objects.get(hashkey=captcha_key, response=captcha_value.lower()).delete()
        except CaptchaStore.DoesNotExist:
            return Response({"error": "Invalid or expired captcha"}, status=status.HTTP_400_BAD_REQUEST)
        
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a registration",
        operation_description="Updates registration data. Supports multipart/form-data for image uploads."
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Full update a registration",
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Soft delete a registration",
        manual_parameters=[
            openapi.Parameter('captcha_key', openapi.IN_QUERY, description="Captcha Hash Key", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('captcha_value', openapi.IN_QUERY, description="Solved Captcha Text", type=openapi.TYPE_STRING, required=True),
        ]
    )
    def delete(self, request, *args, **kwargs):
        """Perform soft delete by setting is_deleted=True. Requires captcha."""
        captcha_key = request.query_params.get('captcha_key')
        captcha_value = request.query_params.get('captcha_value')
        
        if not captcha_key or not captcha_value:
            return Response({"error": "Captcha required for security"}, status=status.HTTP_400_BAD_REQUEST)
        
        from captcha.models import CaptchaStore
        try:
            CaptchaStore.objects.get(hashkey=captcha_key, response=captcha_value.lower()).delete()
        except CaptchaStore.DoesNotExist:
            return Response({"error": "Invalid or expired captcha"}, status=status.HTTP_400_BAD_REQUEST)

        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(
            {"message": "Registration soft-deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


class RegistrationStatusView(views.APIView):
    """
    API View to check the registration status of a student.
    Lookup by UID.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Check registration status",
        operation_description="Returns whether registration is completed, account created, and migration status."
    )
    def get(self, request, uid):
        try:
            registration = NewRegistration.objects.get(uid=uid, is_deleted=False)
        except (NewRegistration.DoesNotExist, ValueError):
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get latest payment status if it exists
        latest_payment = registration.payments.order_by('-created_at').first()
        payment_status = latest_payment.payment_status if latest_payment else None

        if not registration.registration_number and registration.is_registration_completed:
            try:
                if not registration.migrated_from_other_university:
                    if registration.old_registration_no:
                        registration.registration_number = registration.old_registration_no
                        registration.save()
                else:
                    registration.registration_number = generate_registration_number(registration)
                    registration.save()
            except Exception as e:
                # Log error but don't block the status return
                print(f"Error generating registration number in StatusView: {str(e)}")

        return Response({
            "uid": registration.uid,
            "student_name": registration.student_name,
            "is_registration_completed": registration.is_registration_completed,
            "is_account_created": registration.is_account_created,
            "migrated_from_other_university": registration.migrated_from_other_university,
            "latest_payment_status": payment_status,
            "aadhaar_no": registration.aadhaar_no,
            "registration_number": registration.registration_number
        }, status=status.HTTP_200_OK)


class NewRegistrationBulkCreateView(views.APIView):
    """
    API View for bulk creation of registrations.
    """
    permission_classes = [permissions.AllowAny]
    @swagger_auto_schema(
        operation_summary="Bulk create registrations",
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
            serializer = NewRegistrationCreateSerializer(data=registration_data)
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


class PaymentInfoView(views.APIView):
    """
    API View to get payment details (fee amount) before initiating payment.
    Recommended to call this to show a confirmation screen to the user.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Get payment info",
        manual_parameters=[
            openapi.Parameter('aadhaar_no', openapi.IN_QUERY, description="Student Aadhaar No", type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: "Payment Details"}
    )
    def get(self, request):
        aadhaar_no = request.query_params.get('aadhaar_no')
        if not aadhaar_no:
            return Response({"error": "aadhaar_no is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            registration = NewRegistration.objects.select_related('course').get(aadhaar_no=aadhaar_no, is_deleted=False)
        except NewRegistration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

        if not registration.migrated_from_other_university:
            return Response({
                "message": "Payment not required for non-migrated students",
                "payment_required": False
            }, status=status.HTTP_200_OK)
            
        if registration.is_registration_completed:
             return Response({
                "message": "Registration already completed",
                "payment_required": False
            }, status=status.HTTP_200_OK)

        course = registration.course
        if not course:
             return Response({"error": "No course assigned"}, status=status.HTTP_400_BAD_REQUEST)
             
        return Response({
            "student_name": registration.student_name,
            "father_name": registration.father_name,
            "mother_name": registration.mother_name,
            "dob": registration.dob,
            "gender": registration.gender,
            "mobile_no": registration.mobile_no,
            "email": registration.email,
            "aadhaar_no": registration.aadhaar_no,
            "college_name": registration.college.name if registration.college else None,
            "course_name": course.name,
            "course_code": course.code,
            "payment_required": True,
            "amount": course.registration_fee
        }, status=status.HTTP_200_OK)


class InitiatePaymentView(views.APIView):
    """
    API View to initiate CC Avenue payment.
    Requires migrated_from_other_university to be True.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Initiate CC Avenue payment",
        responses={200: "Redirect Data"}
    )
    def post(self, request, aadhaar_no):
        try:
            registration = NewRegistration.objects.select_related('course').get(aadhaar_no=aadhaar_no, is_deleted=False)
        except NewRegistration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

        if not registration.migrated_from_other_university:
            return Response({"error": "Payment only required for migrated students"}, status=status.HTTP_400_BAD_REQUEST)

        if registration.is_registration_completed:
            return Response({"error": "Registration already completed"}, status=status.HTTP_400_BAD_REQUEST)

        # Get Registration Fee from Course
        if not registration.course:
            return Response({"error": "No course assigned to this student"}, status=status.HTTP_400_BAD_REQUEST)
        
        registration_fee = registration.course.registration_fee
        
        if not registration_fee or registration_fee <= 0:
            return Response(
                {"error": f"Registration fee not set for course: {registration.course.name}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Configuration (should be in .env)
        merchant_id = config('CCAVENUE_MERCHANT_ID', default='')
        access_code = config('CCAVENUE_ACCESS_CODE', default='')
        working_key = config('CCAVENUE_WORKING_KEY', default='')
        redirect_url = config('CCAVENUE_REDIRECT_URL', default=f"{request.scheme}://{request.get_host()}/api/voc_new_registration/payment-response/")
        cancel_url = redirect_url
        
        # Use dynamic amount
        amount = str(registration_fee)

        order_id = f"REG_{uuid.uuid4().hex[:12].upper()}"
        
        # Create payment record
        RegistrationPayment.objects.create(
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
        
        ccavenue_url = config('CCAVENUE_URL', default='https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction')
        
        return Response({
            "order_id": order_id,
            "enc_request": encrypted_data,
            "access_code": access_code,
            "production_url": ccavenue_url
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
            payment = RegistrationPayment.objects.get(order_id=order_id)
        except RegistrationPayment.DoesNotExist:
            return Response({"error": "Payment record not found"}, status=status.HTTP_404_NOT_FOUND)

        payment.tracking_id = response_data.get('tracking_id')
        payment.bank_ref_no = response_data.get('bank_ref_no')
        payment.payment_mode = response_data.get('payment_mode')
        payment.raw_response = response_data
        
        if auth_status and auth_status.lower() == 'success':
            payment.payment_status = 'SUCCESS'
            # Complete registration using serializer to trigger reg_no generation
            reg = payment.registration
            serializer = NewRegistrationUpdateSerializer(
                reg, 
                data={'is_registration_completed': True}, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
            else:
                # Log error or handle failure
                print(f"Serializer error for {reg.aadhaar_no}: {serializer.errors}")
                reg.is_registration_completed = True
                reg.save()
        elif auth_status == 'Aborted':
            payment.payment_status = 'ABORTED'
        else:
            payment.payment_status = 'FAILED'
        
        payment.save()

        payment.save()

        # Redirect to Frontend
        # You should define FRONTEND_URL in your .env (e.g., http://localhost:3000)
        frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
        redirect_url = f"{frontend_url}/payment/status?order_id={order_id}&status={payment.payment_status}"
        
        return redirect(redirect_url)


class RegistrationOptionsView(views.APIView):
    """
    API View to fetch gender and caste choices for NewRegistration.
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
        from .options import GENDER_CHOICES, CASTE_CHOICES
        
        gender_choices = [
            {'value': code, 'label': label} for code, label in GENDER_CHOICES
        ]
        caste_choices = [
            {'value': code, 'label': label} for code, label in CASTE_CHOICES
        ]
        
        # Add academic lookup options
        courses = NewRegistrationCourse.objects.filter(is_active=True)
        batches = NewRegistrationBatch.objects.filter(is_active=True)
        sessions = NewRegistrationSession.objects.filter(is_active=True)
        
        return Response({
            'gender': gender_choices,
            'caste': caste_choices,
            'courses': CourseMinimalSerializer(courses, many=True).data,
            'batches': BatchMinimalSerializer(batches, many=True).data,
            'sessions': SessionMinimalSerializer(sessions, many=True).data,
        }, status=status.HTTP_200_OK)

class CaptchaView(views.APIView):
    """
    API View to generate a new captcha.
    Returns a hashkey and an image URL.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Generate new captcha",
        responses={200: "Captcha identity and image link"}
    )
    def get(self, request):
        from captcha.models import CaptchaStore
        from captcha.helpers import captcha_image_url
        
        hashkey = CaptchaStore.generate_key()
        image_url = f"{request.scheme}://{request.get_host()}{captcha_image_url(hashkey)}"
        
        return Response({
            "captcha_key": hashkey,
            "captcha_image": image_url
        }, status=status.HTTP_200_OK)
