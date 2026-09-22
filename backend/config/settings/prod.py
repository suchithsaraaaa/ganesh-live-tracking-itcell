"""
Production settings for AWS EC2 deployment.
"""
from .base import *

DEBUG = False
USE_POSTGIS = True

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Production PostgreSQL + PostGIS database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('POSTGRES_DB') or os.environ.get('DB_NAME') or 'ganesh_tracking',
        'USER': os.environ.get('POSTGRES_USER') or os.environ.get('DB_USER') or 'postgres',
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD') or os.environ.get('DB_PASSWORD') or '',
        'HOST': os.environ.get('POSTGRES_HOST') or os.environ.get('DB_HOST') or 'localhost',
        'PORT': os.environ.get('POSTGRES_PORT') or os.environ.get('DB_PORT') or '5432',
    }
}

# Production security headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = os.environ.get('SECURE_COOKIES', 'False') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('SECURE_COOKIES', 'False') == 'True'
