"""
Base settings for Hyderabad Police Ganesh Visarjan Live Tracking System.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Add apps directory to sys.path so apps can be imported cleanly
APPS_DIR = BASE_DIR / 'apps'
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# GDAL and GEOS configuration for GeoDjango
# Auto-detect on Windows if not already set
if sys.platform == 'win32':
    possible_paths = [
        Path(sys.prefix) / 'lib' / 'site-packages' / 'pyogrio.libs',
        Path(sys.prefix) / 'Lib' / 'site-packages' / 'pyogrio.libs',
        Path(BASE_DIR.parent) / '.venv' / 'Lib' / 'site-packages' / 'pyogrio.libs',
    ]
    for lib_dir in possible_paths:
        if lib_dir.exists():
            gdal_dlls = list(lib_dir.glob('gdal*.dll'))
            geos_dlls = list(lib_dir.glob('geos_c*.dll'))
            if gdal_dlls and not os.environ.get('GDAL_LIBRARY_PATH'):
                GDAL_LIBRARY_PATH = str(gdal_dlls[0])
            if geos_dlls and not os.environ.get('GEOS_LIBRARY_PATH'):
                GEOS_LIBRARY_PATH = str(geos_dlls[0])
            break

if os.environ.get('GDAL_LIBRARY_PATH'):
    GDAL_LIBRARY_PATH = os.environ['GDAL_LIBRARY_PATH']
if os.environ.get('GEOS_LIBRARY_PATH'):
    GEOS_LIBRARY_PATH = os.environ['GEOS_LIBRARY_PATH']

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-police-live-tracking-hyd-2026-key')

DEBUG = False

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    # Third-party
    'rest_framework',
    'corsheaders',

    # Core Domain Apps
    'apps.accounts',
    'apps.idols',
    'apps.assignments',
    'apps.tracking',
    'apps.geography',
    'apps.reports',
    'apps.audit',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# User model
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

USE_POSTGIS = False

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

CORS_ALLOW_ALL_ORIGINS = True

# AWS S3 Configuration (Optional report storage)
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-south-1')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
