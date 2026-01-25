from rest_framework import generics, permissions
from .models import Batch, Course
from .serializers import BatchSerializer, CourseSerializer

class BatchListView(generics.ListAPIView):
    """
    API view to list all batches.
    """
    queryset = Batch.objects.filter(is_active=True)
    serializer_class = BatchSerializer
    permission_classes = [permissions.AllowAny]

class CourseListView(generics.ListAPIView):
    """
    API view to list all courses.
    """
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]
