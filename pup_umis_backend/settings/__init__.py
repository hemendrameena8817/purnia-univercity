"""
Settings module for pup_umis_backend project.

This __init__.py loads the appropriate settings based on environment.

By default, it loads development settings.
For production, set: DJANGO_SETTINGS_MODULE=pup_umis_backend.settings.production
"""

import os
from decouple import config

# Get environment from DJANGO_ENV variable, default to 'development'
ENVIRONMENT = config('DJANGO_ENV', default='development')

if ENVIRONMENT == 'production':
    from .production import *
else:
    from .development import *
