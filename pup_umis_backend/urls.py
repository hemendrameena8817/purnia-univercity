"""
URL configuration for pup_umis_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
import os
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from voc_new_registration.views import CaptchaView

schema_view = get_schema_view(
    openapi.Info(
        title=" API",
        default_version="v1",
        description="API for Sewa Bharati - PUP UMIS Backend",
        contact=openapi.Contact(email="pu@zucol.ai"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("super-admin-umis/", admin.site.urls),
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),

    path('api/accounts/', include('accounts.urls')),
    path('api/students/', include('students.urls')),
    path('api/colleges/', include('colleges.urls')),
    path('api/grievances/', include('grievance.urls')),
    path('api/voc_new_registration/', include('voc_new_registration.urls')),
    path('api/academics/', include('academics.urls')),
    path('api/captcha/', include('captcha.urls')),
    path('api/plw/', include('plw.urls')),
    path('api/mca_sem/', include('mca_sem.urls')),
    path('api/btech/', include('btech.urls')),
    path('api/pg/', include('pg.urls')),
    path('api/ug/', include('ug.urls')),
    path('api/staging/', include('staging.urls')),
    path('api/captcha/', CaptchaView.as_view(), name='common-captcha'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG or os.getenv("DEBUG", "False") == "True":
    urlpatterns += [
        path(
            "swagger/",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
    ]
