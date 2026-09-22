from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    MAIN_OFFICER = 'MAIN_OFFICER', 'Main Officer / System Admin'
    ACP = 'ACP', 'ACP / Senior Officer'
    SHO = 'SHO', 'Station House Officer'
    CONSTABLE = 'CONSTABLE', 'Constable / Ground Staff'


CANONICAL_PERMISSIONS = [
    'view_dashboard',
    'view_live_map',
    'view_gpids',
    'view_processions',
    'view_police_stations',
    'view_reports',
    'view_alerts',
    'view_holding_points',
    'view_visarjan_points',
    'view_tracking_history',
    'assign_field_officers',
    'create_assignments',
    'reassign_assignments',
    'manage_assignments',
    'handover_duty',
    'ingest_telemetry',
    'view_officer_locations',
    'manage_users',
    'manage_permissions',
    'manage_geography',
    'export_reports',
]

ROLE_DEFAULT_PERMISSIONS = {
    UserRole.MAIN_OFFICER: list(CANONICAL_PERMISSIONS),
    UserRole.ACP: [
        'view_dashboard', 'view_live_map', 'view_gpids', 'view_processions',
        'view_police_stations', 'view_reports', 'view_alerts', 'view_holding_points',
        'view_visarjan_points', 'view_tracking_history', 'assign_field_officers',
        'create_assignments', 'reassign_assignments', 'view_officer_locations',
        'export_reports',
    ],
    UserRole.SHO: [
        'view_dashboard', 'view_live_map', 'view_gpids', 'view_processions',
        'view_police_stations', 'view_reports', 'view_alerts', 'view_holding_points',
        'view_visarjan_points', 'view_tracking_history', 'assign_field_officers',
        'create_assignments', 'reassign_assignments', 'view_officer_locations',
        'export_reports',
    ],
    UserRole.CONSTABLE: [
        'view_live_map',
    ],
}


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CONSTABLE,
        db_index=True
    )
    police_id = models.CharField(max_length=50, blank=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    zone = models.CharField(max_length=100, blank=True, db_index=True)
    division = models.CharField(max_length=100, blank=True, db_index=True)
    police_station = models.CharField(max_length=100, blank=True, db_index=True)
    must_change_password = models.BooleanField(default=False)
    custom_permissions = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def clean(self):
        super().clean()
        if self.custom_permissions:
            invalid = [p for p in self.custom_permissions if p not in CANONICAL_PERMISSIONS]
            if invalid:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Invalid permissions: {', '.join(invalid)}")

    def get_effective_permissions(self):
        """
        Returns list of effective permission codenames.
        Uses custom_permissions if explicitly set, otherwise defaults based on role.
        """
        if self.custom_permissions:
            valid_custom = [p for p in self.custom_permissions if p in CANONICAL_PERMISSIONS]
            if valid_custom:
                return valid_custom
        return ROLE_DEFAULT_PERMISSIONS.get(self.role, [])

    def has_capability(self, perm_name: str) -> bool:
        """
        Validates if user has the requested granular capability.
        """
        return perm_name in self.get_effective_permissions()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) - {self.police_station or 'City Wide'}"
