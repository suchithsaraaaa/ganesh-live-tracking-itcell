"""
ASGI config for Hyderabad Police Ganesh Visarjan Live Tracking.
"""
import os
import sys
from pathlib import Path
from django.core.asgi import get_asgi_application

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

application = get_asgi_application()
