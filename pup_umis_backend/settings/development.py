"""
Development settings for pup_umis_backend project.
Use this for local development.

Usage:
    export DJANGO_SETTINGS_MODULE=pup_umis_backend.settings.development
    OR
    python manage.py runserver --settings=pup_umis_backend.settings.development
"""

from .base import *
from decouple import config, Csv

# -------------------------------------------------
# Security Settings (Development)
# -------------------------------------------------

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

DEBUG = True

ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1']


# -------------------------------------------------
# Database (Development - MySQL)
# Each developer creates their own local database
# -------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config('DB_NAME', default='pup_umis_dev'),
        "USER": config('DB_USER', default='root'),
        "PASSWORD": config('DB_PASSWORD', default=''),
        "HOST": config('DB_HOST', default='localhost'),
        "PORT": config('DB_PORT', default='3306'),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# -------------------------------------------------
# CORS Settings (Development - Allow all)
# -------------------------------------------------

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())

# Allow all origins in development (optional - less secure)
CORS_ALLOW_ALL_ORIGINS = True


# -------------------------------------------------
# CSRF Settings (Development)
# -------------------------------------------------
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv())


# -------------------------------------------------
# Email Backend (Development - Console)
# -------------------------------------------------

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# -------------------------------------------------
# Logging (Development - Verbose)
# -------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Set to DEBUG to see SQL queries
            'propagate': False,
        },
    },
}


# -------------------------------------------------
# Debug Toolbar (Optional - uncomment if installed)
# -------------------------------------------------

# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
# INTERNAL_IPS = ['127.0.0.1']
