from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.gis.geos import Point
from apps.assignments.models import Assignment

if getattr(settings, 'USE_POSTGIS', False):
    from django.contrib.gis.db import models as gis_models


class TrackingSessionStatus(models.TextChoices):
    STARTED = 'STARTED', 'Started'
    ACTIVE = 'ACTIVE', 'Active'
    STOPPED = 'STOPPED', 'Stopped'


class TrackingSession(models.Model):
    """
    Represents the active GPS tracking session associated with an Assignment.
    TrackingSession -> Assignment -> Idol
    """
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='tracking_sessions'
    )
    device_info = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=TrackingSessionStatus.choices,
        default=TrackingSessionStatus.ACTIVE,
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['assignment', 'status']),
        ]

    def __str__(self):
        return f"Session #{self.id} for {self.assignment.idol.gpid} by {self.assignment.constable.username} [{self.status}]"

    @property
    def idol(self):
        return self.assignment.idol

    @property
    def constable(self):
        return self.assignment.constable

    def stop_session(self):
        self.status = TrackingSessionStatus.STOPPED
        self.ended_at = timezone.now()
        self.save(update_fields=['status', 'ended_at', 'updated_at'])


class LocationPoint(models.Model):
    """
    Individual GPS breadcrumb recorded during a TrackingSession.
    Relates strictly to TrackingSession.
    """
    session = models.ForeignKey(
        TrackingSession,
        on_delete=models.CASCADE,
        related_name='location_points'
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    if getattr(settings, 'USE_POSTGIS', False):
        point = gis_models.PointField(srid=4326, null=True, blank=True)

    accuracy = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)  # in m/s
    heading = models.FloatField(null=True, blank=True)  # in degrees
    recorded_at = models.DateTimeField(db_index=True)  # Device timestamp
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Server receipt time

    class Meta:
        ordering = ['recorded_at']
        indexes = [
            models.Index(fields=['session', 'recorded_at']),
        ]
        constraints = [
            # Prevents duplicate telemetry on offline queue retries
            models.UniqueConstraint(
                fields=['session', 'recorded_at'],
                name='unique_session_recorded_at'
            )
        ]

    @property
    def geos_point(self):
        """Returns GeoDjango GEOS Point geometry."""
        if self.latitude is not None and self.longitude is not None:
            return Point(self.longitude, self.latitude, srid=4326)
        return None

    def save(self, *args, **kwargs):
        if getattr(settings, 'USE_POSTGIS', False):
            if self.latitude is not None and self.longitude is not None:
                self.point = Point(self.longitude, self.latitude, srid=4326)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.latitude:.5f}, {self.longitude:.5f}) at {self.recorded_at}"
