from django.db import models


class ProcessionState(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    TRACKING = 'TRACKING', 'Tracking Started'
    MOVING = 'MOVING', 'In Transit / Moving'
    HOLDING = 'HOLDING', 'Holding / Stoppage'
    AT_VISARJAN = 'AT_VISARJAN', 'At Visarjan Site'
    IMMERSION_COMPLETED = 'IMMERSION_COMPLETED', 'Immersion Completed'


class GeocodingStatus(models.TextChoices):
    NOT_GEOCODED = 'NOT_GEOCODED', 'Not Geocoded'
    GEOCODED = 'GEOCODED', 'Geocoded'
    PARTIAL = 'PARTIAL', 'Partial'
    UNRESOLVED = 'UNRESOLVED', 'Unresolved'


class GeocodingConfidence(models.TextChoices):
    EXACT = 'EXACT', 'Exact Building / Premise'
    HIGH = 'HIGH', 'High Confidence (Street / Landmark)'
    MEDIUM = 'MEDIUM', 'Medium Confidence (Locality / Village)'
    UNRESOLVED = 'UNRESOLVED', 'Unresolved'


class Idol(models.Model):
    """
    Authoritative Idol master record.
    GPID is the authoritative user-facing identifier and must never be regenerated.
    """
    gpid = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Authoritative GPID (e.g., HYDCMRZCMNR1749)"
    )
    ref_no = models.CharField(max_length=64, blank=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, help_text="Organizer/Applicant Name")
    association_name = models.CharField(max_length=255, blank=True)

    # Jurisdiction
    dist_name = models.CharField(max_length=100, default='HYDERABAD')
    zone = models.CharField(max_length=100, db_index=True)
    division = models.CharField(max_length=100, db_index=True)
    police_station = models.CharField(max_length=100, db_index=True)
    ps_code = models.CharField(max_length=20, blank=True, db_index=True)

    # Location & Address Details
    address = models.TextField(blank=True)
    instal_h_no = models.CharField(max_length=100, blank=True)
    instal_street = models.CharField(max_length=255, blank=True)
    instal_floor = models.CharField(max_length=50, blank=True)
    instal_village = models.CharField(max_length=255, blank=True)
    instal_pin = models.CharField(max_length=20, blank=True)

    # Resolved Geographic Origin Coordinates
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, db_index=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, db_index=True)
    geocoding_status = models.CharField(
        max_length=20,
        choices=GeocodingStatus.choices,
        default=GeocodingStatus.NOT_GEOCODED,
        db_index=True
    )
    geocoded_at = models.DateTimeField(null=True, blank=True)
    geocoding_provider = models.CharField(max_length=50, blank=True)
    geocoding_confidence = models.CharField(
        max_length=20,
        choices=GeocodingConfidence.choices,
        default=GeocodingConfidence.UNRESOLVED,
        db_index=True
    )
    resolved_address = models.TextField(blank=True, help_text="Display address returned by geocoder")
    geocoding_result_type = models.CharField(max_length=50, blank=True, help_text="OSM type: building, road, suburb, etc.")
    geocoding_query_used = models.TextField(blank=True, help_text="Exact query string passed to geocoder")

    # Dimensions
    idol_height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pandal_height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Immersion Information
    immersion_date = models.DateField(null=True, blank=True)
    river_name = models.CharField(max_length=150, blank=True)
    lake_type = models.CharField(max_length=100, blank=True)
    idol_type = models.CharField(max_length=100, blank=True)
    specify_type = models.CharField(max_length=100, blank=True)
    idol_area_type = models.CharField(max_length=100, blank=True)

    # Installation Schedule
    instal_from_date = models.DateField(null=True, blank=True)
    instal_to_date = models.DateField(null=True, blank=True)

    # Approvals & Master Status
    status = models.CharField(max_length=50, default='APPROVED', db_index=True)

    # Operational Procession State (owned by Idol)
    procession_state = models.CharField(
        max_length=30,
        choices=ProcessionState.choices,
        default=ProcessionState.NOT_STARTED,
        db_index=True
    )

    # Auxiliary source data preservation (restricted contacts, permissions, raw metadata)
    raw_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Preserved raw source fields and restricted contact details"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Idol'
        verbose_name_plural = 'Idols'
        ordering = ['gpid']
        indexes = [
            models.Index(fields=['zone', 'police_station']),
            models.Index(fields=['procession_state', 'status']),
            models.Index(fields=['immersion_date']),
            models.Index(fields=['immersion_date', 'procession_state']),
        ]

    @property
    def is_report_eligible(self):
        """Authoritative evaluation for report eligibility."""
        from apps.reports.services import is_report_eligible
        return is_report_eligible(self)

    def __str__(self):
        return f"{self.gpid} - {self.name or self.association_name or 'Idol'}"


class ImportIssueType(models.TextChoices):
    MISSING_GPID = 'MISSING_GPID', 'Missing GPID'
    DUPLICATE_GPID = 'DUPLICATE_GPID', 'Duplicate GPID'
    INVALID_PS_CODE = 'INVALID_PS_CODE', 'Invalid Police Station Code'
    VALIDATION_ERROR = 'VALIDATION_ERROR', 'Validation Error'


class ImportRun(models.Model):
    """Tracks each execution of the master dataset importer."""
    file_name = models.CharField(max_length=255)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_rows = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    invalid_gpid_count = models.IntegerField(default=0)
    duplicate_gpid_count = models.IntegerField(default=0)
    invalid_ps_count = models.IntegerField(default=0)
    summary_notes = models.TextField(blank=True)

    def __str__(self):
        return f"ImportRun {self.id} on {self.file_name} ({self.imported_count} imported)"


class ImportIssue(models.Model):
    """Structured record of invalid or skipped source rows."""
    import_run = models.ForeignKey(ImportRun, on_delete=models.CASCADE, related_name='issues')
    row_number = models.IntegerField()
    gpid = models.CharField(max_length=64, blank=True, db_index=True)
    ref_no = models.CharField(max_length=64, blank=True)
    ps_name = models.CharField(max_length=100, blank=True)
    issue_type = models.CharField(max_length=30, choices=ImportIssueType.choices, db_index=True)
    error_message = models.TextField()
    raw_row_data = models.JSONField(default=dict)

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        return f"Row {self.row_number}: {self.get_issue_type_display()} - {self.gpid or 'No GPID'}"
