from django.urls import path
from dj_rest_auth.views import LogoutView
from .views import LoginView, ProfileView, DashboardView
from .api.admin import RegistrationWindowControlView

urlpatterns = [
    # Unified Login
    path('login/', LoginView.as_view(), name='login'),
    
    # Auth Management
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Admin APIs
    path('admin/registration-window/', RegistrationWindowControlView.as_view(), name='registration-window-control'),
]
