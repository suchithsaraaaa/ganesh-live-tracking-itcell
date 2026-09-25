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
    ADMIN_TERMINATED = 'ADMIN_TERMINATED', 'Admin Terminated'


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
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self):
        c_name = self.assignment.constable.username if (self.assignment and self.assignment.constable) else (
            (self.assignment.officer_name_snapshot or 'Unassigned') if self.assignment else 'Unassigned'
        )
        gpid = self.assignment.idol.gpid if (self.assignment and self.assignment.idol) else 'No Idol'
        return f"Session #{self.id} for {gpid} by {c_name} [{self.status}]"

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

    def terminate_session(self, terminal_status=TrackingSessionStatus.ADMIN_TERMINATED):
        self.status = terminal_status
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


class IdolEventType(models.TextChoices):
    REACHED_SITE = 'REACHED_SITE', 'Reached Site'
    TRACKING_STARTED = 'TRACKING_STARTED', 'Tracking Started'
    TRACKING_STOPPED = 'TRACKING_STOPPED', 'Tracking Stopped'
    ASSIGNMENT_CREATED = 'ASSIGNMENT_CREATED', 'Assignment Created'
    ASSIGNMENT_HANDOVER = 'ASSIGNMENT_HANDOVER', 'Assignment Handover'
    ASSIGNMENT_ENDED = 'ASSIGNMENT_ENDED', 'Assignment Ended'
    ASSIGNMENT_FORCE_ENDED = 'ASSIGNMENT_FORCE_ENDED', 'Assignment Force Ended'
    PROCESSION_ADMIN_TERMINATED = 'PROCESSION_ADMIN_TERMINATED', 'Procession Admin Terminated'
    ZONE_ENTERED = 'ZONE_ENTERED', 'Zone Entered'
    HOLDING_POINT_ENTERED = 'HOLDING_POINT_ENTERED', 'Holding Point Entered'
    HOLDING_POINT_EXITED = 'HOLDING_POINT_EXITED', 'Holding Point Exited'
    VISARJAN_REACHED = 'VISARJAN_REACHED', 'Visarjan Site Reached'
    IMMERSION_COMPLETED = 'IMMERSION_COMPLETED', 'Immersion Completed'
    VISARJAN_NOT_DONE = 'VISARJAN_NOT_DONE', 'Visarjan Not Done'
    SENT_TO_HOLDING = 'SENT_TO_HOLDING', 'Sent to Holding'
    RETURNED_TO_ORIGIN = 'RETURNED_TO_ORIGIN', 'Returned to Origin'
    REPORT_GENERATED = 'REPORT_GENERATED', 'Report Generated'


class IdolEvent(models.Model):
    """
    Chronological operational event history for an idol.
    Captures operational state changes, assignments, and handovers without duplicating raw GPS telemetry.
    """
    idol = models.ForeignKey(
        'idols.Idol',
        on_delete=models.CASCADE,
        related_name='operational_events'
    )
    gpid = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(
        max_length=50,
        choices=IdolEventType.choices,
        db_index=True
    )
    timestamp = models.DateTimeField(db_index=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    zone = models.CharField(max_length=100, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idol_events_triggered'
    )
    tracking_session = models.ForeignKey(
        TrackingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operational_events'
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['idol', 'timestamp']),
            models.Index(fields=['gpid', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.gpid} - {self.event_type} at {self.timestamp}"
