from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
    MAIN_OFFICER = 'MAIN_OFFICER', 'Main Officer / System Admin'
    SYS_ADMIN = 'SYS_ADMIN', 'System Admin'
    ACP = 'ACP', 'ACP / Senior Officer'
    SHO = 'SHO', 'Station House Officer'
    CONSTABLE = 'CONSTABLE', 'Constable / Ground Staff'


CANONICAL_PERMISSIONS = [
    # Dashboard
    'view_dashboard',
    # Idols
    'view_idols',
    'view_gpids',
    'view_police_stations',
    'view_holding_points',
    'view_visarjan_points',
    # Live Operations
    'view_live_map',
    'view_processions',
    'view_journey',
    'view_tracking_history',
    'ingest_telemetry',
    'view_officer_locations',
    # Assignments
    'view_assignments',
    'assign_field_officers',
    'create_assignments',
    'reassign_assignments',
    'manage_assignments',
    'handover_duty',
    # Reports
    'view_reports',
    'generate_reports',
    'export_reports',
    # System & Audits
    'view_audit_logs',
    'view_alerts',
    'manage_geography',
    # User & Role Management
    'manage_users',
    'manage_permissions',
    'manage_roles',
    'manage_role_templates',
]

ROLE_DEFAULT_PERMISSIONS = {
    UserRole.SUPER_ADMIN: list(CANONICAL_PERMISSIONS),
    UserRole.MAIN_OFFICER: [
        'view_dashboard', 'view_live_map', 'view_gpids', 'view_idols', 'view_processions',
        'view_police_stations', 'view_reports', 'generate_reports', 'view_alerts',
        'view_holding_points', 'view_visarjan_points', 'view_tracking_history', 'view_journey',
        'assign_field_officers', 'create_assignments', 'reassign_assignments', 'manage_assignments',
        'handover_duty', 'ingest_telemetry', 'view_officer_locations', 'manage_users',
        'manage_permissions', 'manage_geography', 'export_reports', 'view_audit_logs', 'view_assignments',
    ],
    UserRole.SYS_ADMIN: [
        'view_dashboard', 'view_live_map', 'view_gpids', 'view_idols', 'view_processions',
        'view_police_stations', 'view_reports', 'generate_reports', 'view_alerts',
        'view_holding_points', 'view_visarjan_points', 'view_tracking_history', 'view_journey',
        'assign_field_officers', 'create_assignments', 'reassign_assignments', 'manage_assignments',
        'handover_duty', 'ingest_telemetry', 'view_officer_locations', 'manage_users',
        'manage_geography', 'export_reports', 'view_audit_logs', 'view_assignments',
    ],
    UserRole.ACP: [
        'view_dashboard', 'view_live_map', 'view_gpids', 'view_idols', 'view_processions',
        'view_police_stations', 'view_reports', 'generate_reports', 'view_alerts',
        'view_holding_points', 'view_visarjan_points', 'view_tracking_history', 'view_journey',
        'assign_field_officers', 'create_assignments', 'reassign_assignments', 'view_officer_locations',
        'export_reports', 'view_assignments',
    ],
    UserRole.SHO: [
        'view_dashboard', 'view_live_map', 'view_gpids', 'view_idols', 'view_processions',
        'view_police_stations', 'view_reports', 'generate_reports', 'view_alerts',
        'view_holding_points', 'view_visarjan_points', 'view_tracking_history', 'view_journey',
        'assign_field_officers', 'create_assignments', 'reassign_assignments', 'view_officer_locations',
        'export_reports', 'view_assignments',
    ],
    UserRole.CONSTABLE: [
        'view_live_map', 'ingest_telemetry',
    ],
}


class RolePermissionTemplate(models.Model):
    """
    Persisted default capability template for each operational role.
    Only SUPER_ADMIN may modify these templates.
    """
    role = models.CharField(max_length=20, choices=UserRole.choices, unique=True, db_index=True)
    permissions = models.JSONField(default=list, blank=True)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    class Meta:
        verbose_name = 'Role Permission Template'
        verbose_name_plural = 'Role Permission Templates'
        ordering = ['role']

    def __str__(self):
        return f"{self.role} ({len(self.permissions)} permissions)"


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
        Uses custom_permissions if explicitly set, otherwise dynamic template
        from RolePermissionTemplate table, falling back to hardcoded ROLE_DEFAULT_PERMISSIONS.
        """
        if self.custom_permissions:
            valid_custom = [p for p in self.custom_permissions if p in CANONICAL_PERMISSIONS]
            if valid_custom:
                return valid_custom

        try:
            template = RolePermissionTemplate.objects.filter(role=self.role).first()
            if template and template.permissions is not None:
                return [p for p in template.permissions if p in CANONICAL_PERMISSIONS]
        except Exception:
            pass

        return ROLE_DEFAULT_PERMISSIONS.get(self.role, [])

    def has_capability(self, perm_name: str) -> bool:
        """
        Validates if user has the requested granular capability.
        """
        return perm_name in self.get_effective_permissions()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) - {self.police_station or 'City Wide'}"
