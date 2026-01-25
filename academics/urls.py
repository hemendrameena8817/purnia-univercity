from django.urls import path
from .views import BatchListView, CourseListView

urlpatterns = [
    path('batches/', BatchListView.as_view(), name='batch-list'),
    path('courses/', CourseListView.as_view(), name='course-list'),
]
