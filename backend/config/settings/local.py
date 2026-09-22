"""
Local development settings.
"""
from .base import *

DEBUG = True

# Database configuration
# If DATABASE_URL is set, use PostgreSQL / PostGIS; otherwise SQLite
database_url = os.environ.get('DATABASE_URL')
if database_url:
    import urllib.parse
    parsed = urllib.parse.urlparse(database_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username,
            'PASSWORD': parsed.password,
            'HOST': parsed.hostname,
            'PORT': parsed.port or 5432,
        }
    }
else:
    # Local fallback for development and test suites
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.spatialite' if os.environ.get('USE_SPATIALITE') else 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
