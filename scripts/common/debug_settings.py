import os
import sys
import django
from django.conf import settings

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pup_umis_backend.settings')
django.setup()

print("--- DEBUGGING SETTINGS ---")
print(f"REST_AUTH: {settings.REST_AUTH}")
print(f"JWT_AUTH_REFRESH_COOKIE: {settings.REST_AUTH.get('JWT_AUTH_REFRESH_COOKIE')}")
print(f"JWT_AUTH_COOKIE: {settings.REST_AUTH.get('JWT_AUTH_COOKIE')}")
print(f"USE_JWT: {settings.REST_AUTH.get('USE_JWT')}")
