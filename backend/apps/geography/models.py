from django.conf import settings
from django.db import models
from apps.idols.models import Idol

if getattr(settings, 'USE_POSTGIS', False):
    from django.contrib.gis.db import models as gis_models


class PoliceStationBoundary(models.Model):
    """
    Police Station jurisdictional boundary model.
    Populated from authoritative reference data and official polygons.
    """
    ps_name = models.CharField(max_length=100, unique=True, db_index=True)
    ps_code = models.CharField(max_length=20, blank=True, db_index=True)
    zone = models.CharField(max_length=100, db_index=True)
    division = models.CharField(max_length=100, db_index=True)
    first_unique_id = models.CharField(max_length=50, blank=True)
    starting_gpid_number = models.IntegerField(null=True, blank=True)

    if getattr(settings, 'USE_POSTGIS', False):
        boundary = gis_models.GeometryField(srid=4326, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Police Station Boundary'
        verbose_name_plural = 'Police Station Boundaries'
        ordering = ['ps_name']

    def __str__(self):
        return f"{self.ps_name} ({self.ps_code}) - {self.zone}"


class BoundaryEventType(models.TextChoices):
    ENTRY = 'ENTRY', 'Entry'
    EXIT = 'EXIT', 'Exit'


class BoundaryEvent(models.Model):
    """
    Timestamped geofence event when an idol enters or exits a police station jurisdiction.
    """
    idol = models.ForeignKey(
        Idol,
        on_delete=models.CASCADE,
        related_name='boundary_events'
    )
    police_station = models.ForeignKey(
        PoliceStationBoundary,
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_type = models.CharField(
        max_length=10,
        choices=BoundaryEventType.choices,
        db_index=True
    )
    timestamp = models.DateTimeField(db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['idol', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.idol.gpid} {self.event_type} {self.police_station.ps_name} at {self.timestamp}"


class GeocodingCache(models.Model):
    """
    Persistent normalized spatial cache for reverse-geocoded place names and local PS jurisdictions.
    Coordinates are stored as 4-decimal place buckets (~11m resolution) to deduplicate nearby telemetry
    fixes without transferring place names across streets or jurisdictional boundaries.
    """
    lat_bucket = models.DecimalField(max_digits=9, decimal_places=4, db_index=True)
    lon_bucket = models.DecimalField(max_digits=9, decimal_places=4, db_index=True)
    place_name = models.CharField(max_length=255)
    police_station = models.CharField(max_length=150, default='Jurisdiction unavailable')
    zone = models.CharField(max_length=100, blank=True)
    division = models.CharField(max_length=100, blank=True)
    raw_address = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Geocoding Cache'
        verbose_name_plural = 'Geocoding Cache Entries'
        constraints = [
            models.UniqueConstraint(fields=['lat_bucket', 'lon_bucket'], name='unique_geocoding_lat_lon_bucket')
        ]
        indexes = [
            models.Index(fields=['lat_bucket', 'lon_bucket']),
        ]

    def __str__(self):
        return f"({self.lat_bucket}, {self.lon_bucket}) -> {self.place_name} [{self.police_station}]"
