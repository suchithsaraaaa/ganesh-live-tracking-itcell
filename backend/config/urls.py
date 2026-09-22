"""
Root URL Configuration for Hyderabad Police Ganesh Visarjan Live Tracking.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from apps.tracking.views import MobileSessionView, MobileLocationView


def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'service': 'Hyderabad Police Ganesh Visarjan Live Tracking API',
        'version': '1.0.0'
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    # Direct Android APK compatibility routes
    path('api/tracking/session', MobileSessionView.as_view(), name='mobile-session'),
    path('api/tracking/location', MobileLocationView.as_view(), name='mobile-location'),
    # Versioned REST API routes
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/idols/', include('apps.idols.urls')),
    path('api/v1/assignments/', include('apps.assignments.urls')),
    path('api/v1/tracking/', include('apps.tracking.urls')),
    path('api/v1/geography/', include('apps.geography.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
]
