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
