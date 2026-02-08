"""
Production settings for pup_umis_backend project.
Use this in production environment.

Usage:
    export DJANGO_SETTINGS_MODULE=pup_umis_backend.settings.production
"""

from .base import *
from decouple import config, Csv


# =================================================
# SECURITY SETTINGS
# =================================================

SECRET_KEY = config('SECRET_KEY')

DEBUG = False


# ALLOWED_HOSTS with wildcard subdomain support
# .purneau.ac.in matches all subdomains (api.purneau.ac.in, staging-api.purneau.ac.in, etc.)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    cast=Csv(),
    default=[
        "purneau.ac.in",           # Main domain
        ".purneau.ac.in",          # All subdomains (api., staging-api., student., etc.)
    ]
)


# =================================================
# DATABASE (MySQL)
# =================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config('DB_NAME'),
        "USER": config('DB_USER'),
        "PASSWORD": config('DB_PASSWORD'),
        "HOST": config('DB_HOST', default='localhost'),
        "PORT": config('DB_PORT', default='3306'),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": 60,
    }
}


# =================================================
# HTTPS & SECURITY MIDDLEWARE
# =================================================

SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)

# CRITICAL FOR PRODUCTION: Uncomment these if behind Nginx/Apache/Load Balancer
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# HSTS (Uncomment after testing)
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True


SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=None
CSRF_COOKIE_SAMESITE=None

# =================================================
# CORS SETTINGS
# =================================================

CORS_ALLOW_CREDENTIALS = True

# Match ALL subdomains automatically (*.purneau.ac.in, *.vercel.app)
CORS_ORIGIN_REGEX_WHITELIST = [
    r"^https://[\w-]+\.purneau\.ac\.in$",  # Matches: https://api.purneau.ac.in, https://student.purneau.ac.in, etc.
    r"^https://[\w-]+\.vercel\.app$",       # Matches: https://pup-student.vercel.app, etc.
]

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    cast=Csv(),
    default=[
        "https://student.purneau.ac.in",
        "https://staging-student.purneau.ac.in",
        "https://college.purneau.ac.in",
        "https://university.purneau.ac.in",
        "https://pup-college.vercel.app",
        "https://pup-student.vercel.app",
        "https://pup-university.vercel.app",
    ]
)


# =================================================
# CSRF SETTINGS
# =================================================

# Django 4.0+ supports wildcard patterns
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    cast=Csv(),
    default=[
        "https://api.purneau.ac.in",
        "https://*.purneau.ac.in",  # All subdomains
        "https://*.vercel.app",      # All Vercel apps
    ]
)


# =================================================
# EMAIL SETTINGS
# =================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@puphd.org')


# =================================================
# LOGGING
# =================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}


# =================================================
# TEMPLATE CACHING (PRODUCTION PERFORMANCE)
# =================================================

TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

TEMPLATES[0]['APP_DIRS'] = False

# =================================================
# AWS S3 SETTINGS
# =================================================

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="ap-south-2")

AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_S3_ADDRESSING_STYLE = "virtual"
AWS_S3_PUBLIC_MEDIA = False
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 300

AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

# MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"