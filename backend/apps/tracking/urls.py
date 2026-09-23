from django.urls import path
from .views import (
    StartTrackingView,
    IngestLocationView,
    BatchIngestLocationView,
    StopTrackingView,
    TimestampLookupView,
    JourneyView,
    SessionJourneyView,
    ActiveTrackingListView,
    LatestLocationView,
)

urlpatterns = [
    path('active/', ActiveTrackingListView.as_view(), name='tracking-active'),
    path('sessions/<int:session_id>/journey/', SessionJourneyView.as_view(), name='tracking-session-journey'),
    path('start/', StartTrackingView.as_view(), name='tracking-start'),
    path('location/', IngestLocationView.as_view(), name='tracking-location'),
    path('location/batch/', BatchIngestLocationView.as_view(), name='tracking-location-batch'),
    path('stop/', StopTrackingView.as_view(), name='tracking-stop'),
    path('idols/<str:gpid>/location-at/', TimestampLookupView.as_view(), name='tracking-location-at'),
    path('idols/<str:gpid>/journey/', JourneyView.as_view(), name='tracking-journey'),
    path('idols/<str:gpid>/latest/', LatestLocationView.as_view(), name='tracking-latest'),
]

