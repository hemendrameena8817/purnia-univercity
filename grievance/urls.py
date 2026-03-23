from django.urls import path
from .views import (
    GrievanceListCreateView,
    GrievanceDetailView,
    GrievanceCommentListView,
    GrievanceCommentCreateView,
    GrievanceStatsView,
    GrievancePaymentInitiateView,
    GrievancePaymentResponseView,
    GrievanceStatusByUIDView,
    GrievanceSubCategoriesByCategoryView,
    GrievanceCategoryListView,
    GrievanceAttachmentUploadView,
)

urlpatterns = [
    # List all grievances or create new one
    path('', GrievanceListCreateView.as_view(), name='grievance-list-create'),
    
    # Upload attachment before creating grievance
    path('upload-attachment/', GrievanceAttachmentUploadView.as_view(), name='grievance-upload-attachment'),
    
    # Get all active categories
    path('categories/', GrievanceCategoryListView.as_view(), name='grievance-categories'),
    
    # Get grievance statistics
    path('stats/', GrievanceStatsView.as_view(), name='grievance-stats'),
    
    # Get grievance status by UID (for payment status page)
    path('status-by-uid/', GrievanceStatusByUIDView.as_view(), name='grievance-status-by-uid'),
    
    # Get subcategories by category UID
    path('subcategories/', GrievanceSubCategoriesByCategoryView.as_view(), name='grievance-subcategories'),
    
    # Payment endpoints
    path('payment-response/', GrievancePaymentResponseView.as_view(), name='grievance-payment-response'),
    
    path('<uuid:grievance_uid>/initiate-payment/', GrievancePaymentInitiateView.as_view(), name='grievance-payment-initiate'),
    
    # Retrieve or update a specific grievance (by ID or grievance_number)
    path('<str:identifier>/', GrievanceDetailView.as_view(), name='grievance-detail'),
    
    # Get all comments for a grievance
    path('<str:identifier>/comments/', GrievanceCommentListView.as_view(), name='grievance-comments-list'),
    
    # Add comment to a grievance
    path('<str:identifier>/add-comment/', GrievanceCommentCreateView.as_view(), name='grievance-comment-add'),
]
