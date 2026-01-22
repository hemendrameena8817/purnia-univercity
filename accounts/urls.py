from django.urls import path
from dj_rest_auth.views import LogoutView
from .views import LoginView, ProfileView

urlpatterns = [
    # Unified Login
    path('login/', LoginView.as_view(), name='login'),
    
    # Auth Management
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
