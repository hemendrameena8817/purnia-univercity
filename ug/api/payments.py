import logging
import uuid as uuid_lib

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import redirect as django_redirect
from decouple import config

from ug.models import UGStudentProfile, ExamRegistration, ExamRegistrationPayment
from pg.utils.ccavenue_utils import encrypt, decrypt, parse_response  # Reusing pg utils as they are just cc avenue generic

logger = logging.getLogger(__name__)

class UGPaymentInfoView(APIView):
    """
    GET  /api/ug/payment-info/?registration_uid=<uid>
    Returns fee amount and student details before initiating payment.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            student = UGStudentProfile.objects.get(user=request.user)
        except UGStudentProfile.DoesNotExist:
            return Response({'error': 'No UG student profile found.'}, status=status.HTTP_404_NOT_FOUND)

        registration_uid = request.query_params.get('registration_uid')
        if registration_uid:
            try:
                registration = ExamRegistration.objects.get(uid=registration_uid, student=student)
            except ExamRegistration.DoesNotExist:
                return Response({'error': 'Registration not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            registration = ExamRegistration.objects.filter(student=student).order_by('-sem', '-created_at').first()
            if not registration:
                return Response({'error': 'No exam registration found.'}, status=status.HTTP_404_NOT_FOUND)

        if registration.status == 'REGISTERED':
            return Response({
                'message': 'Payment already completed. Registration is confirmed.',
                'payment_required': False,
                'registration_uid': str(registration.uid),
            }, status=status.HTTP_200_OK)

        if not registration.fees or registration.fees <= 0:
            return Response({'error': 'Fee amount not set for this registration. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)

        # Latest payment status
        latest_payment = registration.payments.order_by('-created_at').first()

        return Response({
            'payment_required': True,
            'registration_uid': str(registration.uid),
            'student_name': student.first_name ,
            'father_name': student.father_name,
            'registration_no': student.registration_no,
            'sem': registration.sem,
            'session': registration.session,
            'amount': registration.fees,
            'latest_payment_status': latest_payment.payment_status if latest_payment else None,
        }, status=status.HTTP_200_OK)


class UGInitiatePaymentView(APIView):
    """
    POST  /api/ug/initiate-payment/
    Body: { "registration_uid": "<uid>" }
    Generates CC Avenue encrypted order and returns enc_request + access_code.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            student = UGStudentProfile.objects.get(user=request.user)
        except UGStudentProfile.DoesNotExist:
            return Response({'error': 'No UG student profile found.'}, status=status.HTTP_404_NOT_FOUND)

        registration_uid = request.data.get('registration_uid') or request.data.get('registration_no')
        if not registration_uid:
            return Response({'error': 'registration_uid or registration_no is required.'}, status=status.HTTP_400_BAD_REQUEST)

        import uuid as _uuid
        registration = None
        try:
            _uuid.UUID(str(registration_uid))          # valid UUID?
            registration = ExamRegistration.objects.filter(
                uid=registration_uid, student=student
            ).first()
        except ValueError:
            pass  # not a UUID — fall through to registration_no lookup

        if registration is None:
            # Fallback: look up by student registration_no
            try:
                prof = UGStudentProfile.objects.get(registration_no=registration_uid)
                registration = ExamRegistration.objects.filter(
                    student=prof
                ).order_by('-sem', '-created_at').first()
            except UGStudentProfile.DoesNotExist:
                pass

        if registration is None:
            return Response({'error': 'Registration not found.'}, status=status.HTTP_404_NOT_FOUND)

        if registration.status == 'REGISTERED':
            return Response({'error': 'Registration already confirmed. Payment not required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not registration.fees or registration.fees <= 0:
            return Response({'error': 'Fee amount not configured for this registration.'}, status=status.HTTP_400_BAD_REQUEST)

        merchant_id = config('CCAVENUE_MERCHANT_ID', default='')
        access_code = config('CCAVENUE_ACCESS_CODE', default='')
        working_key = config('CCAVENUE_WORKING_KEY', default='')
        redirect_url = config(
            'CCAVENUE_UG_REDIRECT_URL',
            default=f"{request.scheme}://{request.get_host()}/api/ug/payment-response/"
        )
        cancel_url = redirect_url

        amount = str(registration.fees)
        order_id = f"UG_{uuid_lib.uuid4().hex[:12].upper()}"

        ExamRegistrationPayment.objects.create(
            registration=registration,
            order_id=order_id,
            amount=amount,
            payment_status='PENDING'
        )

        merchant_data = (
            f"merchant_id={merchant_id}&order_id={order_id}&"
            f"amount={amount}&currency=INR&"
            f"redirect_url={redirect_url}&cancel_url={cancel_url}&"
            f"language=EN&billing_name={student.get_full_name()}&"
            f"billing_tel={student.mobile_no or ''}&"
            f"billing_email={(student.user.email or '') if hasattr(student, 'user') else ''}"
        )

        encrypted_data = encrypt(merchant_data, working_key)
        ccavenue_url = config('CCAVENUE_URL', default='https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction')

        return Response({
            'order_id': order_id,
            'enc_request': encrypted_data,
            'access_code': access_code,
            'production_url': ccavenue_url,
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class UGPaymentResponseView(APIView):
    """
    POST  /api/ug/payment-response/
    CC Avenue posts the encrypted payment result here.
    Decrypts the response, updates payment record, marks registration REGISTERED on success,
    then redirects to the frontend.
    """
    permission_classes = []  # CC Avenue posts here — no JWT

    def post(self, request):
        logger.info(f"UG Payment response received. Data: {request.data}")

        if request.content_type == 'application/x-www-form-urlencoded':
            enc_response = request.POST.get('encResp')
        else:
            enc_response = request.data.get('encResp')

        if not enc_response:
            logger.error("No encResp parameter in UG payment response")
            return Response({'error': 'Invalid response: Missing encResp parameter'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            working_key = config('CCAVENUE_WORKING_KEY')
            decrypted_response = decrypt(enc_response, working_key)
            response_data = parse_response(decrypted_response)
            logger.info(f"UG Decrypted response: {response_data}")

            order_id = response_data.get('order_id')
            auth_status = response_data.get('order_status', '').lower()

            if not order_id:
                raise ValueError("No order_id in decrypted response")

            try:
                payment = ExamRegistrationPayment.objects.select_related('registration').get(order_id=order_id)
            except ExamRegistrationPayment.DoesNotExist:
                logger.error(f"UG Payment record not found for order_id: {order_id}")
                return Response({'error': 'Payment record not found'}, status=status.HTTP_404_NOT_FOUND)

            payment.tracking_id = response_data.get('tracking_id')
            payment.bank_ref_no = response_data.get('bank_ref_no')
            payment.payment_mode = response_data.get('payment_mode')
            payment.raw_response = response_data

            if auth_status == 'success':
                payment.payment_status = 'SUCCESS'
                reg = payment.registration
                reg.status = 'REGISTERED'
                reg.save()
                logger.info(f"UG Registration confirmed for order_id: {order_id}")
            elif auth_status == 'aborted':
                payment.payment_status = 'ABORTED'
            else:
                payment.payment_status = 'FAILED'

            payment.save()

            frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
            uid = str(payment.registration.uid)
            redirect_url = (
                f"{frontend_url}/ug-exam-registration"
                f"?uid={uid}"
                f"&payment_status={payment.payment_status.lower()}"
                f"&order_id={order_id}"
            )
            return django_redirect(redirect_url)

        except Exception as e:
            logger.exception("Error processing UG payment response")
            frontend_url = config('FRONTEND_URL', default='http://localhost:3000')
            return django_redirect(f"{frontend_url}/ug-exam-registration?error={str(e)[:100]}")


class UGRegistrationStatusView(APIView):
    """
    GET /api/ug/<uuid:uid>/status/
    Public endpoint (no auth required) that returns the status of a
    ExamRegistration and its latest payment.
    """
    permission_classes = []

    def get(self, request, uid):
        # Using a very simple serialization here to avoid importing a large serializer if not strictly needed
        # Or you can do it manually:
        try:
            registration = ExamRegistration.objects.select_related('student').get(uid=uid)
        except (ExamRegistration.DoesNotExist, ValueError):
            return Response({'error': 'Registration not found'}, status=status.HTTP_404_NOT_FOUND)

        latest_payment = registration.payments.order_by('-created_at').first()
        payment_data = None
        if latest_payment:
            payment_data = {
                'order_id':       latest_payment.order_id,
                'payment_status': latest_payment.payment_status,
                'amount':         str(latest_payment.amount),
                'payment_mode':   latest_payment.payment_mode,
                'tracking_id':    latest_payment.tracking_id,
                'bank_ref_no':    latest_payment.bank_ref_no,
                'created_at':     latest_payment.created_at,
            }

        return Response({
            'uid': str(registration.uid),
            'registration_no': registration.student.registration_no,
            'sem': registration.sem,
            'session': registration.session,
            'fees': registration.fees,
            'status': registration.status,
            'payment_details': payment_data,
            'latest_payment_status': latest_payment.payment_status if latest_payment else None,
        }, status=status.HTTP_200_OK)


class UGExamRegistrationCardPDFView(APIView):
    """
    GET /api/ug/exam-registration-card/
    Generates a UG Exam Registration Card PDF for the logged-in student.
    Fetches the latest 'REGISTERED' exam registration.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from ug.utils.exam_registration_card_pdf import generate_ug_exam_registration_card_pdf
        from django.http import HttpResponse

        # ── Resolve Student ───────────────────────────────────────────────────
        try:
            student = UGStudentProfile.objects.select_related(
                'college', 'department', 'program', 'degree', 'batch'
            ).get(user=request.user)
        except UGStudentProfile.DoesNotExist:
             return Response(
                 {'error': 'UG Student profile not found for this user.'},
                 status=status.HTTP_404_NOT_FOUND
             )

        # ── Find Latest REGISTERED Registration ──────────────────────────────
        uid = request.query_params.get('uid')
        queryset = ExamRegistration.objects.defer('admission_receipt').filter(
            student=student,
            status='REGISTERED'
        ).select_related('student', 'student__college', 'student__department').order_by('-created_at')

        if uid:
            registration = queryset.filter(uid=uid).first()
        else:
            registration = queryset.first()

        if not registration:
            return Response(
                {'error': 'No active REGISTERED exam registration found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ── Generate PDF ──────────────────────────────────────────────────────
        pdf_buffer = generate_ug_exam_registration_card_pdf(
            student, 
            registration
        )
        
        if not pdf_buffer:
            return Response(
                {'error': 'Failed to generate PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        force_download = request.GET.get('download', 'false').lower() == 'true'
        disposition = 'attachment' if force_download else 'inline'
        filename = f"UG_Exam_Registration_{student.registration_no}.pdf"

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response
