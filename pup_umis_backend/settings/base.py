"""
Base settings for pup_umis_backend project.
Contains settings common to all environments.
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# -------------------------------------------------
# Application definition
# -------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    
    # Third-party apps
    "rest_framework",
    "rest_framework.authtoken",  
    "drf_yasg",
    "import_export",  
    "simple_history",
    "corsheaders",
    "storages",
    
    # Auth apps
    "dj_rest_auth",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",

    # Local apps
    "accounts",
    "university",
    "colleges",
    "academics",
    "students",
    "ug",
    "pg",
    "grievance",
    "staging",
    "voc_new_registration",
    "captcha",
    'plw',
    'llb',
    'mca_sem',
    'btech',
    'mba_sem',
    'ug_before_cbcs',
    'bba_year',
    'bca_hons_year',
    'pgoldresult'
    'omr',
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # Required for allauth

    # simple_history middleware
    "simple_history.middleware.HistoryRequestMiddleware",
]


ROOT_URLCONF = "pup_umis_backend.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "pup_umis_backend.wsgi.application"


# -------------------------------------------------
# Password validation
# -------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# -------------------------------------------------
# Internationalization
# -------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = config('TIME_ZONE', default='Asia/Kolkata')

USE_I18N = True

USE_TZ = True


# -------------------------------------------------
# Static files (CSS, JavaScript, Images)
# -------------------------------------------------

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

# -------------------------------------------------
# Media files (User uploaded files)
# -------------------------------------------------
if config('DJANGO_ENV', default='development') == 'development':
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'


# -------------------------------------------------
# Default primary key field type
# -------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -------------------------------------------------
# Custom User Model
# -------------------------------------------------

AUTH_USER_MODEL = "accounts.UserAccount"

SITE_ID = 1  # Required for allauth

# -------------------------------------------------
# Django REST Framework
# -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# -------------------------------------------------
# Swagger/OpenAPI Settings
# -------------------------------------------------

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Enter your bearer token in the format: Bearer <token>'
        }
    },
    'USE_SESSION_AUTH': False,
}


# -------------------------------------------------
# dj-rest-auth & AllAuth Settings
# -------------------------------------------------

ACCOUNT_LOGIN_METHODS = {'username'}  # Use username for login
# ACCOUNT_SIGNUP_FIELDS = ['username']  # Only username is required for signup
# ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_UNIQUE_EMAIL = True  # Keep email unique if provided
# ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'

REST_AUTH = {
    'LOGIN_SERIALIZER': 'accounts.serializers.LoginSerializer',
    'USER_DETAILS_SERIALIZER': 'accounts.serializers.UserProfileSerializer',
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': None,
    'JWT_AUTH_REFRESH_COOKIE': None,}


# -------------------------------------------------
# Simple JWT Settings
# -------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config('JWT_ACCESS_TOKEN_LIFETIME', default=30, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config('JWT_REFRESH_TOKEN_LIFETIME', default=1, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# -------------------------------------------------
# CORS Settings (common)
# -------------------------------------------------

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "ngrok-skip-browser-warning",
]
