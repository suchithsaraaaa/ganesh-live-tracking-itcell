import os
from django.core.exceptions import ImproperlyConfigured
from .base import *

DEBUG = False
USE_POSTGIS = True

# Production SECRET_KEY: Must be explicitly configured; no fallback to development secrets
SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable is required in production.")

INSECURE_SECRET_KEYS = {
    'django-insecure-police-live-tracking-hyd-2026-key',
    'police_secret_key_change_in_production',
    'change-me-to-a-secure-random-50-char-secret-key',
}
if SECRET_KEY in INSECURE_SECRET_KEYS:
    raise ImproperlyConfigured("Insecure placeholder SECRET_KEY detected. A genuine production secret key is required.")

# Production ALLOWED_HOSTS: Explicitly configured; no wildcard fallback
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS') or os.environ.get('DJANGO_ALLOWED_HOSTS')
if not allowed_hosts_env or not allowed_hosts_env.strip():
    raise ImproperlyConfigured("ALLOWED_HOSTS environment variable is required in production.")

ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS environment variable must contain at least one valid host.")
if '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Wildcard '*' is not permitted in ALLOWED_HOSTS in production.")

# Production Database Password: Must be explicitly configured; no fallback
db_password = os.environ.get('DB_PASSWORD') or os.environ.get('POSTGRES_PASSWORD')
if not db_password:
    raise ImproperlyConfigured("DB_PASSWORD environment variable is required in production.")

INSECURE_DB_PASSWORDS = {
    'police_secure_pass_2026',
    'change-me-to-a-strong-database-password',
}
if db_password in INSECURE_DB_PASSWORDS:
    raise ImproperlyConfigured("Insecure placeholder DB_PASSWORD detected. A genuine production database password is required.")

# Production PostgreSQL + PostGIS database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME') or os.environ.get('POSTGRES_DB') or 'ganesh_tracking',
        'USER': os.environ.get('DB_USER') or os.environ.get('POSTGRES_USER') or 'postgres',
        'PASSWORD': db_password,
        'HOST': os.environ.get('DB_HOST') or os.environ.get('POSTGRES_HOST') or 'db',
        'PORT': os.environ.get('DB_PORT') or os.environ.get('POSTGRES_PORT') or '5432',
        'CONN_MAX_AGE': int(os.environ.get('CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
    }
}

# Production security headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = os.environ.get('SECURE_COOKIES', 'False') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('SECURE_COOKIES', 'False') == 'True'
