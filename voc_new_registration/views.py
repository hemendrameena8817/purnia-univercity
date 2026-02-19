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
from .utils.registration_logic import generate_registration_number, check_course_registration_window
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
from django.utils import timezone
import uuid
from .utils.ccavenue_utils import encrypt, decrypt, parse_response
from accounts.permissions import IsUniversityAdmin, CanManageVocRegistration
from pup_umis_backend.utils.pagination import DefaultPagination


class NewRegistrationListView(generics.ListAPIView):
    """
    API View to list all new registrations.
    Supports search and filtering.
    """
    serializer_class = NewRegistrationListSerializer
    permission_classes = [CanManageVocRegistration]
    pagination_class = DefaultPagination
    
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
        course_uid = self.request.query_params.get('course_uid', None)
        if course_uid:
            queryset = queryset.filter(course__uid=course_uid)
        
        batch_uid = self.request.query_params.get('batch_uid', None)
        if batch_uid:
            queryset = queryset.filter(batch__uid=batch_uid)
        
        gender_uid = self.request.query_params.get('gender_uid', None)
        if gender_uid:
            queryset = queryset.filter(gender=gender_uid.upper())
        
        caste_uid = self.request.query_params.get('caste_uid', None)
        if caste_uid:
            queryset = queryset.filter(caste=caste_uid.upper())
        
        college_uid = self.request.query_params.get('college_uid', None)
        if college_uid:
            queryset = queryset.filter(college__uid=college_uid)
        
        is_completed = self.request.query_params.get('is_registration_completed', None)
        if is_completed is not None:
            queryset = queryset.filter(is_registration_completed=is_completed.lower() == 'true')
            
        return queryset

    @swagger_auto_schema(
        operation_summary="List all new registrations",
        operation_description="Retrieve a list of all new registration entries with pagination support",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description="Search by name, father name, or mother name", type=openapi.TYPE_STRING),
            openapi.Parameter('course_uid', openapi.IN_QUERY, description="Filter by course UID", type=openapi.TYPE_STRING),
            openapi.Parameter('batch_uid', openapi.IN_QUERY, description="Filter by batch UID", type=openapi.TYPE_STRING),
            openapi.Parameter('gender_uid', openapi.IN_QUERY, description="Filter by gender (MALE/FEMALE/OTHER)", type=openapi.TYPE_STRING),
            openapi.Parameter('caste_uid', openapi.IN_QUERY, description="Filter by caste (e.g. GENERAL, OBC, SC, ST)", type=openapi.TYPE_STRING),
            openapi.Parameter('college_uid', openapi.IN_QUERY, description="Filter by college UID", type=openapi.TYPE_STRING),
            openapi.Parameter('is_registration_completed', openapi.IN_QUERY, description="Filter by completion status (true/false)", type=openapi.TYPE_BOOLEAN),
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
        operation_description="Lookup by Aadhaar number. Requires course code matching.",
        manual_parameters=[
            openapi.Parameter('course_code', openapi.IN_QUERY, description="Registered Course Code", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('captcha_key', openapi.IN_QUERY, description="Captcha Hash Key (Optional for now)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('captcha_value', openapi.IN_QUERY, description="Solved Captcha Text (Optional for now)", type=openapi.TYPE_STRING, required=False),
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

        course_code = request.query_params.get('course_type')
        if not course_code:
            return Response({"error": "course_type is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        aadhaar_no = self.kwargs.get(self.lookup_url_kwarg)
        try:
            instance = self.get_queryset().get(aadhaar_no=aadhaar_no, course__code=course_code)
        except NewRegistration.DoesNotExist:
            return Response({"error": "Registration not found with provided Aadhaar and Course Code"}, status=status.HTTP_404_NOT_FOUND)
        
        is_valid, error_data = check_course_registration_window(instance.course)
        if not is_valid:
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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
            registration = NewRegistration.objects.select_related(
                'college', 'course', 'batch', 'session'
            ).get(uid=uid, is_deleted=False)
        except (NewRegistration.DoesNotExist, ValueError):
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get latest payment status and details if it exists
        latest_payment = registration.payments.order_by('-created_at').first()
        payment_data = None
        if latest_payment:
            payment_data = {
                "order_id": latest_payment.order_id,
                "payment_status": latest_payment.payment_status,
                "amount": str(latest_payment.amount),
                "payment_mode": latest_payment.payment_mode,
                "tracking_id": latest_payment.tracking_id,
                "bank_ref_no": latest_payment.bank_ref_no,
                "created_at": latest_payment.created_at
            }

        # Fallback: Generate registration number if needed
        if not registration.registration_number and registration.is_registration_completed:
            try:
                generate_registration_number(registration)
            except Exception as e:
                # Log error but don't block the status return
                print(f"Error generating registration number in StatusView: {str(e)}")

        # Use the serializer to get complete registration data
        serializer = NewRegistrationGetSerializer(registration, context={'request': request})
        registration_data = serializer.data
        
        # Add payment information to the response
        registration_data['payment_details'] = payment_data
        registration_data['latest_payment_status'] = latest_payment.payment_status if latest_payment else None

        return Response(registration_data, status=status.HTTP_200_OK)


class NewRegistrationBulkCreateView(views.APIView):
    """
    API View for bulk creation of registrations.
    """
    permission_classes = [CanManageVocRegistration]
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
        import logging
        logger = logging.getLogger(__name__)
        
        # Log the incoming request data for debugging
        logger.info(f"Payment response received. Data: {request.data}")
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
            decrypted_response = decrypt(enc_response, working_key)
            response_data = parse_response(decrypted_response)
            logger.info(f"Decrypted response data: {response_data}")
            
            order_id = response_data.get('order_id')
            auth_status = response_data.get('order_status', '').lower()
            
            if not order_id:
                raise ValueError("No order_id in decrypted response")
                
            logger.info(f"Processing payment for order_id: {order_id}, status: {auth_status}")
            
            try:
                payment = RegistrationPayment.objects.select_related(
                    'registration',
                    'registration__college',
                    'registration__course',
                    'registration__batch',
                    'registration__session'
                ).get(order_id=order_id)
            except RegistrationPayment.DoesNotExist:
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
                reg = payment.registration
                
                try:
                    # For migrated students, ensure registration number is generated
                    if reg.migrated_from_other_university and not reg.registration_number:
                        # Generate registration number
                        reg.registration_number = generate_registration_number(reg)
                        logger.info(f"Generated registration number: {reg.registration_number} for migrated student")
                    
                    # Mark registration as completed
                    reg.is_registration_completed = True
                    reg.save()
                    
                    logger.info(f"Successfully updated registration for {reg.aadhaar_no}")
                    
                except Exception as e:
                    logger.error(f"Error updating registration: {str(e)}")
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
            
            if hasattr(payment, 'registration') and hasattr(payment.registration, 'uid'):
                uid = str(payment.registration.uid)
                redirect_url = (
                    f"{frontend_url}/new-registration/registration-status"
                    f"?uid={uid}"
                    f"&payment_status={payment.payment_status.lower()}"
                    f"&order_id={order_id}"
                )
                if payment.payment_status == 'SUCCESS' and payment.registration.registration_number:
                    redirect_url += f"&registration_number={payment.registration.registration_number}"
            else:
                logger.error(f"Registration or UID not found for payment {payment.id}")
                redirect_url = f"{frontend_url}/new-registration/registration-status?error=registration_not_found"

            logger.info(f"Redirecting to: {redirect_url}")
            return redirect(redirect_url)
            
        except Exception as e:
            logger.exception("Error processing payment response")
            # Still redirect to frontend but with error status
            frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
            error_redirect = f"{frontend_url}/new-registration/registration-status?error={str(e)[:100]}"
            return redirect(error_redirect)


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


class CheckRegistrationWindowView(views.APIView):
    """
    API View to check if the registration window is open for a given course.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Check course registration window",
        manual_parameters=[
            openapi.Parameter('course_code', openapi.IN_QUERY, description="Course Code", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: "Registration is open",
            400: "Registration is closed",
            404: "Course not found"
        }
    )
    def get(self, request):
        course_code = request.query_params.get('course_code')
        if not course_code:
            return Response({"error": "course_code is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = NewRegistrationCourse.objects.get(code=course_code)
        except NewRegistrationCourse.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            
        current_time = timezone.now()
        start = course.registration_start_datetime
        end = course.registration_end_datetime
        
        if not start and not end:
            return Response({
                "status": "NOT_CONFIGURED",
                "is_open": False,
                "message": "Registration schedule is not configured",
                "course": course.name,
                "code": course.code,
                "current_datetime": timezone.localtime(current_time)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        status_key = "OPEN"
        message = "Registration is open"
        is_open = True
        
        if start and current_time < start:
            status_key = "NOT_STARTED"
            is_open = False
            message = "Registration has not started yet"
        elif end and current_time > end:
            status_key = "ENDED"
            is_open = False
            message = "Registration has ended"
            
        return Response({
            "status": status_key,
            "is_open": is_open,
            "message": message,
            "course": course.name,
            "code": course.code,
            "start_datetime": timezone.localtime(start) if start else None,
            "end_datetime": timezone.localtime(end) if end else None,
            "current_datetime": timezone.localtime(current_time)
        }, status=status.HTTP_200_OK)


class RegistrationCardPDFView(views.APIView):
    """
    Generate and download Registration Card PDF for VOC students.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Download Registration Card PDF",
        manual_parameters=[
            openapi.Parameter('uid', openapi.IN_QUERY, description="Registration UID", type=openapi.TYPE_STRING, required=True),
        ]
    )
    def get(self, request):
        from django.http import HttpResponse
        from .utils.pdf_utils import generate_voc_registration_card
        
        uid = request.query_params.get('uid')
        if not uid:
            return Response({"error": "UID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            registration = NewRegistration.objects.select_related(
                'college', 'course', 'batch', 'session'
            ).get(uid=uid, is_deleted=False)
        except (NewRegistration.DoesNotExist, ValueError):
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if not registration.is_registration_completed:
            return Response({"error": "Registration is not completed yet"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Generate PDF
            pdf_buffer = generate_voc_registration_card(registration)
            
            # Return Response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            filename = f"Registration_Card_{registration.registration_number or registration.aadhaar_no}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
